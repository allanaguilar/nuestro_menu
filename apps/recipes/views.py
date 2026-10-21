from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.core.mixins import HouseholdRequiredMixin, get_owned_or_404
from apps.preferences.selectors import preference_map
from apps.preferences.services import toggle_favorite
from apps.recipes.forms import RecipeForm
from apps.recipes.models import Recipe
from apps.recipes.selectors import recipes_for_household, search_recipes
from apps.recipes.services import archive_recipe, reactivate_recipe


class RecipeListView(HouseholdRequiredMixin, ListView):
    template_name = "recipes/list.html"
    context_object_name = "recipes"
    paginate_by = 30

    def get_queryset(self):
        return search_recipes(
            self.request.household,
            query=self.request.GET.get("q", ""),
            category=self.request.GET.get("categoria", ""),
            sort=self.request.GET.get("orden", "name"),
            include_archived=self.request.GET.get("archivo") == "1",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Recipe.Category.choices
        context["query"] = self.request.GET.get("q", "")
        context["selected_category"] = self.request.GET.get("categoria", "")
        context["sort"] = self.request.GET.get("orden", "name")
        context["include_archived"] = self.request.GET.get("archivo") == "1"
        prefs = preference_map(
            self.request.user, [recipe.id for recipe in context["recipes"]]
        )
        context["favorite_ids"] = {
            recipe_id for recipe_id, pref in prefs.items() if pref.is_favorite
        }
        return context


class RecipeCreateView(HouseholdRequiredMixin, CreateView):
    template_name = "recipes/form.html"
    form_class = RecipeForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["household"] = self.request.household
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Receta guardada.")
        return redirect("recipes:list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Nueva receta"
        return context


class RecipeUpdateView(HouseholdRequiredMixin, UpdateView):
    template_name = "recipes/form.html"
    form_class = RecipeForm
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return recipes_for_household(self.request.household)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["household"] = self.request.household
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Receta actualizada.")
        return redirect("recipes:list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Editar receta"
        return context


class RecipeArchiveView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        recipe = get_owned_or_404(recipes_for_household(request.household), pk=pk)
        if recipe.is_active:
            archive_recipe(recipe)
            messages.success(request, f"«{recipe.name}» se ha archivado. Sigue en el historial.")
        else:
            reactivate_recipe(recipe)
            messages.success(request, f"«{recipe.name}» está de nuevo activa.")
        return redirect(request.POST.get("next") or reverse("recipes:list"))


class RecipeFavoriteView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        recipe = get_owned_or_404(recipes_for_household(request.household), pk=pk)
        pref = toggle_favorite(request.user, recipe)
        if pref.is_favorite:
            messages.success(request, f"«{recipe.name}» marcada como favorita.")
        else:
            messages.success(request, f"«{recipe.name}» ya no es favorita.")
        return redirect(request.POST.get("next") or reverse("recipes:list"))
