import json
from datetime import date
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.test import TestCase, override_settings

from apps.core.mail import EmailDeliveryError
from apps.core.week import weekday_short
from apps.households.services import create_household_for_user


class HealthTests(TestCase):
    def test_health_ok(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


class LoginRedirectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("allan", password="clave-segura-1")
        create_household_for_user(self.user, "Casa")

    def test_login_reaches_dashboard(self):
        response = self.client.post(
            "/cuentas/entrar/",
            {"username": "allan", "password": "clave-segura-1"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Esta semana")
        self.assertContains(response, "Sin plato hoy")
        self.assertLess(len(response.redirect_chain), 4)

    def test_home_does_not_loop(self):
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.get("/", follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/inicio/")
        dashboard = self.client.get("/inicio/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "day-rail")
        self.assertContains(dashboard, "Lun")
        self.assertContains(dashboard, "nav-toggle")
        self.assertContains(dashboard, "Abrir menú")


class PasswordResetPageTests(TestCase):
    def test_send_button_is_centered_and_the_form_navigates(self):
        response = self.client.get("/cuentas/clave/")
        self.assertContains(response, 'class="auth-actions"')
        self.assertContains(response, 'hx-boost="false"')
        self.assertContains(response, ">Enviar<")

    @override_settings(
        EMAIL_BACKEND="apps.core.mail.BrevoEmailBackend",
        BREVO_API_KEY="clave-de-prueba",
        DEFAULT_FROM_EMAIL="Nuestro Menú <allanaguilar.a@gmail.com>",
    )
    def test_known_email_asks_brevo_and_shows_the_done_page(self):
        User.objects.create_user("allan", email="allanaguilar.a@gmail.com", password="clave-segura-1")
        with patch("apps.core.mail.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b"{}"
            response = self.client.post("/cuentas/clave/", {"email": "allanaguilar.a@gmail.com"})
        self.assertRedirects(response, "/cuentas/clave/enviada/")
        payload = json.loads(urlopen.call_args.args[0].data.decode())
        self.assertEqual(payload["to"], [{"email": "allanaguilar.a@gmail.com"}])
        self.assertEqual(payload["sender"]["email"], "allanaguilar.a@gmail.com")
        self.assertIn("cuentas/clave/", payload["textContent"])

    @override_settings(
        EMAIL_BACKEND="apps.core.mail.BrevoEmailBackend",
        BREVO_API_KEY="clave-de-prueba",
    )
    def test_brevo_rejection_stays_on_the_form(self):
        User.objects.create_user("allan", email="allanaguilar.a@gmail.com", password="clave-segura-1")
        error = HTTPError("https://api.brevo.com/v3/smtp/email", 401, "unauthorized", hdrs=None, fp=BytesIO(b""))
        with patch("apps.core.mail.urlopen", side_effect=error):
            response = self.client.post("/cuentas/clave/", {"email": "allanaguilar.a@gmail.com"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No se pudo enviar el correo")


class BrevoBackendTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="apps.core.mail.BrevoEmailBackend",
        BREVO_API_KEY="clave-de-prueba",
        DEFAULT_FROM_EMAIL="Nuestro Menú <origen@example.com>",
    )
    def test_http_error_raises_delivery_error(self):
        error = HTTPError("https://api.brevo.com/v3/smtp/email", 400, "bad", hdrs=None, fp=BytesIO(b""))
        with patch("apps.core.mail.urlopen", side_effect=error):
            with self.assertRaises(EmailDeliveryError):
                send_mail("Asunto", "Cuerpo", None, ["destino@example.com"])


class WeekdayShortTests(TestCase):
    def test_spanish_abbreviations(self):
        self.assertEqual(weekday_short(date(2026, 10, 19)), "Lun")
        self.assertEqual(weekday_short(date(2026, 10, 21)), "Mié")
        self.assertEqual(weekday_short(date(2026, 10, 25)), "Dom")
