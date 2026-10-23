from apps.shopping.models import ShoppingItem


def shopping_page(household, form=None):
    from apps.shopping.forms import AddShoppingItemForm

    items = list(ShoppingItem.objects.filter(household=household).order_by("name"))
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
    return {
        "groups": groups,
        "cart": cart,
        "pending": len(pending),
        "aisles": ShoppingItem.Aisle.choices,
        "form": form or AddShoppingItemForm(),
        "has_items": bool(items),
    }


def pending_count(household):
    return ShoppingItem.objects.filter(household=household, done=False).count()
