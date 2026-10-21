from rest_framework import serializers

from apps.preferences.models import RecipePreference


class RecipePreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipePreference
        fields = (
            "id",
            "recipe",
            "rating",
            "is_favorite",
            "is_avoided",
            "updated_at",
        )
        read_only_fields = ("id", "updated_at")
