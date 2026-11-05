from django.db import IntegrityError
from django.utils import timezone

from apps.shopping.models import Purchase, ShoppingItem, normalize_item_name


class ShoppingError(Exception):
    pass


def add_shopping_item(household, name, user=None):
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
            added_by=user,
        )
    except IntegrityError as exc:
        raise ShoppingError("Ya está en la lista.") from exc


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
