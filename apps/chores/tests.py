from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from apps.chores.models import Chore
from apps.chores.selectors import chore_is_visible, open_chores
from apps.chores.services import add_chore, set_chore_done
from apps.households.services import accept_invite, create_household_for_user, create_invite


class ChoreTests(TestCase):
    def setUp(self):
        self.allan = User.objects.create_user(
            "allan", password="clave-segura-1", first_name="Allan"
        )
        self.naiara = User.objects.create_user(
            "naiara", password="clave-segura-1", first_name="Naiara"
        )
        self.household = create_household_for_user(self.allan, "Casa")
        accept_invite(self.naiara, create_invite(self.household, self.allan).token)
        self.today = date(2026, 11, 3)
        self.client.login(username="allan", password="clave-segura-1")

    def test_daily_stays_struck_today_and_returns_tomorrow(self):
        chore = add_chore(self.household, "Regar las plantas", Chore.Cadence.DAILY, self.naiara, self.today)
        set_chore_done(chore, self.today, True)
        today = open_chores(self.household, self.today)
        self.assertEqual(today["hoy"][0].meta, "Cada día · Naiara")
        self.assertTrue(today["hoy"][0].is_done)
        self.assertEqual(today["pending"], 0)
        tomorrow = open_chores(self.household, self.today + timedelta(days=1))
        self.assertFalse(tomorrow["hoy"][0].is_done)
        self.assertEqual(tomorrow["pending"], 1)

    def test_someday_disappears_the_next_day(self):
        chore = add_chore(self.household, "Recoger un paquete", Chore.Cadence.SOMEDAY, self.allan, self.today)
        set_chore_done(chore, self.today, True)
        self.assertTrue(chore_is_visible(chore, self.today))
        page = open_chores(self.household, self.today + timedelta(days=1))
        self.assertEqual(page["cuando"], [])
        self.assertFalse(Chore.objects.filter(pk=chore.pk).exists())

    def test_weekly_hides_until_the_next_week(self):
        chore = add_chore(self.household, "Limpiar la casa", Chore.Cadence.WEEKLY, None, self.today)
        set_chore_done(chore, self.today, True)
        chore.refresh_from_db()
        self.assertTrue(chore_is_visible(chore, self.today))
        self.assertFalse(chore_is_visible(chore, self.today + timedelta(days=1)))
        self.assertTrue(chore_is_visible(chore, self.today + timedelta(days=7)))

    def test_page_adds_and_checks_a_chore(self):
        home = self.client.get("/inicio/")
        self.assertContains(home, 'href="/por-hacer/"')
        self.assertContains(home, "nada pendiente")
        added = self.client.post(
            "/por-hacer/",
            {"title": "Hacer la comida", "cadence": "dia", "assignee": ""},
        )
        self.assertRedirects(added, "/por-hacer/")
        page = self.client.get("/por-hacer/")
        self.assertContains(page, "Hacer la comida")
        self.assertContains(page, "Cada día")
        self.assertContains(page, "Hoy")
        chore = Chore.objects.get(title="Hacer la comida")
        checked = self.client.post(f"/por-hacer/{chore.pk}/hecho/", {"done": "1"})
        self.assertRedirects(checked, "/por-hacer/")
        done = self.client.get("/por-hacer/")
        self.assertContains(done, "is-done")
        blank = self.client.post("/por-hacer/", {"title": "  ", "cadence": "hoy"})
        self.assertContains(blank, "Escribe la tarea.")

    def test_delete_removes_a_repeating_chore(self):
        chore = add_chore(self.household, "Regar las plantas", Chore.Cadence.DAILY, None, self.today)
        page = self.client.get("/por-hacer/")
        self.assertContains(page, "Borrar Regar las plantas")
        self.assertContains(page, "¿Deseas borrar «Regar las plantas»?")
        response = self.client.post(f"/por-hacer/{chore.pk}/borrar/")
        self.assertRedirects(response, "/por-hacer/")
        self.assertFalse(Chore.objects.filter(pk=chore.pk).exists())
        self.assertNotContains(self.client.get("/por-hacer/"), "Regar las plantas")

    def test_other_household_cannot_toggle(self):
        other = User.objects.create_user("vecino", password="clave-segura-1")
        house = create_household_for_user(other, "Otra")
        chore = add_chore(house, "Regar", Chore.Cadence.TODAY, None, self.today)
        response = self.client.post(f"/por-hacer/{chore.pk}/hecho/", {"done": "1"})
        self.assertEqual(response.status_code, 404)
        chore.refresh_from_db()
        self.assertIsNone(chore.done_on)
        denied = self.client.post(f"/por-hacer/{chore.pk}/borrar/")
        self.assertEqual(denied.status_code, 404)
        self.assertTrue(Chore.objects.filter(pk=chore.pk).exists())
