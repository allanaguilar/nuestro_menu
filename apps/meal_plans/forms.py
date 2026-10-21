from django import forms

from apps.recipes.models import Recipe


class ChangeDishForm(forms.Form):
    recipe = forms.ModelChoiceField(queryset=Recipe.objects.none(), label="Plato")

    def __init__(self, *args, household=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Recipe.objects.filter(household=household, is_active=True).order_by("name")
        self.fields["recipe"].queryset = qs
        self.fields["recipe"].widget.attrs["class"] = "field-input"
