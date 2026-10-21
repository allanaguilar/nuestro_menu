from django.contrib import admin

from apps.meal_plans.models import MealPlan, MealPlanEntry


class MealPlanEntryInline(admin.TabularInline):
    model = MealPlanEntry
    extra = 0


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ("household", "week_start", "status")
    inlines = [MealPlanEntryInline]
