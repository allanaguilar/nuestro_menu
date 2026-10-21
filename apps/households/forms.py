from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class StyledFormMixin:
    def _style(self):
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} field-input".strip()


class SignUpForm(StyledFormMixin, UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=150)
    email = forms.EmailField(label="Correo electrónico")
    household_name = forms.CharField(
        label="Nombre del hogar",
        max_length=120,
        required=False,
        help_text="Obligatorio si no usas un enlace de invitación.",
    )
    invite_token = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = User
        fields = ("username", "first_name", "email", "password1", "password2")
        labels = {
            "username": "Usuario",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Repetir contraseña"
        self._style()

    def clean(self):
        cleaned = super().clean()
        token = (cleaned.get("invite_token") or "").strip()
        household_name = (cleaned.get("household_name") or "").strip()
        if not token and not household_name:
            self.add_error(
                "household_name",
                "Indica un nombre de hogar o usa un enlace de invitación.",
            )
        return cleaned


class HouseholdSettingsForm(StyledFormMixin, forms.Form):
    name = forms.CharField(label="Nombre del hogar", max_length=120)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
