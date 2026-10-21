from apps.recipes.models import Recipe


def archive_recipe(recipe: Recipe):
    recipe.is_active = False
    recipe.save(update_fields=["is_active", "updated_at"])
    return recipe


def reactivate_recipe(recipe: Recipe):
    recipe.is_active = True
    recipe.save(update_fields=["is_active", "updated_at"])
    return recipe
