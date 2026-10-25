from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.core.week import monday_of
from apps.households.services import accept_invite, create_household_for_user, create_invite
from apps.meal_plans.models import MealPlan, MealPlanEntry
from apps.meal_plans.services.generator import (
    ApprovedPlanProtectedError,
    InsufficientRecipesError,
    generate_week_menu,
)
from apps.meal_plans.services.planning import approve_plan, change_entry
from apps.preferences.services import upsert_preference
from apps.recipes.models import Recipe


CATEGORIES = [
    Recipe.Category.LEGUMBRES,
    Recipe.Category.CARNE,
    Recipe.Category.PESCADO,
    Recipe.Category.PASTA,
    Recipe.Category.ARROZ,
    Recipe.Category.VERDURAS,
    Recipe.Category.HUEVOS,
    Recipe.Category.OTROS,
]


def make_recipes(household, count=8):
    recipes = []
    for index in range(count):
        recipes.append(
            Recipe.objects.create(
                household=household,
                name=f"Plato {index + 1}",
                category=CATEGORIES[index % len(CATEGORIES)],
            )
        )
    return recipes


class MealPlanTests(TestCase):
    def setUp(self):
        self.allan = User.objects.create_user("allan", password="clave-segura-1")
        self.naiara = User.objects.create_user("naiara", password="clave-segura-1")
        self.vecino = User.objects.create_user("vecino", password="clave-segura-1")
        self.household = create_household_for_user(self.allan, "Casa")
        accept_invite(self.naiara, create_invite(self.household, self.allan).token)
        self.other = create_household_for_user(self.vecino, "Otra")
        self.week = monday_of(timezone.localdate())
        self.recipes = make_recipes(self.household, 16)
        self.foreign_recipes = make_recipes(self.other, 8)

    def test_week_must_be_monday(self):
        plan = MealPlan(
            household=self.household,
            week_start=self.week + timedelta(days=1),
            created_by=self.allan,
        )
        with self.assertRaises(ValidationError):
            plan.save()

    def test_insufficient_recipes(self):
        Recipe.objects.filter(household=self.household).delete()
        make_recipes(self.household, 6)
        with self.assertRaises(InsufficientRecipesError):
            generate_week_menu(self.household, self.week, self.allan)

    def test_avoided_excluded(self):
        upsert_preference(self.naiara, self.recipes[0], is_avoided=True)
        plan = generate_week_menu(self.household, self.week, self.allan, seed=1)
        ids = set(plan.entries.values_list("recipe_id", flat=True))
        self.assertNotIn(self.recipes[0].id, ids)

    @override_settings(GENERATOR_MAX_COMBINATIONS=40)
    def test_generate_seven_unique(self):
        plan = generate_week_menu(self.household, self.week, self.allan, seed=42)
        self.assertEqual(plan.entries.count(), 7)
        self.assertEqual(plan.status, MealPlan.Status.DRAFT)
        ids = list(plan.entries.values_list("recipe_id", flat=True))
        self.assertEqual(len(ids), len(set(ids)))
        for entry in plan.entries.all():
            self.assertEqual(entry.recipe.household_id, self.household.id)
            self.assertGreaterEqual(entry.day, plan.week_start)
            self.assertLessEqual(entry.day, plan.week_end)

    @override_settings(GENERATOR_MAX_COMBINATIONS=40)
    def test_seed_is_reproducible(self):
        first = generate_week_menu(self.household, self.week, self.allan, seed=7)
        first_ids = list(first.entries.order_by("day").values_list("recipe_id", flat=True))
        generate_week_menu(self.household, self.week, self.allan, seed=7)
        second = MealPlan.objects.get(household=self.household, week_start=self.week)
        second_ids = list(second.entries.order_by("day").values_list("recipe_id", flat=True))
        self.assertEqual(first_ids, second_ids)

    @override_settings(GENERATOR_MAX_COMBINATIONS=40)
    def test_does_not_replace_approved_without_confirm(self):
        plan = generate_week_menu(self.household, self.week, self.allan, seed=3)
        approve_plan(self.household, self.week)
        with self.assertRaises(ApprovedPlanProtectedError):
            generate_week_menu(self.household, self.week, self.allan, seed=4)
        generate_week_menu(
            self.household, self.week, self.allan, seed=4, confirm_replace=True
        )
        plan.refresh_from_db()
        self.assertEqual(plan.status, MealPlan.Status.DRAFT)

    @override_settings(GENERATOR_MAX_COMBINATIONS=40)
    def test_avoids_previous_approved_week(self):
        generate_week_menu(self.household, self.week, self.allan, seed=1)
        approve_plan(self.household, self.week)
        previous_ids = set(
            MealPlanEntry.objects.filter(
                meal_plan__week_start=self.week
            ).values_list("recipe_id", flat=True)
        )
        next_week = self.week + timedelta(days=7)
        nxt = generate_week_menu(self.household, next_week, self.allan, seed=2)
        next_ids = set(nxt.entries.values_list("recipe_id", flat=True))
        self.assertTrue(previous_ids.isdisjoint(next_ids))

    def test_manual_change_can_repeat_recipe(self):
        plan = generate_week_menu(self.household, self.week, self.allan, seed=1)
        monday_recipe = plan.entries.get(day=self.week).recipe
        tuesday = self.week + timedelta(days=1)
        change_entry(self.household, self.week, tuesday, monday_recipe)
        self.assertEqual(plan.entries.get(day=self.week).recipe_id, monday_recipe.id)
        self.assertEqual(plan.entries.get(day=tuesday).recipe_id, monday_recipe.id)
        approve_plan(self.household, self.week)
        plan.refresh_from_db()
        self.assertEqual(plan.status, MealPlan.Status.APPROVED)

    def test_saving_one_day_also_saves_the_other_changes(self):
        self.client.login(username="allan", password="clave-segura-1")
        plan = generate_week_menu(self.household, self.week, self.allan, seed=1)
        tuesday = self.week + timedelta(days=1)
        wednesday = self.week + timedelta(days=2)
        monday_entry = plan.entries.get(day=self.week)
        tuesday_entry = plan.entries.get(day=tuesday)
        wednesday_entry = plan.entries.get(day=wednesday)
        replacement = (
            Recipe.objects.filter(household=self.household, is_active=True)
            .exclude(pk__in=[monday_entry.recipe_id, tuesday_entry.recipe_id])
            .order_by("name")
            .first()
        )
        response = self.client.post(
            f"/menu/{self.week.isoformat()}/dia/{self.week.isoformat()}/cambiar/",
            {
                "recipe": str(replacement.pk),
                "tambien": f"{tuesday.isoformat()}|{wednesday_entry.recipe_id}",
            },
        )
        self.assertRedirects(response, f"/menu/{self.week.isoformat()}/")
        self.assertEqual(plan.entries.get(day=self.week).recipe_id, replacement.pk)
        self.assertEqual(plan.entries.get(day=tuesday).recipe_id, wednesday_entry.recipe_id)
        self.assertEqual(plan.entries.get(day=wednesday).recipe_id, wednesday_entry.recipe_id)

    def test_cannot_use_foreign_recipe(self):
        generate_week_menu(self.household, self.week, self.allan, seed=1)
        with self.assertRaises(Exception):
            change_entry(
                self.household,
                self.week,
                self.week,
                self.foreign_recipes[0],
            )

    def test_api_idor(self):
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.get("/api/recipes/")
        names = [item["name"] for item in response.json()]
        own_ids = {str(pk) for pk in Recipe.objects.filter(household=self.household).values_list("id", flat=True)}
        returned_ids = {item["id"] for item in response.json()}
        self.assertTrue(returned_ids.issubset(own_ids))
        foreign = Recipe.objects.filter(household=self.other).first()
        self.assertNotIn(str(foreign.id), returned_ids)
        response = self.client.get(f"/api/recipes/{foreign.id}/")
        self.assertEqual(response.status_code, 404)

    def test_approve_requires_seven(self):
        plan = MealPlan.objects.create(
            household=self.household, week_start=self.week, created_by=self.allan
        )
        MealPlanEntry.objects.create(
            meal_plan=plan, day=self.week, recipe=self.recipes[0]
        )
        with self.assertRaises(Exception):
            approve_plan(self.household, self.week)

    def test_week_card_shows_the_dish_only_in_the_select(self):
        self.client.login(username="allan", password="clave-segura-1")
        plan = generate_week_menu(self.household, self.week, self.allan, seed=1)
        entry = plan.entries.select_related("recipe").order_by("day").first()
        response = self.client.get(f"/menu/{self.week.isoformat()}/")
        self.assertContains(response, 'class="day-rail-pick"')
        self.assertContains(response, f'data-category="{entry.recipe.get_category_display()}"')
        self.assertContains(response, " · propuesto")
        self.assertContains(response, "selected")
        self.assertNotContains(response, 'class="dish"')

    def test_day_button_shows_the_recipe(self):
        self.client.login(username="allan", password="clave-segura-1")
        plan = generate_week_menu(self.household, self.week, self.allan, seed=1)
        entry = plan.entries.select_related("recipe").order_by("day").first()
        recipe = entry.recipe
        recipe.ingredients = "600 g de carne\n4 patatas"
        recipe.steps = "Dorar la carne."
        recipe.prep_time_minutes = 40
        recipe.save()
        response = self.client.get(f"/menu/{self.week.isoformat()}/")
        self.assertContains(response, "day-open")
        self.assertContains(response, "600 g de carne")
        self.assertContains(response, "Dorar la carne.")
        self.assertContains(response, "40 min")
        self.assertContains(response, "Editar en el recetario")
        home = self.client.get("/inicio/")
        self.assertContains(home, "day-open")
        self.assertContains(home, "600 g de carne")
