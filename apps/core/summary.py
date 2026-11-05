from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.meal_plans.models import MealPlan, MealPlanEntry
from apps.shopping.models import Purchase, product_key

WINDOW_DAYS = 28


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
    bought = Purchase.objects.filter(
        household=household, bought_on__gte=since, bought_on__lte=today
    ).order_by("name")
    for purchase in bought:
        key = product_key(purchase.normalized_name or purchase.name)
        bucket = grouped.setdefault(key, {"count": 0, "names": []})
        bucket["count"] += 1
        bucket["names"].append(purchase.name)
    ranked = sorted(grouped.values(), key=lambda row: (-row["count"], _purchase_label(row["names"]).casefold()))
    named = [
        {"name": _purchase_label(row["names"]), "count": row["count"]}
        for row in ranked[:8]
    ]
    return {
        "since": since,
        "meals": _bars(meals, "recipe__name"),
        "purchases": _bars(named, "name"),
    }


def _purchase_label(names):
    chosen = sorted(names, key=lambda name: (-names.count(name), -len(name), name.casefold()))[0]
    if chosen.islower():
        return chosen[:1].upper() + chosen[1:]
    return chosen
