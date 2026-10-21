from django.contrib import admin

from apps.preferences.models import RecipePreference


@admin.register(RecipePreference)
class RecipePreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe", "rating", "is_favorite", "is_avoided")
