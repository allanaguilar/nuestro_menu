import re
import unicodedata
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.meal_plans.models import MealPlan, MealPlanEntry
from apps.shopping.models import Purchase, product_key
from apps.shopping.selectors import person_label

_WEEKDAYS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
_MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
_UNKNOWN_PERSON = "Sin registro"

WINDOW_DAYS = 28
PURCHASE_LIMIT = 10
_NUMBERS = re.compile(r"\d+")


def _bars(rows, name_key):
    top = max((row["count"] for row in rows), default=0)
    return [
        {
            "name": row[name_key],
            "count": row["count"],
            "percent": round(row["count"] * 100 / top) if top else 0,
        }
        for row in rows
    ]


def summary_for(household, today=None):
    today = today or timezone.localdate()
    since = today - timedelta(days=WINDOW_DAYS - 1)
    meals = (
        MealPlanEntry.objects.filter(
            meal_plan__household=household,
            meal_plan__status=MealPlan.Status.APPROVED,
            day__gte=since,
            day__lte=today,
        )
        .values("recipe__name")
        .annotate(count=Count("id"))
        .order_by("-count", "recipe__name")[:8]
    )
    grouped = {}
    bought = (
        Purchase.objects.filter(household=household)
        .select_related("added_by", "bought_by")
        .order_by("name")
    )
    for purchase in bought:
        if not _one_product(purchase.name):
            continue
        key = _purchase_key(purchase.name)
        bucket = grouped.setdefault(key, {"count": 0, "names": [], "events": []})
        bucket["count"] += 1
        bucket["names"].append(purchase.name.strip())
        bucket["events"].append(purchase)
    ranked = sorted(grouped.values(), key=_purchase_rank)
    named = [
        {
            "name": _purchase_label(row["names"]),
            "count": row["count"],
            "times": _purchase_times(row["events"]),
        }
        for row in ranked[:PURCHASE_LIMIT]
    ]
    purchases = _bars(named, "name")
    for row, source in zip(purchases, named):
        row["times"] = source["times"]
    return {
        "since": since,
        "meals": _bars(meals, "recipe__name"),
        "purchases": purchases,
    }


def _bought_when(day):
    return f"{_WEEKDAYS[day.weekday()]} {day.day} {_MONTHS[day.month - 1]}"


def _person(user):
    if user is None:
        return _UNKNOWN_PERSON
    return person_label(user)


def _purchase_times(events):
    ordered = sorted(events, key=lambda purchase: (purchase.bought_on, purchase.pk), reverse=True)
    return [
        {
            "when": _bought_when(purchase.bought_on),
            "added": _person(purchase.added_by),
            "bought": _person(purchase.bought_by),
        }
        for purchase in ordered
    ]


def _one_product(name):
    """A pasted ingredient list has several numbers and is not one product."""
    return len(_NUMBERS.findall(name or "")) <= 1


def _fold(name):
    folded = unicodedata.normalize("NFKD", name or "")
    return "".join(char for char in folded if not unicodedata.combining(char))


def _purchase_key(name):
    return product_key(_fold(name or ""))


def _purchase_rank(row):
    latest = max(purchase.bought_on for purchase in row["events"])
    return (-row["count"], -latest.toordinal(), _purchase_label(row["names"]).casefold())


def _purchase_label(names):
    def rank(name):
        accented = sum(1 for char in name if ord(char) > 127)
        return (-names.count(name), -len(name), -accented, name.casefold())

    chosen = sorted(names, key=rank)[0]
    if chosen.islower():
        return chosen[:1].upper() + chosen[1:]
    return chosen
