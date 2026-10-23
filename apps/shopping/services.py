from django.db import IntegrityError

from apps.shopping.models import ShoppingItem, normalize_item_name


class ShoppingError(Exception):
    pass


def add_shopping_item(household, name):
    cleaned = " ".join((name or "").split())
    if not cleaned:
        raise ShoppingError("Escribe lo que falta.")
    normalized = normalize_item_name(cleaned)
    if ShoppingItem.objects.filter(household=household, normalized_name=normalized).exists():
        raise ShoppingError("Ya está en la lista.")
    try:
        return ShoppingItem.objects.create(
            household=household,
            name=cleaned,
            aisle=ShoppingItem.Aisle.NONE,
        )
    except IntegrityError as exc:
        raise ShoppingError("Ya está en la lista.") from exc


def clear_bought(household):
    deleted, _detail = ShoppingItem.objects.filter(household=household, done=True).delete()
    return deleted
