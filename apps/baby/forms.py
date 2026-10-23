from django import forms
from django.db.models import Q

from apps.baby.models import BabyFood


class BabyFoodForm(forms.ModelForm):
    class Meta:
        model = BabyFood
        fields = ("name", "texture", "is_new")
        labels = {
            "name": "Nombre",
            "texture": "Textura",
            "is_new": "Todavía es nuevo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{css} field-input".strip()


class BabyFoodSelect(forms.Select):
    def __init__(self, *args, foods=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.foods = {str(food.pk): food for food in foods or []}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        raw = option["value"]
        food = self.foods.get(str(getattr(raw, "value", raw)))
        if food is None:
            return option
        option["attrs"]["data-texture"] = food.get_texture_display()
        if food.is_new:
            option["attrs"]["data-new"] = "1"
        return option


class BabyDayForm(forms.Form):
    comida = forms.ModelChoiceField(
        queryset=BabyFood.objects.none(),
        required=False,
        empty_label="Sin comida",
        label="Comida",
    )
    merienda = forms.ModelChoiceField(
        queryset=BabyFood.objects.none(),
        required=False,
        empty_label="Sin comida",
        label="Merienda",
    )

    def __init__(self, *args, household=None, lunch=None, snack=None, **kwargs):
        super().__init__(*args, **kwargs)
        lunch_foods = _food_choices(household, lunch)
        snack_foods = _food_choices(household, snack)
        self.fields["comida"].widget = BabyFoodSelect(foods=lunch_foods)
        self.fields["merienda"].widget = BabyFoodSelect(foods=snack_foods)
        self.fields["comida"].queryset = lunch_foods
        self.fields["merienda"].queryset = snack_foods
        for field in self.fields.values():
            field.widget.attrs["class"] = "field-input baby-food-select"


def _food_choices(household, current):
    if household is None:
        return BabyFood.objects.none()
    return (
        BabyFood.objects.filter(household=household)
        .filter(Q(is_active=True) | Q(pk=current))
        .order_by("name")
    )
