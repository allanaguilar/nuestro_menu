from datetime import date, timedelta
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from apps.chores.models import Chore, ChorePhoto
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
        plain = self.client.post("/por-hacer/", {"title": "Sacar la basura"})
        self.assertRedirects(plain, "/por-hacer/")
        quick = Chore.objects.get(title="Sacar la basura")
        self.assertEqual(quick.cadence, Chore.Cadence.TODAY)
        self.assertIsNone(quick.assignee_id)

    def test_edit_updates_the_text_when_and_who(self):
        chore = add_chore(self.household, "Recoger un paquete", Chore.Cadence.TODAY, None, self.today)
        page = self.client.get("/por-hacer/")
        self.assertContains(page, "Editar Recoger un paquete")
        self.assertContains(page, 'id="editar-modal"')
        saved = self.client.post(
            f"/por-hacer/{chore.pk}/editar/",
            {
                "editar-title": "Código del paquete",
                "editar-cadence": "dia",
                "editar-assignee": self.naiara.pk,
            },
        )
        self.assertRedirects(saved, "/por-hacer/")
        chore.refresh_from_db()
        self.assertEqual(chore.title, "Código del paquete")
        self.assertEqual(chore.cadence, Chore.Cadence.DAILY)
        self.assertEqual(chore.assignee, self.naiara)
        self.assertIsNone(chore.weekday)
        blank = self.client.post(
            f"/por-hacer/{chore.pk}/editar/",
            {"editar-title": "  ", "editar-cadence": "hoy", "editar-assignee": ""},
            follow=True,
        )
        self.assertContains(blank, "Escribe la tarea.")
        chore.refresh_from_db()
        self.assertEqual(chore.title, "Código del paquete")

    def test_other_household_cannot_edit(self):
        other = User.objects.create_user("vecino-editar", password="clave-segura-1")
        house = create_household_for_user(other, "Otra")
        chore = add_chore(house, "Regar", Chore.Cadence.TODAY, None, self.today)
        denied = self.client.post(
            f"/por-hacer/{chore.pk}/editar/",
            {"editar-title": "Ajeno", "editar-cadence": "hoy", "editar-assignee": ""},
        )
        self.assertEqual(denied.status_code, 404)
        chore.refresh_from_db()
        self.assertEqual(chore.title, "Regar")

    def test_delete_removes_a_repeating_chore(self):
        chore = add_chore(self.household, "Regar las plantas", Chore.Cadence.DAILY, None, self.today)
        page = self.client.get("/por-hacer/")
        self.assertContains(page, "Borrar Regar las plantas")
        self.assertContains(page, "¿Deseas borrar «Regar las plantas»?")
        response = self.client.post(f"/por-hacer/{chore.pk}/borrar/")
        self.assertRedirects(response, "/por-hacer/")
        self.assertFalse(Chore.objects.filter(pk=chore.pk).exists())
        self.assertNotContains(self.client.get("/por-hacer/"), "Regar las plantas")

    def _png(self):
        buffer = BytesIO()
        Image.new("RGB", (16, 8), "red").save(buffer, format="PNG")
        return SimpleUploadedFile("codigo.png", buffer.getvalue(), content_type="image/png")

    def test_photo_is_saved_on_the_chore_and_shown_in_a_modal(self):
        chore = add_chore(self.household, "Recoger un paquete", Chore.Cadence.TODAY, self.allan, self.today)
        page = self.client.get("/por-hacer/")
        self.assertContains(page, "Añadir foto a Recoger un paquete")
        self.assertContains(page, 'id="foto-modal"')
        saved = self.client.post(f"/por-hacer/{chore.pk}/foto/", {"foto": self._png()})
        self.assertRedirects(saved, "/por-hacer/")
        second = self.client.post(f"/por-hacer/{chore.pk}/foto/", {"foto": self._png()})
        self.assertRedirects(second, "/por-hacer/")
        photos = list(ChorePhoto.objects.filter(chore=chore).order_by("created_at"))
        self.assertEqual(len(photos), 2)
        self.assertEqual(photos[0].content_type, "image/jpeg")
        self.assertLess(len(photos[0].content), 20000)
        again = self.client.get("/por-hacer/")
        self.assertContains(again, "Añadir foto a Recoger un paquete")
        self.assertContains(again, "Borrar foto")
        self.assertEqual(again.content.count(b"chore-photo-open"), 2)
        image = self.client.get(f"/por-hacer/{chore.pk}/foto/{photos[0].pk}/")
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image["Content-Type"], "image/jpeg")
        self.assertTrue(image.content.startswith(b"\xff\xd8"))
        removed = self.client.post(f"/por-hacer/{chore.pk}/foto/{photos[0].pk}/borrar/")
        self.assertRedirects(removed, "/por-hacer/")
        self.assertEqual(ChorePhoto.objects.filter(chore=chore).count(), 1)

    def test_photo_rejects_a_file_that_is_not_an_image(self):
        chore = add_chore(self.household, "Recoger un paquete", Chore.Cadence.TODAY, None, self.today)
        upload = SimpleUploadedFile("nota.txt", b"no es una foto", content_type="text/plain")
        response = self.client.post(f"/por-hacer/{chore.pk}/foto/", {"foto": upload}, follow=True)
        self.assertRedirects(response, "/por-hacer/", fetch_redirect_response=False)
        self.assertFalse(ChorePhoto.objects.filter(chore=chore).exists())
        self.assertContains(response, "Esa foto no se puede usar.")

    def test_other_household_cannot_see_the_photo(self):
        other = User.objects.create_user("vecino", password="clave-segura-1")
        house = create_household_for_user(other, "Otra")
        chore = add_chore(house, "Recoger", Chore.Cadence.TODAY, None, self.today)
        self.client.force_login(other)
        self.client.post(f"/por-hacer/{chore.pk}/foto/", {"foto": self._png()})
        photo = ChorePhoto.objects.get(chore=chore)
        self.client.force_login(self.allan)
        hidden = self.client.get(f"/por-hacer/{chore.pk}/foto/{photo.pk}/")
        self.assertEqual(hidden.status_code, 404)
        denied = self.client.post(f"/por-hacer/{chore.pk}/foto/{photo.pk}/borrar/")
        self.assertEqual(denied.status_code, 404)
        self.assertTrue(ChorePhoto.objects.filter(pk=photo.pk).exists())

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
