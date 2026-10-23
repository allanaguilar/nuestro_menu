from datetime import timedelta

from django.core.exceptions import ValidationError

from apps.baby.models import BabyFood, BabyPlan, BabyPlanEntry
from apps.core.week import monday_of


class BabyPlanningError(Exception):
    pass


def set_baby_meal(household, week_start, day, slot, food):
    start = monday_of(week_start)
    if day < start or day > start + timedelta(days=6):
        raise BabyPlanningError("El día no pertenece a esta semana.")
    if slot not in BabyPlanEntry.Slot.values:
        raise BabyPlanningError("Ese hueco no existe.")
    if food is not None:
        if food.household_id != household.id:
            raise BabyPlanningError("El alimento no es de este hogar.")
        if not food.is_active:
            raise BabyPlanningError("Ese alimento está archivado.")
    plan, _created = BabyPlan.objects.get_or_create(
        household=household, week_start=start
    )
    if food is None:
        BabyPlanEntry.objects.filter(plan=plan, day=day, slot=slot).delete()
        return None
    try:
        entry, _created = BabyPlanEntry.objects.update_or_create(
            plan=plan, day=day, slot=slot, defaults={"food": food}
        )
    except ValidationError as exc:
        raise BabyPlanningError("No se ha podido guardar ese alimento.") from exc
    return entry


def new_foods_this_week(plan):
    if plan is None:
        return BabyFood.objects.none()
    return BabyFood.objects.filter(
        plan_entries__plan=plan, is_new=True
    ).distinct()
