from apps.preferences.models import RecipePreference


def avoided_recipe_ids(household):
    return set(
        RecipePreference.objects.filter(
            recipe__household=household, is_avoided=True
        ).values_list("recipe_id", flat=True)
    )


def preferences_for_user(user, household):
    return RecipePreference.objects.select_related("recipe").filter(
        user=user, recipe__household=household
    )


def preference_map(user, recipe_ids):
    return {
        pref.recipe_id: pref
        for pref in RecipePreference.objects.filter(user=user, recipe_id__in=recipe_ids)
    }
