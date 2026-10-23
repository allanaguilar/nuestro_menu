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
        self.fields["comida"].queryset = _food_choices(household, lunch)
        self.fields["merienda"].queryset = _food_choices(household, snack)
        for field in self.fields.values():
            field.widget.attrs["class"] = "field-input"


def _food_choices(household, current):
    if household is None:
        return BabyFood.objects.none()
    return (
        BabyFood.objects.filter(household=household)
        .filter(Q(is_active=True) | Q(pk=current))
        .order_by("name")
    )
