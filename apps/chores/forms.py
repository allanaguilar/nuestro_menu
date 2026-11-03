from django import forms
from django.contrib.auth.models import User

from apps.chores.models import Chore


class MemberChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.first_name or obj.username


class AddChoreForm(forms.Form):
    title = forms.CharField(
        label="Tarea",
        max_length=80,
        error_messages={"required": "Escribe la tarea."},
        widget=forms.TextInput(
            attrs={
                "class": "field-input",
                "placeholder": "Recoger un paquete",
                "autocomplete": "off",
                "maxlength": "80",
            }
        ),
    )
    cadence = forms.ChoiceField(
        label="Cuándo",
        choices=Chore.Cadence.choices,
        initial=Chore.Cadence.TODAY,
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    assignee = MemberChoiceField(
        label="Quién",
        queryset=User.objects.none(),
        required=False,
        empty_label="Cualquiera",
        widget=forms.Select(attrs={"class": "field-input"}),
    )
