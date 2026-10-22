from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

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
        self.assertContains(response, "Almuerzos de esta semana")
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


class WeekdayShortTests(TestCase):
    def test_spanish_abbreviations(self):
        self.assertEqual(weekday_short(date(2026, 10, 19)), "Lun")
        self.assertEqual(weekday_short(date(2026, 10, 21)), "Mié")
        self.assertEqual(weekday_short(date(2026, 10, 25)), "Dom")
