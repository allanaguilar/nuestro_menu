from django.contrib import admin

from apps.baby.models import BabyFood, BabyPlan, BabyPlanEntry


@admin.register(BabyFood)
class BabyFoodAdmin(admin.ModelAdmin):
    list_display = ("name", "household", "texture", "is_new", "is_active")
    list_filter = ("texture", "is_new", "is_active")
    search_fields = ("name",)


class BabyPlanEntryInline(admin.TabularInline):
    model = BabyPlanEntry
    extra = 0


@admin.register(BabyPlan)
class BabyPlanAdmin(admin.ModelAdmin):
    list_display = ("household", "week_start")
    inlines = [BabyPlanEntryInline]
