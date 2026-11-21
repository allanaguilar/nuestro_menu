from django.db import IntegrityError
from django.db.models import Max
from django.utils import timezone

from apps.shopping.models import Purchase, ShoppingItem, product_key


class ShoppingError(Exception):
    pass


def following_position(household):
    current = ShoppingItem.objects.filter(household=household).aggregate(last=Max("position"))
    return (current["last"] or 0) + 1


def add_shopping_item(household, name, user=None):
    cleaned = " ".join((name or "").split())
    if not cleaned:
        raise ShoppingError("Escribe lo que falta.")
    normalized = product_key(cleaned)
    if ShoppingItem.objects.filter(household=household, normalized_name=normalized).exists():
        raise ShoppingError("Ya está en la lista.")
    try:
        return ShoppingItem.objects.create(
            household=household,
            name=cleaned,
            aisle=ShoppingItem.Aisle.NONE,
            position=following_position(household),
            added_by=user,
        )
    except IntegrityError as exc:
        raise ShoppingError("Ya está en la lista.") from exc


def rename_shopping_item(item, name):
    cleaned = " ".join((name or "").split())
    if not cleaned:
        raise ShoppingError("Escribe lo que falta.")
    if len(cleaned) > 120:
        raise ShoppingError("El nombre es demasiado largo.")
    key = product_key(cleaned)
    clash = ShoppingItem.objects.filter(
        household_id=item.household_id, normalized_name=key
    ).exclude(pk=item.pk)
    if clash.exists():
        raise ShoppingError("Ya está en la lista.")
    item.name = cleaned
    try:
        item.save(update_fields=["name", "normalized_name", "updated_at"])
    except IntegrityError as exc:
        raise ShoppingError("Ya está en la lista.") from exc
    return item


def reorder_shopping_items(household, ordered_ids):
    pending = list(ShoppingItem.objects.filter(household=household, done=False))
    by_id = {str(item.pk): item for item in pending}
    ordered = []
    for raw in ordered_ids:
        item = by_id.pop(str(raw), None)
        if item:
            ordered.append(item)
    ordered.extend(by_id.values())
    now = timezone.now()
    for index, item in enumerate(ordered, start=1):
        if item.position != index:
            ShoppingItem.objects.filter(pk=item.pk).update(position=index, updated_at=now)


def add_recipe_ingredients(household, recipe, user=None):
    existing = set(
        ShoppingItem.objects.filter(household=household).values_list(
            "normalized_name", flat=True
        )
    )
    added = 0
    skipped = 0
    position = following_position(household)
    for line in recipe.ingredient_lines:
        cleaned = " ".join(line.split())[:120].strip()
        if not cleaned:
            continue
        key = product_key(cleaned)
        if key in existing:
            skipped += 1
            continue
        try:
            ShoppingItem.objects.create(
                household=household,
                name=cleaned,
                aisle=ShoppingItem.Aisle.NONE,
                position=position,
                added_by=user,
            )
            position += 1
        except IntegrityError:
            skipped += 1
            continue
        existing.add(key)
        added += 1
    return added, skipped


def clear_bought(household):
    bought = list(ShoppingItem.objects.filter(household=household, done=True))
    if bought:
        today = timezone.localdate()
        Purchase.objects.bulk_create(
            [
                Purchase(
                    household=household,
                    name=item.name,
                    normalized_name=item.normalized_name,
                    bought_on=today,
                )
                for item in bought
            ]
        )
    deleted, _detail = ShoppingItem.objects.filter(pk__in=[item.pk for item in bought]).delete()
    return deleted
