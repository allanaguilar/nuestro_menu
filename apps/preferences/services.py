from apps.preferences.models import RecipePreference


def upsert_preference(user, recipe, **fields):
    pref, _created = RecipePreference.objects.get_or_create(user=user, recipe=recipe)
    for key, value in fields.items():
        setattr(pref, key, value)
    if pref.is_avoided:
        pref.is_favorite = False
    pref.save()
    return pref


def toggle_favorite(user, recipe):
    pref, _created = RecipePreference.objects.get_or_create(user=user, recipe=recipe)
    pref.is_favorite = not pref.is_favorite
    if pref.is_favorite:
        pref.is_avoided = False
    pref.save()
    return pref
