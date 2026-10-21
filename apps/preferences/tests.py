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

    def test_unique_user_recipe(self):
        RecipePreference.objects.create(user=self.allan, recipe=self.recipe, rating=5)
        with self.assertRaises(Exception):
            RecipePreference.objects.create(user=self.allan, recipe=self.recipe, rating=1)
