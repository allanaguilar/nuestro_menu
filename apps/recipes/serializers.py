from rest_framework import serializers

from apps.recipes.models import Recipe
from apps.recipes.selectors import find_duplicates


class RecipeSerializer(serializers.ModelSerializer):
    confirm_duplicate = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "name",
            "normalized_name",
            "category",
            "prep_time_minutes",
            "ingredients",
            "steps",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
            "confirm_duplicate",
        )
        read_only_fields = ("id", "normalized_name", "created_at", "updated_at")

    def validate(self, attrs):
        household = self.context["household"]
        name = attrs.get("name") or getattr(self.instance, "name", None)
        confirm = attrs.pop("confirm_duplicate", False)
        if name:
            duplicates = find_duplicates(
                household,
                name,
                exclude_id=self.instance.pk if self.instance else None,
            )
            if duplicates.exists() and not confirm:
                raise serializers.ValidationError(
                    "Ya existe una receta con un nombre equivalente. "
                    "Envía confirm_duplicate=true para guardarla."
                )
        return attrs

    def create(self, validated_data):
        validated_data["household"] = self.context["household"]
        return super().create(validated_data)
