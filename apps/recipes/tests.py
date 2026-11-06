import json
from datetime import date
from unittest.mock import patch
from urllib.error import URLError

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.households.services import create_household_for_user
from apps.meal_plans.models import MealPlan, MealPlanEntry
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

    def test_share_text_includes_the_recipe(self):
        self.recipe.prep_time_minutes = 40
        self.recipe.ingredients = "200 g de lentejas\n1 cebolla"
        self.recipe.steps = "Cocer las lentejas."
        self.recipe.save()
        text = self.recipe.share_text()
        self.assertIn("Lentejas", text)
        self.assertIn("Legumbres · 40 min", text)
        self.assertIn("- 200 g de lentejas", text)
        self.assertIn("Cocer las lentejas.", text)
        self.client.login(username="allan", password="clave-segura-1")
        page = self.client.get("/recetas/")
        self.assertContains(page, "Compartir Lentejas")
        self.assertContains(page, "200 g de lentejas")
        self.assertContains(page, "Cocer las lentejas.")

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
        self.assertContains(response, "Compartir Lentejas")
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
        self.assertContains(archived, "Borrar Sopa vieja")
        self.assertContains(archived, "¿Deseas borrar «Sopa vieja»?")
        self.assertNotContains(active, "Borrar Lentejas")

    def test_delete_archived_recipe(self):
        old = Recipe.objects.create(
            household=self.household,
            name="Sopa vieja",
            category=Recipe.Category.OTROS,
            is_active=False,
        )
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.post(f"/recetas/{old.id}/borrar/", {"next": "/recetas/?archivo=1"})
        self.assertRedirects(response, "/recetas/?archivo=1")
        self.assertFalse(Recipe.objects.filter(pk=old.pk).exists())

    def test_active_recipe_is_not_deleted(self):
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.post(f"/recetas/{self.recipe.id}/borrar/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Recipe.objects.filter(pk=self.recipe.pk, is_active=True).exists())

    def test_archived_recipe_used_in_a_menu_stays(self):
        old = Recipe.objects.create(
            household=self.household,
            name="Sopa vieja",
            category=Recipe.Category.OTROS,
            is_active=False,
        )
        plan = MealPlan.objects.create(
            household=self.household, week_start=date(2026, 11, 2), created_by=self.user
        )
        MealPlanEntry.objects.create(meal_plan=plan, day=date(2026, 11, 2), recipe=old)
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.post(f"/recetas/{old.id}/borrar/", follow=True)
        self.assertContains(response, "se queda archivada")
        self.assertTrue(Recipe.objects.filter(pk=old.pk).exists())

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
                "servings": 4,
                "prep_time_minutes": 30,
                "notes": "Huevo y tomate",
            },
        )
        self.assertEqual(response.status_code, 302)
        recipe = Recipe.objects.get(household=self.household, normalized_name="arroz cubana")
        self.assertEqual(recipe.servings, 4)

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

    def _model_body(self, **fields):
        payload = {
            "name": "Lentejas",
            "category": "legumbres",
            "servings": 4,
            "prep_time_minutes": 40,
            "ingredients": "200 g de lentejas",
            "steps": "Cocer las lentejas.",
        }
        payload.update(fields)
        raw = json.dumps(
            {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}
        ).encode()
        return raw

    @override_settings(GEMINI_API_KEY="clave-de-prueba", GEMINI_MODEL="gemini-3.5-flash")
    def test_interpret_fills_the_form_without_saving(self):
        self.client.login(username="allan", password="clave-segura-1")
        page = self.client.get("/recetas/nueva/")
        self.assertContains(page, "Procesar con IA")
        self.assertContains(page, "field-pair")
        self.assertContains(page, "Raciones")
        self.assertContains(page, "Procesando la receta…")
        self.assertContains(page, "fa-wand-magic-sparkles")
        self.assertContains(page, "placeholder=\"Pega aquí la receta. Se procesará con IA para sacar los ingredientes y los pasos y ponerlos en el formulario.\"")
        recipe = Recipe.objects.get(household=self.household, name="Lentejas")
        edit = self.client.get(f"/recetas/{recipe.id}/editar/")
        self.assertContains(edit, "Procesar con IA")
        before = Recipe.objects.count()
        with patch("apps.recipes.ai.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = self._model_body()
            response = self.client.post("/recetas/interpretar/", {"source": "lentejas con cebolla"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lentejas")
        self.assertContains(response, 'name="servings"')
        self.assertContains(response, 'value="4"')
        self.assertContains(response, "200 g de lentejas")
        self.assertContains(response, "Cocer las lentejas.")
        self.assertContains(response, 'value="legumbres" selected')
        self.assertEqual(Recipe.objects.count(), before)
        sent = urlopen.call_args.args[0]
        self.assertIn("models/gemini-3.5-flash:generateContent", sent.full_url)
        self.assertEqual(sent.get_header("X-goog-api-key"), "clave-de-prueba")
        instruction = json.loads(sent.data)["systemInstruction"]["parts"][0]["text"]
        self.assertIn("deduce las raciones (platos) a partir de las cantidades", instruction)

    @override_settings(GEMINI_API_KEY="clave-de-prueba")
    def test_unknown_category_uses_the_name(self):
        self.client.login(username="allan", password="clave-segura-1")
        before = Recipe.objects.count()
        with patch("apps.recipes.ai.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = self._model_body(
                category="sopas"
            )
            response = self.client.post("/recetas/interpretar/", {"source": "lentejas"})
        self.assertContains(response, 'value="legumbres" selected')
        self.assertEqual(Recipe.objects.count(), before)

    @override_settings(GEMINI_API_KEY="clave-de-prueba")
    def test_network_failure_keeps_the_text_and_saves_nothing(self):
        self.client.login(username="allan", password="clave-segura-1")
        before = Recipe.objects.count()
        with patch("apps.recipes.ai.urlopen", side_effect=URLError("no")):
            response = self.client.post(
                "/recetas/interpretar/", {"source": "lentejas con cebolla"}
            )
        self.assertContains(response, "No se pudo leer la receta. Escríbela en el formulario.")
        self.assertContains(response, "lentejas con cebolla")
        self.assertEqual(Recipe.objects.count(), before)

    @override_settings(GEMINI_API_KEY="")
    def test_paste_box_stays_hidden_without_a_key(self):
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.get("/recetas/nueva/")
        self.assertNotContains(response, "Procesar con IA")
        self.assertNotContains(response, "Pega la receta")
