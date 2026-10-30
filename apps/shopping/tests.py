import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.households.models import HouseholdMembership
from apps.households.services import create_household_for_user
from apps.shopping.models import ShoppingItem, ShoppingPushSubscription


class ShoppingListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("allan", password="clave-segura-1")
        self.partner = User.objects.create_user("pareja", password="clave-segura-1")
        self.other_user = User.objects.create_user("vecino", password="clave-segura-1")
        self.household = create_household_for_user(self.user, "Casa")
        HouseholdMembership.objects.create(
            household=self.household,
            user=self.partner,
            role=HouseholdMembership.Role.MEMBER,
        )
        self.other = create_household_for_user(self.other_user, "Otra")
        self.client.login(username="allan", password="clave-segura-1")

    def test_empty_list_invites_the_next_item(self):
        response = self.client.get("/lista/")
        self.assertContains(response, "La lista está al día. Escribe lo que falte.")
        self.assertContains(response, "Qué falta")
        self.assertContains(response, ">Añadir<")

    def test_add_shows_the_item_under_sin_pasillo(self):
        response = self.client.post("/lista/anadir/", {"name": "  Leche  "})
        self.assertRedirects(response, "/lista/")
        page = self.client.get("/lista/")
        self.assertContains(page, "Leche")
        self.assertContains(page, "Sin pasillo")
        self.assertLess(page.content.find(b"shop-add"), page.content.find(b"shop-board"))
        self.assertContains(page, "Queda 1")
        self.assertEqual(ShoppingItem.objects.get().normalized_name, "leche")

    def test_duplicate_stays_on_the_list_once(self):
        self.client.post("/lista/anadir/", {"name": "Leche"})
        response = self.client.post("/lista/anadir/", {"name": "leche"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya está en la lista.")
        self.assertEqual(ShoppingItem.objects.filter(household=self.household).count(), 1)

    def test_aisle_groups_the_item_and_check_moves_it_to_the_cart(self):
        self.client.post("/lista/anadir/", {"name": "Tomates"})
        item = ShoppingItem.objects.get()
        moved = self.client.post(f"/lista/{item.pk}/pasillo/", {"aisle": "verduras"})
        self.assertRedirects(moved, "/lista/")
        page = self.client.get("/lista/")
        self.assertContains(page, 'id="pasillo-verduras"')
        self.assertContains(page, "fa-carrot")
        self.assertContains(page, "Verduras")
        self.assertContains(page, 'value="verduras" selected')
        self.assertNotContains(page, "Frescos")
        checked = self.client.post(f"/lista/{item.pk}/hecho/", {"done": "1"})
        self.assertRedirects(checked, "/lista/")
        cart = self.client.get("/lista/")
        self.assertContains(cart, "En el carro")
        self.assertContains(cart, "Vaciar lo comprado")
        self.assertContains(cart, "No queda nada")
        cleared = self.client.post("/lista/vaciar/")
        self.assertRedirects(cleared, "/lista/")
        self.assertFalse(ShoppingItem.objects.exists())

    def test_partner_sees_the_same_list_and_another_home_cannot_change_it(self):
        self.client.post("/lista/anadir/", {"name": "Arroz"})
        item = ShoppingItem.objects.get()
        self.client.login(username="pareja", password="clave-segura-1")
        shared = self.client.get("/lista/")
        self.assertContains(shared, "Arroz")
        self.client.login(username="vecino", password="clave-segura-1")
        foreign = self.client.post(f"/lista/{item.pk}/hecho/", {"done": "1"})
        self.assertEqual(foreign.status_code, 404)
        item.refresh_from_db()
        self.assertFalse(item.done)

    def test_check_and_aisle_answer_without_leaving_the_page(self):
        self.client.post("/lista/anadir/", {"name": "Tomates"})
        item = ShoppingItem.objects.get()
        moved = self.client.post(
            f"/lista/{item.pk}/pasillo/",
            {"aisle": "verduras"},
            HTTP_X_SHOP="1",
        )
        self.assertEqual(moved.status_code, 200)
        self.assertContains(moved, "fa-carrot", html=False)
        self.assertIn("Verduras", moved.json()["html"])
        checked = self.client.post(
            f"/lista/{item.pk}/hecho/",
            {"done": "1"},
            HTTP_X_SHOP="1",
        )
        self.assertEqual(checked.status_code, 200)
        self.assertIn("En el carro", checked.json()["html"])
        self.assertIn("Vaciar lo comprado", checked.json()["html"])
        item.refresh_from_db()
        self.assertTrue(item.done)

    def test_partner_presence_and_recent_add(self):
        self.partner.first_name = "Naiara"
        self.partner.save(update_fields=["first_name"])
        self.client.login(username="pareja", password="clave-segura-1")
        self.client.post("/lista/anadir/", {"name": "Detergente"})
        self.client.get("/lista/", HTTP_X_SHOP_CLIENT="telefono-naiara")
        self.client.login(username="allan", password="clave-segura-1")
        page = self.client.get("/lista/", HTTP_X_SHOP_CLIENT="telefono-allan")
        self.assertContains(page, "Naiara también la tiene abierta.")
        self.assertContains(page, "Naiara lo añadió ahora")
        self.client.post("/lista/anadir/", {"name": "Leche"})
        own = self.client.get("/lista/", HTTP_X_SHOP_CLIENT="telefono-allan")
        self.assertContains(own, "allan lo añadió ahora")

    def test_two_phones_of_the_same_account_see_each_other(self):
        self.client.get("/lista/fragmento/", HTTP_X_SHOP="1", HTTP_X_SHOP_CLIENT="telefono-a")
        other = self.client.get(
            "/lista/fragmento/", HTTP_X_SHOP="1", HTTP_X_SHOP_CLIENT="telefono-b"
        )
        self.assertEqual(other.status_code, 200)
        self.assertIn("otro teléfono", other.json()["viewers"])

    @override_settings(VAPID_PUBLIC_KEY="clave-publica", VAPID_PRIVATE_KEY="clave-privada")
    def test_push_reaches_the_other_phone_only(self):
        self.user.first_name = "Allan"
        self.user.save(update_fields=["first_name"])
        ShoppingPushSubscription.objects.create(
            household=self.household,
            user=self.user,
            client_key="telefono-allan",
            endpoint="https://push.example/allan",
            p256dh="p256",
            auth="auth",
        )
        ShoppingPushSubscription.objects.create(
            household=self.household,
            user=self.partner,
            client_key="telefono-naiara",
            endpoint="https://push.example/naiara",
            p256dh="p256",
            auth="auth",
        )
        with patch("apps.shopping.push.webpush") as pushed:
            added = self.client.post(
                "/lista/anadir/",
                {"name": "Pan", "client_key": "telefono-allan"},
            )
        self.assertRedirects(added, "/lista/")
        self.assertEqual(pushed.call_count, 1)
        self.assertEqual(
            pushed.call_args.kwargs["subscription_info"]["endpoint"],
            "https://push.example/naiara",
        )
        self.assertIn("Allan añadió Pan", pushed.call_args.kwargs["data"])
        item = ShoppingItem.objects.get()
        item.done = True
        item.save(update_fields=["done"])
        with patch("apps.shopping.push.webpush") as cleared:
            self.client.post("/lista/vaciar/", HTTP_X_SHOP_CLIENT="telefono-allan")
        self.assertEqual(cleared.call_count, 1)
        self.assertIn("ha hecho la compra", cleared.call_args.kwargs["data"])

    def test_empty_cart_does_not_notify(self):
        with patch("apps.shopping.push.webpush") as pushed:
            self.client.post("/lista/vaciar/")
        self.assertEqual(pushed.call_count, 0)

    @override_settings(VAPID_PUBLIC_KEY="")
    def test_phone_can_subscribe_to_list_alerts(self):
        response = self.client.post(
            "/lista/avisos/",
            data=json.dumps(
                {
                    "endpoint": "https://push.example/allan",
                    "keys": {"p256dh": "p256", "auth": "auth"},
                    "client_key": "telefono-allan",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        saved = ShoppingPushSubscription.objects.get()
        self.assertEqual(saved.user, self.user)
        self.assertEqual(saved.client_key, "telefono-allan")
        page = self.client.get("/lista/")
        self.assertNotContains(page, "Avisarme")

    @override_settings(VAPID_PUBLIC_KEY="clave-publica")
    def test_list_offers_alerts_when_push_is_configured(self):
        page = self.client.get("/lista/")
        self.assertContains(page, "Avisarme")

    def test_home_links_to_the_list(self):
        self.client.post("/lista/anadir/", {"name": "Pan"})
        self.client.post("/lista/anadir/", {"name": "Leche"})
        home = self.client.get("/inicio/")
        self.assertContains(home, "Lista de compra")
        self.assertContains(home, "quedan 2")
        self.assertContains(home, "Lista de compra</span>")

    def test_phone_add_returns_the_new_id(self):
        response = self.client.post(
            "/lista/anadir/", {"name": "Leche"}, HTTP_X_SHOP="1"
        )
        self.assertEqual(response.status_code, 200)
        item = ShoppingItem.objects.get()
        self.assertEqual(response.json()["created_id"], str(item.pk))
        self.assertIn("Leche", response.json()["html"])
        self.assertIn('data-aisle="none"', response.json()["html"])

    def test_phone_duplicate_points_at_the_existing_item(self):
        self.client.post("/lista/anadir/", {"name": "Leche"})
        item = ShoppingItem.objects.get()
        response = self.client.post(
            "/lista/anadir/", {"name": "leche"}, HTTP_X_SHOP="1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["error"], "Ya está en la lista.")
        self.assertEqual(response.json()["matched_id"], str(item.pk))
        self.assertEqual(ShoppingItem.objects.filter(household=self.household).count(), 1)

    def test_phone_clear_returns_the_list(self):
        self.client.post("/lista/anadir/", {"name": "Pan"})
        item = ShoppingItem.objects.get()
        item.done = True
        item.save(update_fields=["done"])
        response = self.client.post("/lista/vaciar/", HTTP_X_SHOP="1")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Pan", response.json()["html"])
        self.assertFalse(ShoppingItem.objects.exists())

    def test_list_page_keeps_a_copy_for_the_phone(self):
        self.client.post("/lista/anadir/", {"name": "Leche"})
        page = self.client.get("/lista/")
        item = ShoppingItem.objects.get()
        self.assertContains(page, f'data-id="{item.pk}"')
        self.assertContains(page, 'data-aisle="none"')
        self.assertContains(page, 'id="shop-offline"')
        self.assertContains(page, f'data-home="{self.household.id}"')
