from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.core.week import monday_of
from apps.meal_plans.models import MealPlan, MealPlanEntry
from apps.meal_plans.selectors import get_plan_for_week
from apps.meal_plans.services.generator import (
    GeneratorError,
    eligible_recipes,
)
from apps.recipes.models import Recipe


class PlanningError(GeneratorError):
    pass


@transaction.atomic
def change_entry(household, week_start: date, day: date, recipe: Recipe, user=None):
    week_start = monday_of(week_start)
    if recipe.household_id != household.id:
        raise PlanningError("La receta no pertenece a este hogar.")
    if not recipe.is_active:
        raise PlanningError("No se puede elegir una receta archivada.")
    plan = get_plan_for_week(household, week_start)
    if plan is None:
        raise PlanningError("No hay un menú para esa semana.")
    if day < plan.week_start or day > plan.week_end:
        raise PlanningError("El día no pertenece a esta semana.")
    entry = plan.entries.filter(day=day).first()
    if not recipe.is_meal and (entry is None or entry.recipe_id != recipe.id):
        raise PlanningError("Esta receta es un apunte y no sale como comida de un día.")
    if entry is None:
        entry = MealPlanEntry(meal_plan=plan, day=day)
    entry.recipe = recipe
    entry.selection_source = MealPlanEntry.Source.MANUAL
    entry.save()
    if plan.status == MealPlan.Status.APPROVED:
        plan.status = MealPlan.Status.DRAFT
        plan.approved_at = None
        plan.save(update_fields=["status", "approved_at", "updated_at"])
    return entry


def suggest_alternative(household, week_start: date, day: date):
    plan = get_plan_for_week(household, week_start)
    if plan is None:
        raise PlanningError("No hay un menú para esa semana.")
    entry = plan.entries.filter(day=day).select_related("recipe").first()
    if entry is None:
        raise PlanningError("Ese día no tiene plato.")
    used = set(plan.entries.values_list("recipe_id", flat=True))
    candidates = [
        recipe
        for recipe in eligible_recipes(household, week_start)
        if recipe.id not in used
    ]
    if not candidates:
        raise PlanningError("No hay alternativas disponibles esta semana.")
    current_category = entry.recipe.category
    preferred = [recipe for recipe in candidates if recipe.category != current_category]
    pool = preferred or candidates
    pool.sort(key=lambda recipe: recipe.name)
    return pool[0]


@transaction.atomic
def approve_plan(household, week_start: date):
    week_start = monday_of(week_start)
    plan = (
        MealPlan.objects.select_for_update()
        .filter(household=household, week_start=week_start)
        .first()
    )
    if plan is None:
        raise PlanningError("No hay un menú para aprobar.")
    if plan.entries.count() != 7:
        raise PlanningError("No se puede aprobar un menú incompleto.")
    plan.status = MealPlan.Status.APPROVED
    plan.approved_at = timezone.now()
    plan.save(update_fields=["status", "approved_at", "updated_at"])
    return plan
