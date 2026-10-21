from django.contrib import admin

from apps.recipes.models import Recipe


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "household", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name",)
