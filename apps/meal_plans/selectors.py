from datetime import timedelta

from django.db.models import Count

from apps.meal_plans.models import MealPlan, MealPlanEntry


def get_plan_for_week(household, week_start):
    return (
        MealPlan.objects.filter(household=household, week_start=week_start)
        .prefetch_related("entries__recipe")
        .first()
    )


def list_history(household):
    return (
        MealPlan.objects.filter(household=household)
        .annotate(entry_count=Count("entries"))
        .order_by("-week_start")
    )


def approved_entries_for_household(household):
    return MealPlanEntry.objects.filter(
        meal_plan__household=household,
        meal_plan__status=MealPlan.Status.APPROVED,
    ).select_related("recipe", "meal_plan")


def previous_week_recipe_ids(household, week_start):
    previous = week_start - timedelta(days=7)
    plan = MealPlan.objects.filter(
        household=household,
        week_start=previous,
        status=MealPlan.Status.APPROVED,
    ).first()
    if not plan:
        return set()
    return set(plan.entries.values_list("recipe_id", flat=True))
