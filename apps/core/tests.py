import json
from datetime import date, timedelta
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.chores.models import Chore
from apps.core.house_chat import house_snapshot
from apps.core.mail import EmailDeliveryError
from apps.core.models import HouseMessage
from apps.core.week import monday_of, weekday_short
from apps.households.models import HouseholdMembership
from apps.households.services import create_household_for_user
from apps.meal_plans.models import MealPlan, MealPlanEntry
from apps.recipes.models import Recipe
from apps.shopping.models import Purchase, ShoppingItem, product_key
from apps.shopping.services import clear_bought


class HealthTests(TestCase):
    def test_health_ok(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertIs(body["database"], True)
        self.assertGreaterEqual(body["database_ms"], 0)

    def test_health_reports_a_database_failure(self):
        with patch("apps.core.views.connection.cursor", side_effect=OSError("caido")):
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["status"], "error")
        self.assertIs(body["database"], False)
        self.assertEqual(body["error"], "OSError")
        self.assertNotIn("caido", response.content.decode())

    def test_ping_does_not_open_the_database(self):
        with patch("apps.core.views.connection.cursor") as cursor:
            response = self.client.get("/ping/")
        cursor.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


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
        self.assertContains(dashboard, 'class="tabbar"')
        self.assertContains(dashboard, 'href="/inicio/" data-title="Inicio" aria-current="page"')
        self.assertContains(dashboard, 'href="/por-hacer/" data-title="Por hacer"')
        self.assertNotContains(dashboard, 'data-title="Recetario"')
        self.assertContains(dashboard, 'aria-controls="menu-cuenta"')
        self.assertContains(dashboard, "Historial</a>")
        self.assertContains(dashboard, "Resumen</a>")
        self.assertContains(dashboard, "fa-chart-column")
        self.assertContains(dashboard, "Recetario</a>")
        self.assertNotContains(dashboard, ">Más<")


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


class SummaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("allan", password="clave-segura-1")
        self.other = User.objects.create_user("vecino", password="clave-segura-1")
        self.household = create_household_for_user(self.user, "Casa")
        self.other_home = create_household_for_user(self.other, "Otra")
        self.recipe = Recipe.objects.create(
            household=self.household, name="Lentejas", category=Recipe.Category.LEGUMBRES
        )
        self.client.login(username="allan", password="clave-segura-1")

    def test_approved_meals_and_cleared_cart_show_on_the_summary(self):
        plan = MealPlan.objects.create(
            household=self.household,
            week_start=date(2026, 11, 2),
            status=MealPlan.Status.APPROVED,
            created_by=self.user,
        )
        MealPlanEntry.objects.create(meal_plan=plan, day=date(2026, 11, 2), recipe=self.recipe)
        MealPlanEntry.objects.create(meal_plan=plan, day=date(2026, 11, 3), recipe=self.recipe)
        draft = MealPlan.objects.create(
            household=self.household,
            week_start=date(2026, 10, 26),
            created_by=self.user,
        )
        MealPlanEntry.objects.create(meal_plan=draft, day=date(2026, 10, 26), recipe=self.recipe)
        item = ShoppingItem.objects.create(household=self.household, name="Leche", added_by=self.user)
        item.done = True
        item.save(update_fields=["done"])
        with patch("apps.shopping.services.timezone.localdate", return_value=date(2026, 11, 5)):
            clear_bought(self.household)
        Purchase.objects.create(
            household=self.other_home, name="Secreto", normalized_name="secreto", bought_on=date(2026, 11, 5)
        )
        with patch("apps.core.summary.timezone.localdate", return_value=date(2026, 11, 5)):
            page = self.client.get("/resumen/")
        self.assertContains(page, "Comidas")
        self.assertContains(page, "Lentejas")
        self.assertContains(page, 'summary-count">2<')
        self.assertContains(page, "Leche")
        self.assertNotContains(page, "Secreto")
        self.assertContains(page, "fa-chart-column")
        self.assertContains(page, 'aria-current="page"')

    def test_potato_spellings_count_as_one_purchase(self):
        for name in ("patata", "patatas", "Patatas"):
            Purchase.objects.create(
                household=self.household,
                name=name,
                normalized_name=name.casefold(),
                bought_on=date(2026, 11, 5),
            )
        with patch("apps.core.summary.timezone.localdate", return_value=date(2026, 11, 5)):
            page = self.client.get("/resumen/")
        self.assertContains(page, "Patatas")
        self.assertContains(page, 'summary-count">3<')
        self.assertNotContains(page, ">patata<")
        self.assertEqual(product_key("Patatas"), product_key("patata"))

    def test_purchases_count_each_cart_clear_across_all_history(self):
        Purchase.objects.create(
            household=self.household,
            name="2 cebollas",
            normalized_name="2 cebollas",
            bought_on=date(2020, 1, 1),
        )
        Purchase.objects.create(
            household=self.household,
            name="Cebolla",
            normalized_name="cebolla",
            bought_on=date(2020, 1, 2),
        )
        Purchase.objects.create(
            household=self.household,
            name="Cebollas",
            normalized_name="cebollas",
            bought_on=date(2026, 11, 5),
        )
        Purchase.objects.create(
            household=self.household,
            name="300 gr de pasta",
            normalized_name="300 gr de pasta",
            bought_on=date(2026, 11, 5),
        )
        Purchase.objects.create(
            household=self.household,
            name="Plátanos",
            normalized_name="plátanos",
            bought_on=date(2026, 11, 5),
        )
        Purchase.objects.create(
            household=self.household,
            name="Platanos",
            normalized_name="platanos",
            bought_on=date(2026, 11, 4),
        )
        pasted = (
            "300 gr. de espaguetis 280 gr. de chorizo picante "
            "2 cebolletas 2 pimientos verdes"
        )
        Purchase.objects.create(
            household=self.household,
            name=pasted,
            normalized_name=pasted.casefold(),
            bought_on=date(2026, 11, 5),
        )
        with patch("apps.core.summary.timezone.localdate", return_value=date(2026, 11, 5)):
            page = self.client.get("/resumen/")
        self.assertContains(page, "Cebollas")
        self.assertContains(page, "2 cebollas")
        self.assertContains(page, 'summary-count">2<')
        self.assertNotContains(page, 'summary-count">3<')
        self.assertContains(page, "Plátanos")
        self.assertContains(page, 'summary-count">2<')
        self.assertContains(page, "300 gr de pasta")
        self.assertContains(page, 'summary-count">1<')
        self.assertNotContains(page, "2 cebolletas")

    def test_summary_shows_the_ten_most_bought_products(self):
        for index in range(12):
            name = f"Producto {index:02d}"
            Purchase.objects.create(
                household=self.household,
                name=name,
                normalized_name=name.casefold(),
                bought_on=date(2026, 11, 5),
            )
            if index < 11:
                Purchase.objects.create(
                    household=self.household,
                    name=name,
                    normalized_name=name.casefold(),
                    bought_on=date(2026, 11, 4),
                )
        with patch("apps.core.summary.timezone.localdate", return_value=date(2026, 11, 5)):
            page = self.client.get("/resumen/")
        self.assertContains(page, "Producto 00")
        self.assertContains(page, "Producto 09")
        self.assertNotContains(page, "Producto 10")
        self.assertNotContains(page, "Producto 11")

    def test_same_count_puts_the_latest_purchase_first(self):
        Purchase.objects.create(
            household=self.household,
            name="Cebolla",
            normalized_name="cebolla",
            bought_on=date(2026, 10, 21),
        )
        Purchase.objects.create(
            household=self.household,
            name="Patata",
            normalized_name="patata",
            bought_on=date(2026, 11, 21),
        )
        with patch("apps.core.summary.timezone.localdate", return_value=date(2026, 11, 21)):
            page = self.client.get("/resumen/")
        body = page.content.decode()
        self.assertLess(body.index(">Patata<"), body.index(">Cebolla<"))

    def test_a_product_opens_each_purchase_with_date_and_people(self):
        self.user.first_name = "Allan"
        self.user.save(update_fields=["first_name"])
        naiara = User.objects.create_user("naiara", password="clave-segura-1", first_name="Naiara")
        item = ShoppingItem.objects.create(
            household=self.household, name="Pan bimbo", added_by=naiara
        )
        item.done = True
        item.save(update_fields=["done"])
        with patch("apps.shopping.services.timezone.localdate", return_value=date(2026, 11, 17)):
            clear_bought(self.household, self.user)
        Purchase.objects.create(
            household=self.household,
            name="Pan bimbo",
            normalized_name="pan bimbo",
            bought_on=date(2026, 11, 6),
        )
        with patch("apps.core.summary.timezone.localdate", return_value=date(2026, 11, 21)):
            page = self.client.get("/resumen/")
        self.assertContains(page, "Comprado")
        self.assertContains(page, "Lo añadió")
        self.assertContains(page, "Lo compró")
        self.assertContains(page, "mar 17 nov")
        self.assertContains(page, "Naiara")
        self.assertContains(page, "Allan")
        self.assertContains(page, "vie 6 nov")
        self.assertContains(page, "Sin registro")

    def test_summary_requires_login(self):
        self.client.logout()
        response = self.client.get("/resumen/")
        self.assertEqual(response.status_code, 302)


class HouseChatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "allan", password="clave-segura-1", first_name="Allan"
        )
        self.naiara = User.objects.create_user(
            "naiara", password="clave-segura-1", first_name="Naiara"
        )
        self.other = User.objects.create_user(
            "vecino", password="clave-segura-1", first_name="Vecino"
        )
        self.household = create_household_for_user(self.user, "Allan&Naiara")
        HouseholdMembership.objects.create(
            household=self.household,
            user=self.naiara,
            role=HouseholdMembership.Role.MEMBER,
        )
        self.other_home = create_household_for_user(self.other, "Otra")
        self.recipe = Recipe.objects.create(
            household=self.household, name="Lentejas", category=Recipe.Category.LEGUMBRES
        )
        Recipe.objects.create(
            household=self.other_home, name="Secreto secreto", category=Recipe.Category.CARNE
        )
        today = timezone.localdate()
        plan = MealPlan.objects.create(
            household=self.household,
            week_start=monday_of(today),
            status=MealPlan.Status.APPROVED,
            created_by=self.user,
        )
        MealPlanEntry.objects.create(meal_plan=plan, day=today, recipe=self.recipe)
        self.client.login(username="allan", password="clave-segura-1")

    def _body(self, **payload):
        data = {"reply": "Hoy toca lentejas.", "actions": []}
        data.update(payload)
        return json.dumps(
            {"candidates": [{"content": {"parts": [{"text": json.dumps(data)}]}}]}
        ).encode()

    def test_home_has_the_floating_button(self):
        page = self.client.get("/inicio/")
        self.assertContains(page, "Hablar con casa")
        self.assertContains(page, 'id="house-open"')
        self.assertNotContains(page, ">Casa</span>")

    def test_snapshot_includes_ingredients_without_naming_the_recipe(self):
        self.recipe.ingredients = "200 g de lentejas\n1 cebolla"
        self.recipe.steps = "Cocer las lentejas."
        self.recipe.servings = 4
        self.recipe.save()
        Purchase.objects.create(
            household=self.household, name="Pan bimbo", normalized_name="pan bimbo", bought_on=timezone.localdate()
        )
        Purchase.objects.create(
            household=self.household, name="Pan bimbo", normalized_name="pan bimbo", bought_on=timezone.localdate()
        )
        Purchase.objects.create(
            household=self.other_home, name="Secreto secreto", normalized_name="secreto", bought_on=timezone.localdate()
        )
        recipes = house_snapshot(self.household, self.user, "qué recetas tengo guardadas")
        self.assertIn("200 g de lentejas", recipes)
        self.assertIn("Cocer las lentejas.", recipes)
        self.assertNotIn("Pan bimbo: 2 veces", recipes)
        bought = house_snapshot(self.household, self.user, "qué productos compro más")
        self.assertIn("Pan bimbo: 2 veces", bought)
        self.assertNotIn("200 g de lentejas", bought)
        today = house_snapshot(self.household, self.user, "qué comemos hoy")
        self.assertIn("Lentejas", today)
        self.assertNotIn("200 g de lentejas", today)
        self.assertNotIn("Pan bimbo: 2 veces", today)
        whole = house_snapshot(self.household, self.user, "qué hay en casa")
        self.assertIn("200 g de lentejas", whole)
        self.assertIn("Pan bimbo: 2 veces", whole)
        self.assertIn("Alimentos del bebé", whole)
        self.assertNotIn("Secreto secreto", whole)

    def test_empty_message_is_rejected(self):
        response = self.client.post("/casa/", {"text": "   "})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(HouseMessage.objects.count(), 0)

    @override_settings(GEMINI_API_KEY="clave-de-prueba", GEMINI_MODEL="gemini-3.5-flash")
    def test_answer_uses_this_household_and_saves_the_thread(self):
        with patch("apps.recipes.ai.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = self._body()
            response = self.client.post("/casa/", {"text": "Qué comemos hoy"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["reply"]["body"], "Hoy toca lentejas.")
        sent = json.loads(urlopen.call_args.args[0].data.decode())
        question = sent["contents"][-1]["parts"][0]["text"]
        self.assertIn("Lentejas", question)
        self.assertNotIn("Secreto secreto", question)
        self.assertIn("Recetas: Lentejas", question)
        self.assertNotIn("Ingredientes:", question)
        self.assertIn("models/gemini-3.5-flash:generateContent", urlopen.call_args.args[0].full_url)
        self.assertEqual(HouseMessage.objects.filter(user=self.user).count(), 2)
        self.client.logout()
        self.client.login(username="naiara", password="clave-segura-1")
        history = self.client.get("/casa/")
        self.assertEqual(history.json()["messages"], [])

    @override_settings(GEMINI_API_KEY="clave-de-prueba")
    def test_can_put_recipe_ingredients_on_the_list_and_a_dish_on_a_day(self):
        self.recipe.ingredients = "200 g de lentejas"
        self.recipe.is_meal = True
        self.recipe.save()
        with patch("apps.recipes.ai.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = self._body(
                reply="Ingredientes en la lista.",
                actions=[{"kind": "ingredients_to_list", "name": "Lentejas"}],
            )
            listed = self.client.post("/casa/", {"text": "Pon los ingredientes de las lentejas"})
            urlopen.return_value.__enter__.return_value.read.return_value = self._body(
                reply="El domingo toca lentejas.",
                actions=[{"kind": "set_dish", "name": "Lentejas", "day": "domingo"}],
            )
            moved = self.client.post("/casa/", {"text": "El domingo lentejas"})
        self.assertIn("Lista de compra · 1 de Lentejas", listed.json()["reply"]["receipts"])
        self.assertTrue(ShoppingItem.objects.filter(household=self.household, name="200 g de lentejas").exists())
        sunday = monday_of(timezone.localdate()) + timedelta(days=6)
        entry = MealPlanEntry.objects.get(meal_plan__household=self.household, day=sunday)
        self.assertEqual(entry.recipe, self.recipe)
        self.assertIn("Menú ·", moved.json()["reply"]["receipts"][0])

    @override_settings(GEMINI_API_KEY="clave-de-prueba")
    def test_can_add_to_the_shopping_list_and_mark_a_chore(self):
        Chore.objects.create(household=self.household, title="Colada", cadence=Chore.Cadence.TODAY)
        with patch("apps.recipes.ai.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = self._body(
                reply="Leche añadida a la lista.",
                actions=[{"kind": "add_shopping", "name": "Leche"}],
            )
            added = self.client.post("/casa/", {"text": "Añade leche"})
            urlopen.return_value.__enter__.return_value.read.return_value = self._body(
                reply="Colada marcada como hecha.",
                actions=[{"kind": "complete_chore", "name": "Colada"}],
            )
            done = self.client.post("/casa/", {"text": "La colada ya está"})
        self.assertEqual(added.json()["reply"]["receipts"], ["Lista de compra · Leche"])
        self.assertTrue(
            ShoppingItem.objects.filter(household=self.household, name="Leche", added_by=self.user).exists()
        )
        self.assertEqual(done.json()["reply"]["receipts"], ["Por hacer · Colada"])
        self.assertEqual(Chore.objects.get(title="Colada").done_on, timezone.localdate())

    @override_settings(GEMINI_API_KEY="clave-de-prueba")
    def test_ambiguous_chore_is_not_marked(self):
        Chore.objects.create(household=self.household, title="Colada blanca")
        Chore.objects.create(household=self.household, title="Colada oscura")
        with patch("apps.recipes.ai.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = self._body(
                reply="Marco la colada.",
                actions=[{"kind": "complete_chore", "name": "colada"}],
            )
            response = self.client.post("/casa/", {"text": "La colada ya está"})
        self.assertIn("varias tareas", response.json()["reply"]["body"])
        self.assertEqual(response.json()["reply"]["receipts"], [])
        self.assertFalse(Chore.objects.exclude(done_on=None).exists())

    @override_settings(GEMINI_API_KEY="clave-de-prueba")
    def test_can_create_a_recipe_for_someone_in_the_house(self):
        with patch("apps.recipes.ai.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = self._body(
                reply="Tortilla guardada.",
                actions=[
                    {
                        "kind": "create_recipe",
                        "name": "Tortilla de patata",
                        "category": "huevos",
                        "ingredients": "4 huevos\n2 patatas",
                        "steps": "Freír la patata y cuajar.",
                        "servings": 2,
                    },
                    {
                        "kind": "add_chore",
                        "name": "Bajar la basura",
                        "cadence": "hoy",
                        "assignee": "Naiara",
                    },
                ],
            )
            response = self.client.post("/casa/", {"text": "Guarda la tortilla y apunta la basura"})
        recipe = Recipe.objects.get(household=self.household, name="Tortilla de patata")
        self.assertEqual(recipe.category, Recipe.Category.HUEVOS)
        self.assertEqual(recipe.servings, 2)
        chore = Chore.objects.get(title="Bajar la basura")
        self.assertEqual(chore.assignee, self.naiara)
        self.assertEqual(
            response.json()["reply"]["receipts"],
            ["Recetario · Tortilla de patata", "Por hacer · Bajar la basura"],
        )
        self.assertFalse(Recipe.objects.filter(household=self.other_home, name="Tortilla de patata").exists())

    @override_settings(GEMINI_API_KEY="clave-de-prueba")
    def test_quota_error_changes_nothing(self):
        body = json.dumps(
            {
                "error": {
                    "status": "RESOURCE_EXHAUSTED",
                    "details": [
                        {"retryDelay": "65641s"},
                        {
                            "violations": [
                                {
                                    "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                                    "quotaValue": "20",
                                }
                            ]
                        },
                    ],
                }
            }
        ).encode()
        error = HTTPError(
            "https://generativelanguage.googleapis.com/",
            429,
            "Too Many Requests",
            hdrs=None,
            fp=BytesIO(body),
        )
        with patch("apps.recipes.ai.urlopen", side_effect=error):
            response = self.client.post("/casa/", {"text": "Añade pan"})
        self.assertEqual(response.status_code, 502)
        self.assertIn("20 lecturas", response.json()["error"])
        self.assertEqual(ShoppingItem.objects.count(), 0)
        self.assertEqual(HouseMessage.objects.count(), 0)


class WeekdayShortTests(TestCase):
    def test_spanish_abbreviations(self):
        self.assertEqual(weekday_short(date(2026, 10, 19)), "Lun")
        self.assertEqual(weekday_short(date(2026, 10, 21)), "Mié")
        self.assertEqual(weekday_short(date(2026, 10, 25)), "Dom")
