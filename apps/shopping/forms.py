from django import forms


class AddShoppingItemForm(forms.Form):
    name = forms.CharField(
        label="Qué falta",
        max_length=120,
        error_messages={"required": "Escribe lo que falta."},
        widget=forms.TextInput(
            attrs={
                "class": "field-input",
                "placeholder": "Yogures de fresa",
                "autocomplete": "off",
                "maxlength": "120",
            }
        ),
    )
