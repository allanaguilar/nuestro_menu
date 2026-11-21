import unicodedata

from django.utils import timezone

from apps.chores.models import Chore
from apps.chores.selectors import open_chores
from apps.chores.services import ChoreError, add_chore, set_chore_done
from apps.core.models import HouseMessage
from apps.core.week import monday_of, weekday_label, weekday_short
from apps.households.selectors import list_members
from apps.meal_plans.selectors import get_plan_for_week
from apps.recipes.ai import ask_model
from apps.recipes.models import Recipe
from apps.recipes.selectors import find_duplicates, list_active_recipes
from apps.recipes.services import guess_recipe_category
from apps.shopping.models import ShoppingItem
from apps.shopping.selectors import person_label
from apps.shopping.services import ShoppingError, add_shopping_item

_MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
_HISTORY = 8
_KEEP = 40
_MAX_ACTIONS = 4
_SYSTEM = (
    "Eres Casa, el asistente del hogar en Nuestro Menú. "
    "Respondes en español, en una o dos frases, usando solo los datos que vienen en el mensaje. "
    "No inventes platos, recetas, tareas ni productos. "
    "Si falta un dato, dilo y deja actions vacío. "
    "actions solo cuando la persona pide un cambio. "
    "kind puede ser add_shopping, add_chore, complete_chore o create_recipe. "
    "name es el producto, la tarea o la receta. "
    "cadence es hoy, dia, semana o cuando. assignee es el nombre de una persona de la casa, o vacío. "
    "Para create_recipe, ingredients y steps van en líneas separadas y category es una de: "
    "legumbres, carne, pescado, pasta, arroz, verduras, huevos, otros. "
    "No borres nada, no vacíes la compra y no apruebes el menú."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string"},
                    "name": {"type": "string"},
                    "cadence": {"type": "string"},
                    "assignee": {"type": "string"},
                    "category": {"type": "string"},
                    "ingredients": {"type": "string"},
                    "steps": {"type": "string"},
                    "servings": {"type": "integer", "nullable": True},
                },
                "required": ["kind", "name"],
            },
        },
    },
    "required": ["reply", "actions"],
}


def house_messages(household, user):
    return HouseMessage.objects.filter(household=household, user=user)


def message_payload(message):
    return {
        "role": message.role,
        "body": message.body,
        "receipts": [line for line in (message.receipts or "").splitlines() if line.strip()],
    }


def speak(household, user, text):
    cleaned = " ".join((text or "").split())
    if not cleaned:
        raise ValueError("Escribe lo que quieres preguntar.")
    cleaned = cleaned[:1000]
    prior = list(house_messages(household, user).order_by("-created_at")[:_HISTORY])
    prior.reverse()
    contents = [
        ("user" if item.role == HouseMessage.Role.USER else "model", item.body)
        for item in prior
    ]
    contents.append(("user", f"{house_snapshot(household, user, cleaned)}\n\nPregunta:\n{cleaned}"))
    data = ask_model(household.gemini_model, _SYSTEM, contents, _SCHEMA)
    reply = " ".join(str(data.get("reply") or "").split())
    notes = []
    receipts = []
    actions = data.get("actions") if isinstance(data.get("actions"), list) else []
    for action in actions[:_MAX_ACTIONS]:
        if not isinstance(action, dict):
            continue
        note, receipt = _apply(household, user, action)
        if note:
            notes.append(note)
        if receipt:
            receipts.append(receipt)
    if notes:
        reply = " ".join(part for part in (reply, " ".join(notes)) if part).strip()
    if not reply:
        reply = "Hecho." if receipts else "No tengo eso en casa."
    user_row = HouseMessage.objects.create(
        household=household, user=user, role=HouseMessage.Role.USER, body=cleaned
    )
    casa_row = HouseMessage.objects.create(
        household=household,
        user=user,
        role=HouseMessage.Role.CASA,
        body=reply,
        receipts="\n".join(receipts),
    )
    stale = list(
        house_messages(household, user).order_by("-created_at").values_list("pk", flat=True)[_KEEP:]
    )
    if stale:
        HouseMessage.objects.filter(pk__in=stale).delete()
    return {"user": message_payload(user_row), "reply": message_payload(casa_row)}


def house_snapshot(household, user, question):
    today = timezone.localdate()
    people = [person_label(member.user) for member in list_members(household)]
    lines = [
        f"Hoy es {weekday_label(today).lower()} {today.day} {_MONTHS[today.month - 1]}.",
        f"Quien habla: {person_label(user)}.",
        "Personas: " + ", ".join(people) + ".",
    ]
    plan = get_plan_for_week(household, monday_of(today))
    if plan is None:
        lines.append("Menú de esta semana: no hay.")
    else:
        status = "aprobado" if plan.status == plan.Status.APPROVED else "borrador"
        dishes = [
            f"{weekday_short(entry.day).lower()} {entry.day.day}: {entry.recipe.name}"
            for entry in plan.entries.all()
        ]
        lines.append(f"Menú de esta semana ({status}): " + ("; ".join(dishes) or "sin platos") + ".")
    items = list(ShoppingItem.objects.filter(household=household).order_by("done", "position", "name"))
    pending = [item.name for item in items if not item.done][:40]
    cart = [item.name for item in items if item.done][:40]
    lines.append("Lista de compra: " + (", ".join(pending) or "nada pendiente") + ".")
    lines.append("En el carro: " + (", ".join(cart) or "nada") + ".")
    chores = open_chores(household, today)
    visible = chores["hoy"] + chores["cuando"]
    chore_bits = []
    for chore in visible:
        state = "hecha" if chore.is_done else "pendiente"
        who = person_label(chore.assignee) if chore.assignee_id else "sin asignar"
        chore_bits.append(f"{chore.title} ({chore.get_cadence_display()}, {who}, {state})")
    lines.append("Por hacer: " + ("; ".join(chore_bits) or "nada") + ".")
    recipes = list(list_active_recipes(household).order_by("name")[:60])
    lines.append(
        "Recetas: "
        + (", ".join(f"{recipe.name} ({recipe.get_category_display()})" for recipe in recipes) or "ninguna")
        + "."
    )
    folded_question = _fold(question)
    details = []
    for recipe in recipes:
        folded_name = _fold(recipe.name)
        if len(folded_name) >= 4 and folded_name in folded_question:
            details.append(_recipe_detail(recipe))
        if len(details) == 2:
            break
    lines.extend(details)
    return "\n".join(lines)


