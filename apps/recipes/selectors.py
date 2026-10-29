from django.db.models import Q

from apps.recipes.models import Recipe
from apps.recipes.utils import normalize_recipe_name


def recipes_for_household(household):
    return Recipe.objects.filter(household=household)


def list_active_recipes(household):
    return recipes_for_household(household).filter(is_active=True)


def recipe_count(household):
    return recipes_for_household(household).count()


def search_recipes(
    household, *, query="", category="", sort="name", include_archived=False, archived_only=False
):
    qs = recipes_for_household(household)
    if archived_only:
        qs = qs.filter(is_active=False)
    elif not include_archived:
        qs = qs.filter(is_active=True)
    if query:
        qs = qs.filter(
            Q(name__icontains=query.strip()) | Q(notes__icontains=query.strip())
        )
    if category:
        qs = qs.filter(category=category)
    if sort == "recent":
        qs = qs.order_by("-created_at", "name")
    else:
        qs = qs.order_by("name")
    return qs


def find_duplicates(household, name, exclude_id=None):
    qs = recipes_for_household(household).filter(
        normalized_name=normalize_recipe_name(name)
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs
