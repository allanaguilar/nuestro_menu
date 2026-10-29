from django.contrib.auth.models import User
from django.test import TestCase

from apps.households.services import create_household_for_user
from apps.recipes.models import Recipe
from apps.recipes.services import guess_recipe_category, import_recipes_from_text
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
        self.assertContains(response, "Vista previa de Lentejas")
        self.assertContains(response, "Ver archivadas")
        self.assertContains(response, "button-ghost")
        self.assertContains(response, 'aria-pressed="false"')
        self.assertNotContains(response, "Filtrar")
        self.assertNotContains(response, "Categoría")
        self.assertNotContains(response, "Más recientes")
        self.assertNotContains(response, "Secreto")

    def test_archived_check_shows_only_archived(self):
        Recipe.objects.create(
            household=self.household,
            name="Sopa vieja",
            category=Recipe.Category.OTROS,
            is_active=False,
        )
        self.client.login(username="allan", password="clave-segura-1")
        archived = self.client.get("/recetas/?archivo=1")
        self.assertContains(archived, "Sopa vieja")
        self.assertContains(archived, 'aria-pressed="true"')
        self.assertNotContains(archived, "Vista previa de Lentejas")
        active = self.client.get("/recetas/")
        self.assertContains(active, "Vista previa de Lentejas")
        self.assertNotContains(active, "Sopa vieja")

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

    def test_edit_form_keeps_long_recipe_fields_in_a_scroll_box(self):
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.get(f"/recetas/{self.recipe.id}/editar/")
        self.assertContains(response, "Ingredientes")
        self.assertContains(response, "Pasos")
        self.assertContains(response, "recipe-text")
        self.assertContains(response, "Sale como comida de un día")
        self.assertNotContains(response, "Notas")
        saved = self.client.post(
            f"/recetas/{self.recipe.id}/editar/",
            {
                "name": "Lentejas",
                "category": Recipe.Category.LEGUMBRES,
                "ingredients": "Lentejas\nCebolla",
                "steps": "Cocer 40 minutos.",
            },
        )
        self.assertRedirects(saved, "/recetas/")
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.ingredient_lines, ["Lentejas", "Cebolla"])
        self.assertEqual(self.recipe.step_lines, ["Cocer 40 minutos."])

    def test_form_does_not_ask_to_confirm_a_similar_name(self):
        self.client.login(username="allan", password="clave-segura-1")
        page = self.client.get(f"/recetas/{self.recipe.id}/editar/")
        self.assertNotContains(page, "nombre parecido")
        saved = self.client.post(
            "/recetas/nueva/",
            {"name": "lentejas", "category": Recipe.Category.LEGUMBRES},
        )
        self.assertRedirects(saved, "/recetas/")


class RecipeImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("allan", password="clave-segura-1")
        self.other = User.objects.create_user("vecino", password="clave-segura-1")
        self.household = create_household_for_user(self.user, "Casa")
        self.other_home = create_household_for_user(self.other, "Otra")
        Recipe.objects.create(
            household=self.household, name="Lentejas", category=Recipe.Category.LEGUMBRES
        )

    def test_guesses_category_from_name(self):
        self.assertEqual(guess_recipe_category("Pasta con carne"), Recipe.Category.PASTA)
        self.assertEqual(guess_recipe_category("Crema de calabaza"), Recipe.Category.VERDURAS)
        self.assertEqual(guess_recipe_category("Salmón con verduras"), Recipe.Category.PESCADO)
        self.assertEqual(guess_recipe_category("Patatas a la riojana"), Recipe.Category.OTROS)

    def test_skips_existing_names(self):
        result = import_recipes_from_text(
            self.household,
            "lentejas\nPatatas a la riojana\n• Garbanzos | legumbres",
        )
        self.assertEqual([recipe.name for recipe in result.created], ["Patatas a la riojana", "Garbanzos"])
        self.assertEqual(result.skipped, ["lentejas"])

    def test_web_import_creates_recipes(self):
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.post(
            "/recetas/importar/",
            {"text": "Arroz cremoso\nHuevo frito | huevos"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se han importado 2 recetas")
        self.assertTrue(
            Recipe.objects.filter(household=self.household, normalized_name="arroz cremoso").exists()
        )
        self.assertEqual(
            Recipe.objects.get(household=self.household, normalized_name="huevo frito").category,
            Recipe.Category.HUEVOS,
        )

    def test_import_stays_in_own_household(self):
        self.client.login(username="allan", password="clave-segura-1")
        self.client.post("/recetas/importar/", {"text": "Gazpacho"})
        self.assertTrue(Recipe.objects.filter(household=self.household, normalized_name="gazpacho").exists())
        self.assertFalse(Recipe.objects.filter(household=self.other_home, normalized_name="gazpacho").exists())

    def test_api_import(self):
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.post(
            "/api/recipes/import/",
            {"text": "Chuleta\nLentejas"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(len(data["created"]), 1)
        self.assertEqual(data["skipped"], ["Lentejas"])
        self.assertEqual(data["created"][0]["category"], Recipe.Category.CARNE)
