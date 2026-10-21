"""Generador de menús semanales.

Limitación documentada: la «última vez que se comió» se aproxima con los
menús aprobados, no con comidas realmente confirmadas en el plato.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from datetime import date, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.week import monday_of, week_dates
from apps.households.selectors import list_members
from apps.meal_plans.models import MealPlan, MealPlanEntry
from apps.meal_plans.selectors import previous_week_recipe_ids
from apps.preferences.models import RecipePreference
from apps.recipes.models import Recipe


class GeneratorError(Exception):
    pass


class InsufficientRecipesError(GeneratorError):
    pass


class ApprovedPlanProtectedError(GeneratorError):
    pass


def _tokenize(name: str) -> set[str]:
    stop = {"de", "del", "la", "el", "los", "las", "con", "y", "en", "al"}
    return {part for part in name.casefold().replace(",", " ").split() if part not in stop and len(part) > 2}


def _similarity(a: Recipe, b: Recipe) -> float:
    ta, tb = _tokenize(a.name), _tokenize(b.name)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    score = inter / union
    if a.category == b.category:
        score += 0.15
    return score


def _history(household):
    """Usa solo planes aprobados como aproximación histórica."""
    last_used = {}
    frequency = Counter()
    entries = MealPlanEntry.objects.filter(
        meal_plan__household=household,
        meal_plan__status=MealPlan.Status.APPROVED,
    ).select_related("meal_plan")
    for entry in entries:
        frequency[entry.recipe_id] += 1
        previous = last_used.get(entry.recipe_id)
        if previous is None or entry.day > previous:
            last_used[entry.recipe_id] = entry.day
    return last_used, frequency


def _preference_index(household):
    members = list(list_members(household))
    prefs = RecipePreference.objects.filter(
        user_id__in=[m.user_id for m in members],
        recipe__household=household,
    )
    by_recipe = defaultdict(list)
    for pref in prefs:
        by_recipe[pref.recipe_id].append(pref)
    return members, by_recipe


def eligible_recipes(household, week_start: date) -> list[Recipe]:
    avoided_ids = set(
        RecipePreference.objects.filter(
            recipe__household=household, is_avoided=True
        ).values_list("recipe_id", flat=True)
    )
    previous_ids = previous_week_recipe_ids(household, week_start)
    recipes = list(
        Recipe.objects.filter(household=household, is_active=True).exclude(
            id__in=avoided_ids
        )
    )
    return [recipe for recipe in recipes if recipe.id not in previous_ids]


def score_recipe(recipe: Recipe, *, today: date, last_used, frequency, prefs, rng: random.Random) -> float:
    last = last_used.get(recipe.id)
    if last is None:
        recency = 3.0
    else:
        days = max((today - last).days, 0)
        recency = min(days / 21.0, 3.0)
    freq_penalty = -0.35 * frequency.get(recipe.id, 0)
    recipe_prefs = prefs.get(recipe.id, [])
    fav_count = sum(1 for item in recipe_prefs if item.is_favorite)
    ratings = [item.rating for item in recipe_prefs if item.rating]
    favorite_bonus = 0.9 * fav_count
    if fav_count >= 2:
        favorite_bonus += 0.7
    rating_bonus = 0.0
    if ratings:
        rating_bonus = (sum(ratings) / len(ratings) - 3.0) * 0.45
    noise = rng.uniform(-0.18, 0.18)
    return recency + freq_penalty + favorite_bonus + rating_bonus + noise


def evaluate_combination(recipes: list[Recipe], individual_scores: dict) -> float:
    total = sum(individual_scores[recipe.id] for recipe in recipes)
    categories = Counter(recipe.category for recipe in recipes)
    variety_penalty = 0.0
    for count in categories.values():
        if count > 2:
            variety_penalty += (count - 2) * 1.4
        if count > 3:
            variety_penalty += (count - 3) * 1.0
    similarity_penalty = 0.0
    for i, left in enumerate(recipes):
        for right in recipes[i + 1 :]:
            sim = _similarity(left, right)
            if sim > 0.35:
                similarity_penalty += sim * 1.2
    unique_categories = len(categories)
    variety_bonus = unique_categories * 0.35
    return total + variety_bonus - variety_penalty - similarity_penalty


def _weighted_sample(candidates: list[Recipe], scores: dict, rng: random.Random, k: int) -> list[Recipe]:
    pool = list(candidates)
    chosen = []
    while pool and len(chosen) < k:
        weights = []
        for recipe in pool:
            weights.append(max(scores[recipe.id], 0.05))
        total = sum(weights)
        pick = rng.random() * total
        running = 0.0
        selected = pool[-1]
        for recipe, weight in zip(pool, weights):
            running += weight
            if running >= pick:
                selected = recipe
                break
        chosen.append(selected)
        pool.remove(selected)
        # Penalize same category remaining in this combination.
        for recipe in pool:
            if recipe.category == selected.category:
                scores[recipe.id] = scores.get(recipe.id, 0) - 0.55
    return chosen


def build_best_combination(candidates: list[Recipe], scores: dict, rng: random.Random, max_combinations: int):
    if len(candidates) < 7:
        raise InsufficientRecipesError(
            "No hay suficientes recetas activas y compatibles para generar siete almuerzos distintos."
        )
    best = None
    best_score = -math.inf
    attempts = max(1, max_combinations)
    for _ in range(attempts):
        working_scores = dict(scores)
        combo = _weighted_sample(candidates, working_scores, rng, 7)
        if len({item.id for item in combo}) < 7:
            continue
        quality = evaluate_combination(combo, scores)
        if quality > best_score:
            best_score = quality
            best = combo
    if best is None:
        raise InsufficientRecipesError("No se pudo construir un menú válido.")
    return best, best_score


@transaction.atomic
def generate_week_menu(household, week_start: date, user, *, seed=None, confirm_replace=False):
    week_start = monday_of(week_start)
    existing = (
        MealPlan.objects.select_for_update()
        .filter(household=household, week_start=week_start)
        .first()
    )
    if existing and existing.status == MealPlan.Status.APPROVED and not confirm_replace:
        raise ApprovedPlanProtectedError(
            "Este menú ya está aprobado. Confirma si quieres sustituirlo."
        )

    candidates = eligible_recipes(household, week_start)
    if len(candidates) < 7:
        raise InsufficientRecipesError(
            "Necesitas al menos siete recetas activas, no evitadas y distintas "
            "para generar la semana. Añade recetas o quita exclusiones."
        )

    rng = random.Random(seed)
    last_used, frequency = _history(household)
    _members, prefs = _preference_index(household)
    today = timezone.localdate()
    scores = {
        recipe.id: score_recipe(
            recipe,
            today=today,
            last_used=last_used,
            frequency=frequency,
            prefs=prefs,
            rng=rng,
        )
        for recipe in candidates
    }
    max_combinations = getattr(settings, "GENERATOR_MAX_COMBINATIONS", 200)
    combination, _quality = build_best_combination(
        candidates, scores, rng, max_combinations
    )

    if existing is None:
        plan = MealPlan(
            household=household,
            week_start=week_start,
            status=MealPlan.Status.DRAFT,
            created_by=user,
            generated_at=timezone.now(),
            approved_at=None,
        )
        plan.save()
    else:
        plan = existing
        plan.status = MealPlan.Status.DRAFT
        plan.generated_at = timezone.now()
        plan.approved_at = None
        plan.created_by = user
        plan.save(update_fields=["status", "generated_at", "approved_at", "created_by", "updated_at"])
        plan.entries.all().delete()

    days = week_dates(week_start)
    for day, recipe in zip(days, combination):
        MealPlanEntry.objects.create(
            meal_plan=plan,
            day=day,
            recipe=recipe,
            selection_source=MealPlanEntry.Source.ALGORITHM,
        )
    if plan.entries.count() != 7:
        raise GeneratorError("El plan generado está incompleto y no se guardará.")
    return plan