def _recipe_detail(recipe):
    parts = [f"Detalle de {recipe.name}:"]
    if recipe.ingredients.strip():
        parts.append("Ingredientes: " + " | ".join(recipe.ingredient_lines)[:500])
    if recipe.steps.strip():
        parts.append("Pasos: " + " | ".join(recipe.step_lines)[:500])
    return " ".join(parts)


def _apply(household, user, action):
    kind = str(action.get("kind") or "").strip()
    name = " ".join(str(action.get("name") or "").split())
    try:
        if kind == "add_shopping":
            return _add_shopping(household, user, name)
        if kind == "add_chore":
            return _add_chore(household, user, name, action)
        if kind == "complete_chore":
            return _complete_chore(household, name)
        if kind == "create_recipe":
            return _create_recipe(household, name, action)
    except (ShoppingError, ChoreError, HouseActionError) as exc:
        return str(exc), ""
    return "", ""


def _add_shopping(household, user, name):
    if not name:
        raise HouseActionError("Escribe lo que falta.")
    item = add_shopping_item(household, name[:120], user)
    return "", f"Lista de compra · {item.name}"


def _add_chore(household, user, name, action):
    if not name:
        raise HouseActionError("Escribe la tarea.")
    cadence = _cadence(str(action.get("cadence") or ""))
    assignee = _assignee(household, user, str(action.get("assignee") or ""))
    chore = add_chore(household, name[:80], cadence, assignee, timezone.localdate())
    return "", f"Por hacer · {chore.title}"


def _complete_from(pending, name, today):
    folded = _fold(name)
    exact = [chore for chore in pending if _fold(chore.title) == folded]
    chosen = exact or [
        chore for chore in pending if folded and (folded in _fold(chore.title) or _fold(chore.title) in folded)
    ]
    if not chosen:
        raise HouseActionError("No encuentro esa tarea.")
    if len(chosen) > 1:
        titles = " y ".join(chore.title for chore in chosen[:4])
        raise HouseActionError(f"Hay varias tareas parecidas: {titles}.")
    set_chore_done(chosen[0], today, True)
    return "", f"Por hacer · {chosen[0].title}"


def _complete_chore(household, name):
    if not name:
        raise HouseActionError("Di qué tarea está hecha.")
    today = timezone.localdate()
    board = open_chores(household, today)
    pending = [chore for chore in board["hoy"] + board["cuando"] if not chore.is_done]
    return _complete_from(pending, name, today)


def _create_recipe(household, name, action):
    if not name:
        raise HouseActionError("Falta el nombre de la receta.")
    ingredients = str(action.get("ingredients") or "").strip()
    steps = str(action.get("steps") or "").strip()
    if not ingredients and not steps:
        raise HouseActionError("Faltan los ingredientes o los pasos.")
    if find_duplicates(household, name).exists():
        raise HouseActionError("Esa receta ya está.")
    categories = {value for value, _label in Recipe.Category.choices}
    category = str(action.get("category") or "")
    if category not in categories:
        category = guess_recipe_category(name)
    servings = action.get("servings")
    if not isinstance(servings, int) or servings < 1:
        servings = None
    recipe = Recipe.objects.create(
        household=household,
        name=name[:180],
        category=category,
        servings=servings,
        ingredients=ingredients,
        steps=steps,
    )
    return "", f"Recetario · {recipe.name}"


def _cadence(value):
    phrase = _fold(value)
    if not phrase or "hoy" in phrase:
        return Chore.Cadence.TODAY
    if "semana" in phrase:
        return Chore.Cadence.WEEKLY
    if "cuando" in phrase:
        return Chore.Cadence.SOMEDAY
    if "dia" in phrase or "diario" in phrase:
        return Chore.Cadence.DAILY
    raise HouseActionError("Elige cuándo hay que hacerlo.")


def _assignee(household, user, label):
    cleaned = " ".join(label.split())
    if not cleaned:
        return None
    if _fold(cleaned) in {"yo", "mi", "conmigo"}:
        return user
    folded = _fold(cleaned)
    people = list(list_members(household))
    exact = [member.user for member in people if _fold(person_label(member.user)) == folded]
    if len(exact) == 1:
        return exact[0]
    partial = [
        member.user
        for member in people
        if folded and folded in _fold(person_label(member.user))
    ]
    if len(partial) == 1:
        return partial[0]
    raise HouseActionError("Esa persona no está en el hogar.")


def _fold(value):
    text = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in text if not unicodedata.combining(char)).casefold()


class HouseActionError(Exception):
    pass
