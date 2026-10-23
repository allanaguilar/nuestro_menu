from apps.baby.models import BabyPlan, BabyPlanEntry
from apps.core.week import monday_of


def get_baby_plan(household, week_start):
    return (
        BabyPlan.objects.filter(household=household, week_start=monday_of(week_start))
        .prefetch_related("entries__food")
        .first()
    )


def baby_meals_on(household, day):
    plan = BabyPlan.objects.filter(
        household=household, week_start=monday_of(day)
    ).first()
    if plan is None:
        return {}
    return {
        entry.slot: entry
        for entry in plan.entries.filter(day=day).select_related("food")
    }


def active_baby_foods(household):
    return BabyFoodQuery(household)


class BabyFoodQuery:
    def __new__(cls, household):
        from apps.baby.models import BabyFood

        return BabyFood.objects.filter(household=household, is_active=True).order_by("name")
