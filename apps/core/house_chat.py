import unicodedata
from datetime import timedelta

from django.utils import timezone

from apps.baby.selectors import active_baby_foods, get_baby_plan
from apps.chores.models import Chore
from apps.chores.selectors import open_chores
from apps.chores.services import ChoreError, add_chore, set_chore_done
from apps.core.models import HouseMessage
from apps.core.summary import summary_for
from apps.core.week import monday_of, weekday_label, weekday_short
from apps.households.selectors import list_members
from apps.meal_plans.selectors import get_plan_for_week
from apps.meal_plans.services.planning import PlanningError, change_entry
from apps.preferences.models import RecipePreference
from apps.preferences.services import upsert_preference
from apps.recipes.ai import ask_model
from apps.recipes.models import Recipe
from apps.recipes.selectors import find_duplicates, list_active_recipes, recipes_for_household
from apps.recipes.services import guess_recipe_category
from apps.shopping.models import ShoppingItem
from apps.shopping.selectors import person_label
from apps.shopping.services import ShoppingError, add_recipe_ingredients, add_shopping_item

_MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
_HISTORY = 8
_KEEP = 40
_MAX_ACTIONS = 4
_SYSTEM = (
    "Eres Casa, el asistente del hogar en Nuestro Menú. "
    "Respondes en español y breve, usando solo los datos que vienen en el mensaje. "
    "Cada mensaje trae un índice (menú de la semana, lista, carro, pendientes y nombres de recetas) "
    "y solo el detalle que encaja con la pregunta. "
    "Si un mensaje anterior dijo que faltaba un dato, vuelve a mirar los bloques de este mensaje. "
    "No inventes platos, recetas, tareas ni productos. "
    "Si falta un dato, dilo y deja actions vacío. "
    "actions solo cuando la persona pide un cambio. "
    "kind puede ser add_shopping, mark_cart, unmark_cart, ingredients_to_list, "
    "add_chore, complete_chore, reopen_chore, create_recipe, set_dish, favorite o avoid. "
    "name es el producto, la tarea, la receta o el alimento. "
    "day es hoy, mañana o un día de esta semana, y hace falta en set_dish. "
    "cadence es hoy, dia, semana o cuando. assignee es el nombre de una persona de la casa, o vacío. "
    "Para create_recipe, ingredients y steps van en líneas separadas y category es una de: "
    "legumbres, carne, pescado, pasta, arroz, verduras, huevos, otros. "
    "No borres nada, no vacíes el carro y no apruebes el menú."
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
                    "day": {"type": "string"},
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
        f"Hogar: {household.name}.",
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
    wanted = _topics(question)
    if "meals" in wanted:
        meals = [f"{row['name']} ({row['count']})" for row in summary_for(household, today)["meals"]]
        lines.append(
            "Platos aprobados en las últimas 4 semanas: " + (", ".join(meals) or "ninguno") + "."
        )
    items = list(ShoppingItem.objects.filter(household=household).order_by("done", "position", "name"))
    pending = [item.name for item in items if not item.done][:40]
    cart = [item.name for item in items if item.done][:40]
    lines.append("Lista de compra: " + (", ".join(pending) or "nada pendiente") + ".")
    lines.append("En el carro: " + (", ".join(cart) or "nada") + ".")
    if "purchases" in wanted:
        purchases = summary_for(household, today)["purchases"]
        lines.append("Historial de compras, de más comprado a más reciente:")
        lines.extend(_purchase_lines(purchases) or ["Ninguna."])
    chores = open_chores(household, today)
    visible = chores["hoy"] + chores["cuando"]
    chore_bits = []
    for chore in visible:
        state = "hecha" if chore.is_done else "pendiente"
        who = person_label(chore.assignee) if chore.assignee_id else "sin asignar"
        chore_bits.append(f"{chore.title} ({chore.get_cadence_display()}, {who}, {state})")
    lines.append("Por hacer: " + ("; ".join(chore_bits) or "nada") + ".")
    if "baby" in wanted:
        lines.extend(_baby_lines(household, today))
    if "preferences" in wanted:
        lines.extend(_preference_lines(household, user))
    recipes = list(list_active_recipes(household).order_by("name")[:60])
    lines.append(
        "Recetas: "
        + (", ".join(f"{recipe.name} ({recipe.get_category_display()})" for recipe in recipes) or "ninguna")
        + "."
    )
    detailed = _recipes_for_detail(recipes, question, "recipes" in wanted)
    if detailed:
        lines.append("Detalle de recetas:")
        lines.extend(_recipe_lines(detailed))
    archived = list(
        recipes_for_household(household).filter(is_active=False).order_by("name").values_list("name", flat=True)[:40]
    )
    if archived:
        lines.append("Recetas archivadas: " + ", ".join(archived) + ".")
    return "\n".join(lines)


_BROAD = ("en casa", "toda la casa", "todo lo", "informe", "cuentame", "que sabes", "que puedes")
_PURCHASE_WORDS = ("compra", "compro", "comprado", "historial", "carro", "carrito", "veces")
_RECIPE_WORDS = ("receta", "ingrediente", "paso", "detalle", "como se hace", "guardad")
_BABY_WORDS = ("bebe", "pure", "merienda", "alimento del")
_PREFERENCE_WORDS = ("favorit", "evitar", "puntuacion")
_MEAL_WORDS = ("ultimas semanas", "mas com", "aprobad")


def _topics(question):
    folded = _fold(question)
    if any(phrase in folded for phrase in _BROAD):
        return {"meals", "purchases", "recipes", "baby", "preferences"}
    topics = set()
    if any(word in folded for word in _PURCHASE_WORDS):
        topics.add("purchases")
    if any(word in folded for word in _RECIPE_WORDS):
        topics.add("recipes")
    if any(word in folded for word in _BABY_WORDS):
        topics.add("baby")
    if any(word in folded for word in _PREFERENCE_WORDS):
        topics.add("preferences")
    if any(word in folded for word in _MEAL_WORDS):
        topics.add("meals")
    return topics


def _recipes_for_detail(recipes, question, all_of_them):
    if all_of_them:
        return recipes
    folded = _fold(question)
    return [recipe for recipe in recipes if _named_in(recipe, folded)]


def _purchase_lines(purchases):
    lines = []
    for row in purchases:
        times = row.get("times") or []
        recent = "; ".join(
            f"{item['when']}, lo añadió {item['added']}, lo compró {item['bought']}"
            for item in times[:4]
        )
        lines.append(f"{row['name']}: {row['count']} veces. {recent}".rstrip())
    return lines


def _baby_lines(household, today):
    foods = [
        f"{food.name} ({food.get_texture_display()})"
        for food in active_baby_foods(household)[:40]
    ]
    lines = ["Alimentos del bebé: " + (", ".join(foods) or "ninguno") + "."]
    plan = get_baby_plan(household, monday_of(today))
    if plan is None:
        lines.append("Menú del bebé de esta semana: no hay.")
        return lines
    meals = [
        f"{weekday_short(entry.day).lower()} {entry.day.day} {entry.get_slot_display().lower()}: {entry.food.name}"
        for entry in plan.entries.all()
    ]
    lines.append("Menú del bebé de esta semana: " + ("; ".join(meals) or "sin comidas") + ".")
    return lines


def _preference_lines(household, user):
    rows = RecipePreference.objects.filter(user=user, recipe__household=household).select_related("recipe")
    favorites = [row.recipe.name for row in rows if row.is_favorite]
    avoided = [row.recipe.name for row in rows if row.is_avoided]
    rated = [f"{row.recipe.name} {row.rating}" for row in rows if row.rating]
    return [
        "Favoritas de quien habla: " + (", ".join(favorites) or "ninguna") + ".",
        "Recetas a evitar: " + (", ".join(avoided) or "ninguna") + ".",
        "Puntuaciones: " + (", ".join(rated) or "ninguna") + ".",
    ]


def _recipe_lines(recipes):
    ordered = sorted(recipes, key=lambda recipe: recipe.name.casefold())
    lines = []
    used = 0
    for recipe in ordered:
        line = _recipe_detail(recipe)
        if lines and used + len(line) > 12000:
            lines.append("Hay más recetas. Pregunta por el nombre para ver esa.")
            break
        lines.append(line)
        used += len(line)
    return lines


def _named_in(recipe, folded_question):
    folded_name = _fold(recipe.name)
    return len(folded_name) >= 4 and folded_name in folded_question


def _recipe_detail(recipe):
    bits = [recipe.get_category_display()]
    if recipe.servings:
        bits.append(f"{recipe.servings} raciones")
    if recipe.prep_time_minutes:
        bits.append(f"{recipe.prep_time_minutes} min")
    parts = [f"{recipe.name} ({', '.join(bits)})."]
    if recipe.ingredients.strip():
        parts.append("Ingredientes: " + " | ".join(recipe.ingredient_lines)[:400])
    else:
        parts.append("Ingredientes: sin anotar.")
    if recipe.steps.strip():
        parts.append("Pasos: " + " | ".join(recipe.step_lines)[:400])
    notes = (recipe.notes or "").strip()
    if notes:
        parts.append("Notas: " + notes[:200])
    return " ".join(parts)


def _apply(household, user, action):
    kind = str(action.get("kind") or "").strip()
    name = " ".join(str(action.get("name") or "").split())
    try:
        if kind == "add_shopping":
            return _add_shopping(household, user, name)
        if kind == "mark_cart":
            return _set_cart(household, name, True)
        if kind == "unmark_cart":
            return _set_cart(household, name, False)
        if kind == "ingredients_to_list":
            return _ingredients_to_list(household, user, name)
        if kind == "add_chore":
            return _add_chore(household, user, name, action)
        if kind == "complete_chore":
            return _complete_chore(household, name, done=True)
        if kind == "reopen_chore":
            return _complete_chore(household, name, done=False)
        if kind == "create_recipe":
            return _create_recipe(household, name, action)
        if kind == "set_dish":
            return _set_dish(household, name, action)
        if kind == "favorite":
            return _set_preference(household, user, name, favorite=True)
        if kind == "avoid":
            return _set_preference(household, user, name, favorite=False)
    except (ShoppingError, ChoreError, HouseActionError, PlanningError) as exc:
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


def _complete_from(pending, name, today, done):
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
    set_chore_done(chosen[0], today, done)
    return "", f"Por hacer · {chosen[0].title}"


def _complete_chore(household, name, done):
    if not name:
        raise HouseActionError("Di qué tarea es.")
    today = timezone.localdate()
    board = open_chores(household, today)
    chores = [
        chore
        for chore in board["hoy"] + board["cuando"]
        if chore.is_done is not done
    ]
    return _complete_from(chores, name, today, done)


def _set_cart(household, name, done):
    if not name:
        raise HouseActionError("Di qué producto es.")
    items = list(ShoppingItem.objects.filter(household=household, done=not done))
    chosen = _match_name(items, name, lambda item: item.name)
    if not chosen:
        anywhere = _match_name(
            list(ShoppingItem.objects.filter(household=household)), name, lambda item: item.name
        )
        if anywhere:
            raise HouseActionError("Ya está en el carro." if done else "Sigue en la lista.")
        raise HouseActionError("No encuentro ese producto.")
    if len(chosen) > 1:
        titles = " y ".join(item.name for item in chosen[:4])
        raise HouseActionError(f"Hay varios productos parecidos: {titles}.")
    chosen[0].done = done
    chosen[0].save(update_fields=["done", "updated_at"])
    label = "En el carro" if done else "Lista de compra"
    return "", f"{label} · {chosen[0].name}"


def _ingredients_to_list(household, user, name):
    recipe = _one_recipe(household, name)
    added, _skipped = add_recipe_ingredients(household, recipe, user)
    if not added:
        raise HouseActionError("Esos ingredientes ya están en la lista.")
    return "", f"Lista de compra · {added} de {recipe.name}"


def _set_dish(household, name, action):
    recipe = _one_recipe(household, name)
    today = timezone.localdate()
    day = _parse_day(str(action.get("day") or ""), today)
    change_entry(household, monday_of(day), day, recipe)
    return "", f"Menú · {weekday_short(day).lower()} {day.day}: {recipe.name}"


def _set_preference(household, user, name, favorite):
    recipe = _one_recipe(household, name)
    upsert_preference(user, recipe, is_favorite=favorite, is_avoided=not favorite)
    label = "Favorita" if favorite else "A evitar"
    return "", f"{label} · {recipe.name}"


def _one_recipe(household, name):
    if not name:
        raise HouseActionError("Di el nombre de la receta.")
    recipes = list(recipes_for_household(household).filter(is_active=True))
    chosen = _match_name(recipes, name, lambda recipe: recipe.name)
    if not chosen:
        raise HouseActionError("No encuentro esa receta.")
    if len(chosen) > 1:
        titles = " y ".join(recipe.name for recipe in chosen[:4])
        raise HouseActionError(f"Hay varias recetas parecidas: {titles}.")
    return chosen[0]


def _match_name(rows, name, label):
    folded = _fold(name)
    exact = [row for row in rows if _fold(label(row)) == folded]
    return exact or [
        row for row in rows if folded and (folded in _fold(label(row)) or _fold(label(row)) in folded)
    ]


def _parse_day(value, today):
    phrase = _fold(value)
    if not phrase or phrase == "hoy":
        return today
    if "manana" in phrase:
        return today + timedelta(days=1)
    week = monday_of(today)
    names = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
    for index, name in enumerate(names):
        if name in phrase:
            return week + timedelta(days=index)
    raise HouseActionError("Di el día: hoy, mañana o un día de esta semana.")


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
