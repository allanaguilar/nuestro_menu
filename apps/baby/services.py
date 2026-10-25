from datetime import timedelta

from django.core.exceptions import ValidationError

from apps.baby.models import BabyFood, BabyPlan, BabyPlanEntry
from apps.baby.selectors import active_baby_foods, get_baby_plan
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


def suggest_baby_day(household, week_start, day):
    start = monday_of(week_start)
    if day < start or day > start + timedelta(days=6):
        raise BabyPlanningError("El día no pertenece a esta semana.")
    foods = list(active_baby_foods(household))
    if not foods:
        raise BabyPlanningError("No hay alimentos para proponer.")
    plan = get_baby_plan(household, start)
    current = {}
    if plan:
        current = {entry.slot: entry.food_id for entry in plan.entries.filter(day=day)}
    lunch = _next_food(foods, current.get(BabyPlanEntry.Slot.LUNCH))
    snack = _next_food(foods, current.get(BabyPlanEntry.Slot.SNACK))
    if lunch is not None and snack is not None and lunch.pk == snack.pk and len(foods) > 1:
        snack = _next_food(foods, lunch.pk)
    changed = False
    if lunch is not None:
        set_baby_meal(household, start, day, BabyPlanEntry.Slot.LUNCH, lunch)
        changed = True
    if snack is not None:
        set_baby_meal(household, start, day, BabyPlanEntry.Slot.SNACK, snack)
        changed = True
    if not changed:
        raise BabyPlanningError("No hay otro alimento.")


def _next_food(foods, current_id):
    if current_id is None:
        return foods[0]
    ids = [food.id for food in foods]
    if current_id not in ids:
        return foods[0]
    if len(foods) == 1:
        return None
    return foods[(ids.index(current_id) + 1) % len(foods)]


def new_foods_this_week(plan):
    if plan is None:
        return BabyFood.objects.none()
    return BabyFood.objects.filter(
        plan_entries__plan=plan, is_new=True
    ).distinct()
