from rest_framework import serializers

from apps.meal_plans.models import MealPlan, MealPlanEntry
from apps.recipes.serializers import RecipeSerializer


class MealPlanEntrySerializer(serializers.ModelSerializer):
    recipe = RecipeSerializer(read_only=True)

    class Meta:
        model = MealPlanEntry
        fields = ("id", "day", "recipe", "selection_source", "updated_at")


class MealPlanSerializer(serializers.ModelSerializer):
    entries = MealPlanEntrySerializer(many=True, read_only=True)

    class Meta:
        model = MealPlan
        fields = (
            "id",
            "week_start",
            "status",
            "generated_at",
            "approved_at",
            "created_at",
            "updated_at",
            "entries",
        )
