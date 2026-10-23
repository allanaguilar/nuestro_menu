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


class BabyMealForm(forms.Form):
    food = forms.ModelChoiceField(
        queryset=BabyFood.objects.none(),
        required=False,
        empty_label="Sin comida",
        label="",
    )

    def __init__(self, *args, household=None, current=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = BabyFood.objects.none()
        if household is not None:
            queryset = BabyFood.objects.filter(household=household).filter(
                Q(is_active=True) | Q(pk=current)
            ).order_by("name")
        self.fields["food"].queryset = queryset
        self.fields["food"].widget.attrs["class"] = "field-input"
