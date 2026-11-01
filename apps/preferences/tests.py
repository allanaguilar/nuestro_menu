from django.contrib.auth.models import User
from django.test import TestCase

from apps.households.services import create_household_for_user, accept_invite, create_invite
from apps.preferences.models import RecipePreference
from apps.preferences.selectors import avoided_recipe_ids
from apps.preferences.services import upsert_preference
from apps.recipes.models import Recipe


class PreferenceTests(TestCase):
    def setUp(self):
        self.allan = User.objects.create_user("allan", password="clave-segura-1")
        self.naiara = User.objects.create_user("naiara", password="clave-segura-1")
        self.household = create_household_for_user(self.allan, "Casa")
        accept_invite(self.naiara, create_invite(self.household, self.allan).token)
        self.recipe = Recipe.objects.create(
            household=self.household, name="Hígado", category=Recipe.Category.CARNE
        )

    def test_avoided_by_any_member(self):
        upsert_preference(self.naiara, self.recipe, is_avoided=True)
        self.assertIn(self.recipe.id, avoided_recipe_ids(self.household))

    def test_rating_keeps_the_favorite(self):
        upsert_preference(self.allan, self.recipe, is_favorite=True, rating=2)
        self.client.login(username="allan", password="clave-segura-1")
        page = self.client.get("/preferencias/")
        self.assertNotContains(page, "Favorita para mí")
        self.assertNotContains(page, ">Guardar<")
        self.assertContains(page, "Evitar en el menú")
        self.client.post(
            "/preferencias/",
            {
                "recipe_id": str(self.recipe.id),
                f"{self.recipe.id}-rating": "4",
            },
        )
        pref = RecipePreference.objects.get(user=self.allan, recipe=self.recipe)
        self.assertTrue(pref.is_favorite)
        self.assertEqual(pref.rating, 4)
        self.assertFalse(pref.is_avoided)

    def test_baby_menu_stays_hidden_until_the_preference_is_on(self):
        self.client.login(username="allan", password="clave-segura-1")
        home = self.client.get("/inicio/")
        self.assertNotContains(home, 'data-title="Bebé"')
        self.assertNotContains(home, ">Bebé</span>")
        prefs = self.client.get("/preferencias/")
        self.assertContains(prefs, "Ver menú bebé")
        self.assertNotContains(prefs, 'name="show_baby_menu" checked')
        turned_on = self.client.post(
            "/preferencias/",
            {"form": "baby_menu", "show_baby_menu": "on"},
            follow=True,
        )
        self.assertContains(turned_on, "Menú del bebé visible.")
        self.assertContains(turned_on, 'name="show_baby_menu" checked')
        visible = self.client.get("/inicio/")
        self.assertContains(visible, 'data-title="Bebé"')
        self.assertContains(visible, ">Bebé</span>")
        self.client.post("/preferencias/", {"form": "baby_menu"})
        hidden = self.client.get("/inicio/")
        self.assertNotContains(hidden, 'data-title="Bebé"')

    def test_unique_user_recipe(self):
        RecipePreference.objects.create(user=self.allan, recipe=self.recipe, rating=5)
        with self.assertRaises(Exception):
            RecipePreference.objects.create(user=self.allan, recipe=self.recipe, rating=1)
