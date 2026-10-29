from django import forms
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template import loader


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
        token = self.data.get("invite_token") if self.is_bound else self.initial.get("invite_token")
        self.invited = bool((token or "").strip())
        if self.invited:
            self.fields.pop("first_name", None)
            self.fields.pop("household_name", None)
            self.fields["email"].required = False
            self.fields["email"].label = "Correo"
            self.fields["email"].help_text = "Opcional. Sirve para recuperar la contraseña."
            self.fields["username"].help_text = ""
            self.fields["password1"].help_text = "Al menos 8 caracteres y distinta del usuario."
            self.fields["password2"].required = False
            self.fields["password2"].widget = forms.HiddenInput()
        self._style()

    def validate_password_for_user(self, user, password_field_name="password2"):
        if self.invited:
            password_field_name = "password1"
        super().validate_password_for_user(user, password_field_name)

    def clean(self):
        if self.invited:
            password = self.cleaned_data.get("password1")
            if password:
                self.cleaned_data["password2"] = password
        cleaned = super().clean()
        token = (cleaned.get("invite_token") or "").strip()
        household_name = (cleaned.get("household_name") or "").strip()
        if not token and not household_name:
            self.add_error(
                "household_name",
                "Indica un nombre de hogar o usa un enlace de invitación.",
            )
        return cleaned


class PasswordResetForm(DjangoPasswordResetForm):
    """Reenvía el fallo de Brevo. Django 5 se lo traga y muestra éxito igual."""

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = loader.render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)
        message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        message.send()


class HouseholdSettingsForm(StyledFormMixin, forms.Form):
    name = forms.CharField(label="Nombre del hogar", max_length=120)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
