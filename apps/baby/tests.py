from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.baby.models import BabyFood, BabyPlanEntry
from apps.baby.services import set_baby_meal
from apps.core.week import monday_of
from apps.households.services import create_household_for_user
from apps.recipes.models import Recipe


class BabyMenuTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("allan", password="clave-segura-1")
        self.other_user = User.objects.create_user("vecino", password="clave-segura-1")
        self.household = create_household_for_user(self.user, "Casa")
        self.other = create_household_for_user(self.other_user, "Otra")
        self.week = monday_of(timezone.localdate())
        self.today = timezone.localdate()
        self.client.login(username="allan", password="clave-segura-1")

    def test_food_is_not_a_recipe(self):
        BabyFood.objects.create(
            household=self.household, name="Calabacín", texture=BabyFood.Texture.PUREE
        )
        self.assertFalse(Recipe.objects.filter(name="Calabacín").exists())
        response = self.client.get("/recetas/")
        self.assertNotContains(response, "Calabacín")

    def test_lunch_and_snack_same_day(self):
        zucchini = BabyFood.objects.create(household=self.household, name="Calabacín")
        pear = BabyFood.objects.create(
            household=self.household, name="Pera", texture=BabyFood.Texture.MASHED, is_new=False
        )
        set_baby_meal(self.household, self.week, self.today, BabyPlanEntry.Slot.LUNCH, zucchini)
        set_baby_meal(self.household, self.week, self.today, BabyPlanEntry.Slot.SNACK, pear)
        slots = set(
            BabyPlanEntry.objects.filter(day=self.today).values_list("slot", "food__name")
        )
        self.assertEqual(slots, {("comida", "Calabacín"), ("merienda", "Pera")})

    def test_other_household_food_is_rejected(self):
        foreign = BabyFood.objects.create(household=self.other, name="Plátano")
        response = self.client.post(
            f"/bebe/{self.week.isoformat()}/dia/{self.today.isoformat()}/",
            {"comida": str(foreign.pk), "merienda": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(BabyPlanEntry.objects.filter(food=foreign).exists())

    def test_notice_only_with_two_new_foods(self):
        zucchini = BabyFood.objects.create(household=self.household, name="Calabacín", is_new=True)
        pear = BabyFood.objects.create(household=self.household, name="Pera", is_new=True)
        set_baby_meal(self.household, self.week, self.today, BabyPlanEntry.Slot.LUNCH, zucchini)
        one = self.client.get(f"/bebe/{self.week.isoformat()}/")
        self.assertNotContains(one, "más de un alimento nuevo")
        set_baby_meal(
            self.household,
            self.week,
            self.today + timedelta(days=1) if self.today.weekday() < 6 else self.today - timedelta(days=1),
            BabyPlanEntry.Slot.LUNCH,
            pear,
        )
        two = self.client.get(f"/bebe/{self.week.isoformat()}/")
        self.assertContains(two, "Esta semana hay más de un alimento nuevo")

    def test_one_save_keeps_both_slots(self):
        zucchini = BabyFood.objects.create(household=self.household, name="Calabacín")
        pear = BabyFood.objects.create(household=self.household, name="Pera", is_new=False)
        response = self.client.post(
            f"/bebe/{self.week.isoformat()}/dia/{self.today.isoformat()}/",
            {"comida": str(zucchini.pk), "merienda": str(pear.pk)},
        )
        self.assertEqual(response.status_code, 302)
        slots = set(
            BabyPlanEntry.objects.filter(day=self.today).values_list("slot", "food__name")
        )
        self.assertEqual(slots, {("comida", "Calabacín"), ("merienda", "Pera")})

    def test_edit_renames_food(self):
        food = BabyFood.objects.create(household=self.household, name="Patata")
        response = self.client.post(
            f"/bebe/alimentos/{food.pk}/editar/",
            {"name": "Patata chafada", "texture": BabyFood.Texture.MASHED, "is_new": "on"},
        )
        self.assertEqual(response.status_code, 302)
        food.refresh_from_db()
        self.assertEqual(food.name, "Patata chafada")
        self.assertEqual(BabyFood.objects.filter(household=self.household).count(), 1)

    def test_dashboard_shows_today(self):
        food = BabyFood.objects.create(household=self.household, name="Calabacín")
        set_baby_meal(self.household, self.week, self.today, BabyPlanEntry.Slot.LUNCH, food)
        response = self.client.get("/inicio/")
        self.assertContains(response, "Hoy el bebé:")
        self.assertContains(response, "Calabacín")

    def test_day_card_shows_the_food_only_in_the_select(self):
        food = BabyFood.objects.create(
            household=self.household,
            name="Batata",
            texture=BabyFood.Texture.PUREE,
            is_new=True,
        )
        set_baby_meal(self.household, self.week, self.today, BabyPlanEntry.Slot.LUNCH, food)
        response = self.client.get(f"/bebe/{self.week.isoformat()}/")
        self.assertContains(response, 'class="baby-slot"')
        self.assertContains(response, 'data-texture="Puré"')
        self.assertContains(response, "Puré · nuevo")
        self.assertContains(response, 'aria-label="Guardar el')
        self.assertContains(response, 'aria-label="Proponer alternativa el')
        self.assertNotContains(response, 'class="dish"')
        self.assertNotContains(response, ">Guardar<")

    def test_alternative_moves_to_the_next_food(self):
        batata = BabyFood.objects.create(household=self.household, name="Batata")
        pollo = BabyFood.objects.create(
            household=self.household, name="Pollo", texture=BabyFood.Texture.PIECES
        )
        set_baby_meal(self.household, self.week, self.today, BabyPlanEntry.Slot.LUNCH, batata)
        set_baby_meal(self.household, self.week, self.today, BabyPlanEntry.Slot.SNACK, pollo)
        response = self.client.post(
            f"/bebe/{self.week.isoformat()}/dia/{self.today.isoformat()}/alternativa/"
        )
        self.assertEqual(response.status_code, 302)
        slots = dict(
            BabyPlanEntry.objects.filter(day=self.today).values_list("slot", "food__name")
        )
        self.assertEqual(slots, {"comida": "Pollo", "merienda": "Batata"})

    def test_alternative_uses_a_different_food_for_each_slot_and_saves_it(self):
        batata = BabyFood.objects.create(household=self.household, name="Batata")
        pollo = BabyFood.objects.create(household=self.household, name="Pollo")
        set_baby_meal(self.household, self.week, self.today, BabyPlanEntry.Slot.LUNCH, pollo)
        set_baby_meal(self.household, self.week, self.today, BabyPlanEntry.Slot.SNACK, pollo)
        response = self.client.post(
            f"/bebe/{self.week.isoformat()}/dia/{self.today.isoformat()}/alternativa/"
        )
        self.assertEqual(response.status_code, 302)
        slots = dict(
            BabyPlanEntry.objects.filter(day=self.today).values_list("slot", "food_id")
        )
        self.assertEqual(slots["comida"], batata.pk)
        self.assertEqual(slots["merienda"], pollo.pk)
        self.assertNotEqual(slots["comida"], slots["merienda"])
