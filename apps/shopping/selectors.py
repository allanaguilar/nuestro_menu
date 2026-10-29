from datetime import timedelta

from django.db.models import Count, Max
from django.utils import timezone

from apps.shopping.models import ShoppingItem, ShoppingPresence

RECENT_ADD = timedelta(minutes=15)
PRESENCE_WINDOW = timedelta(seconds=30)


def person_label(user):
    name = (user.first_name or "").strip()
    return name or user.get_username()


def pending_sentence(count):
    if count == 0:
        return "No queda nada"
    if count == 1:
        return "Queda 1"
    return f"Quedan {count}"


def touch_presence(household, user):
    ShoppingPresence.objects.update_or_create(
        household=household,
        user=user,
        defaults={"last_seen": timezone.now()},
    )


def viewers_sentence(household, user):
    cutoff = timezone.now() - PRESENCE_WINDOW
    names = [
        person_label(row.user)
        for row in ShoppingPresence.objects.filter(
            household=household, last_seen__gte=cutoff
        )
        .exclude(user=user)
        .select_related("user")
    ]
    if not names:
        return ""
    if len(names) == 1:
        return f"{names[0]} también la tiene abierta."
    return f"{' y '.join(names)} también la tienen abierta."


def items_revision(household):
    stamp = ShoppingItem.objects.filter(household=household).aggregate(
        latest=Max("updated_at"), count=Count("id")
    )
    latest = stamp["latest"].isoformat() if stamp["latest"] else "0"
    return f"{stamp['count']}:{latest}"


def shopping_page(household, user, form=None):
    from apps.shopping.forms import AddShoppingItemForm

    items = list(
        ShoppingItem.objects.filter(household=household)
        .select_related("added_by")
        .order_by("name")
    )
    recent = timezone.now() - RECENT_ADD
    for item in items:
        item.fresh_from = ""
        if (
            item.added_by_id
            and user is not None
            and item.added_by_id != user.id
            and item.created_at >= recent
        ):
            item.fresh_from = person_label(item.added_by)
    pending = [item for item in items if not item.done]
    cart = [item for item in items if item.done]
    by_aisle = {key: [] for key, _label in ShoppingItem.Aisle.choices}
    for item in pending:
        by_aisle[item.aisle].append(item)
    groups = [
        {"key": key, "label": label, "items": by_aisle[key]}
        for key, label in ShoppingItem.Aisle.choices
        if by_aisle[key]
    ]
    count = len(pending)
    return {
        "groups": groups,
        "cart": cart,
        "pending": count,
        "pending_label": pending_sentence(count) if items else "",
        "aisles": ShoppingItem.Aisle.choices,
        "form": form or AddShoppingItemForm(),
        "has_items": bool(items),
        "viewers": viewers_sentence(household, user) if user is not None else "",
        "revision": items_revision(household),
    }


def pending_count(household):
    return ShoppingItem.objects.filter(household=household, done=False).count()
