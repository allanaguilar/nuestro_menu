from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.meal_plans.models import MealPlan, MealPlanEntry
from apps.shopping.models import Purchase

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
    purchases = (
        Purchase.objects.filter(household=household, bought_on__gte=since, bought_on__lte=today)
        .values("normalized_name")
        .annotate(count=Count("id"))
        .order_by("-count", "normalized_name")[:8]
    )
    named = []
    for row in purchases:
        latest = (
            Purchase.objects.filter(
                household=household,
                normalized_name=row["normalized_name"],
                bought_on__gte=since,
            )
            .order_by("-bought_on", "-id")
            .values_list("name", flat=True)
            .first()
        )
        named.append({"name": latest or row["normalized_name"], "count": row["count"]})
    return {
        "since": since,
        "meals": _bars(meals, "recipe__name"),
        "purchases": _bars(named, "name"),
    }
