from django.contrib.auth.models import User
from django.test import TestCase

from apps.households.services import create_household_for_user
from apps.recipes.models import Recipe
from apps.recipes.utils import normalize_recipe_name


class RecipeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("allan", password="clave-segura-1")
        self.other = User.objects.create_user("vecino", password="clave-segura-1")
        self.household = create_household_for_user(self.user, "Casa")
        self.other_home = create_household_for_user(self.other, "Otra")
        self.recipe = Recipe.objects.create(
            household=self.household, name="Lentejas", category=Recipe.Category.LEGUMBRES
        )
        self.foreign = Recipe.objects.create(
            household=self.other_home, name="Secreto", category=Recipe.Category.OTROS
        )

    def test_normalized_name(self):
        self.assertEqual(normalize_recipe_name("  Lentejas   Estofadas "), "lentejas estofadas")
        recipe = Recipe.objects.create(
            household=self.household, name="  Pollo  Asado ", category=Recipe.Category.CARNE
        )
        self.assertEqual(recipe.normalized_name, "pollo asado")

    def test_list_requires_auth(self):
        response = self.client.get("/recetas/")
        self.assertEqual(response.status_code, 302)

    def test_user_sees_only_own_recipes(self):
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.get("/recetas/")
        self.assertContains(response, "Lentejas")
        self.assertNotContains(response, "Secreto")

    def test_cannot_edit_foreign_recipe(self):
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.get(f"/recetas/{self.foreign.id}/editar/")
        self.assertEqual(response.status_code, 404)

    def test_create_recipe(self):
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.post(
            "/recetas/nueva/",
            {
                "name": "Arroz cubana",
                "category": Recipe.Category.ARROZ,
                "prep_time_minutes": 30,
                "notes": "Huevo y tomate",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Recipe.objects.filter(household=self.household, normalized_name="arroz cubana").exists()
        )

    def test_duplicate_requires_confirmation(self):
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.post(
            "/recetas/nueva/",
            {"name": "lentejas", "category": Recipe.Category.LEGUMBRES},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "nombre equivalente")
