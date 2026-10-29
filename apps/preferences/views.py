from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from apps.core.mixins import HouseholdRequiredMixin
from apps.preferences.forms import PreferenceForm
from apps.preferences.models import RecipePreference
from apps.preferences.services import upsert_preference
from apps.recipes.selectors import list_active_recipes


class PreferenceListView(HouseholdRequiredMixin, View):
    template_name = "preferences/list.html"

    def get(self, request):
        recipes = list_active_recipes(request.household).order_by("name")
        existing = {
            pref.recipe_id: pref
            for pref in RecipePreference.objects.filter(
                user=request.user, recipe__household=request.household
            )
        }
        rows = []
        for recipe in recipes:
            pref = existing.get(recipe.id)
            form = PreferenceForm(instance=pref, prefix=str(recipe.id))
            rows.append({"recipe": recipe, "form": form, "pref": pref})
        return render(request, self.template_name, {"rows": rows})

    def post(self, request):
        recipe_id = request.POST.get("recipe_id")
        recipes = {str(item.id): item for item in list_active_recipes(request.household)}
        recipe = recipes.get(recipe_id)
        if recipe is None:
            messages.error(request, "Receta no encontrada.")
            return redirect("preferences:list")
        form = PreferenceForm(request.POST, prefix=str(recipe.id))
        if form.is_valid():
            rating = form.cleaned_data.get("rating") or None
            upsert_preference(
                request.user,
                recipe,
                rating=rating,
                is_avoided=form.cleaned_data.get("is_avoided"),
            )
            messages.success(request, f"Preferencias de «{recipe.name}» guardadas.")
        else:
            messages.error(request, "Revisa los datos de la preferencia.")
        return redirect("preferences:list")
