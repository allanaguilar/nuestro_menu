from django import forms
from django.db.models import Q

from apps.recipes.models import Recipe


class DishSelect(forms.Select):
    def __init__(self, *args, recipes=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.recipes = {str(recipe.pk): recipe for recipe in recipes or []}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        raw = option["value"]
        recipe = self.recipes.get(str(getattr(raw, "value", raw)))
        if recipe is not None:
            option["attrs"]["data-category"] = recipe.get_category_display()
        return option


class ChangeDishForm(forms.Form):
    recipe = forms.ModelChoiceField(
        queryset=Recipe.objects.none(),
        label="Plato",
        empty_label=None,
    )

    def __init__(self, *args, household=None, current=None, **kwargs):
        super().__init__(*args, **kwargs)
        recipes = Recipe.objects.filter(household=household).filter(
            Q(is_active=True) | Q(pk=current)
        ).order_by("name")
        self.fields["recipe"].widget = DishSelect(recipes=recipes)
        self.fields["recipe"].queryset = recipes
        self.fields["recipe"].widget.attrs["class"] = "field-input dish-select"
        if current:
            self.initial.setdefault("recipe", current)
