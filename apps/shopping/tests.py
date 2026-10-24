from django.contrib.auth.models import User
from django.test import TestCase

from apps.households.models import HouseholdMembership
from apps.households.services import create_household_for_user
from apps.shopping.models import ShoppingItem


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

    def test_home_links_to_the_list(self):
        self.client.post("/lista/anadir/", {"name": "Pan"})
        self.client.post("/lista/anadir/", {"name": "Leche"})
        home = self.client.get("/inicio/")
        self.assertContains(home, "Lista de compra")
        self.assertContains(home, "quedan 2")
        self.assertContains(home, ">Lista de compra<")
