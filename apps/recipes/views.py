from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, FormView, ListView, UpdateView

from apps.core.mixins import HouseholdRequiredMixin, get_owned_or_404
from apps.preferences.selectors import preference_map
from apps.preferences.services import toggle_favorite
from apps.recipes.ai import RecipeReadError, interpret_recipe
from apps.recipes.forms import RecipeForm, RecipeImportForm
from apps.recipes.selectors import recipes_for_household, search_recipes
from apps.recipes.services import (
    RecipeDeleteError,
    archive_recipe,
    delete_archived_recipe,
    import_recipes_from_text,
    reactivate_recipe,
)


class RecipeListView(HouseholdRequiredMixin, ListView):
    template_name = "recipes/list.html"
    context_object_name = "recipes"
    paginate_by = 30

    def get_queryset(self):
        show_archived = self.request.GET.get("archivo") == "1"
        return search_recipes(
            self.request.household,
            query=self.request.GET.get("q", ""),
            archived_only=show_archived,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        context["include_archived"] = self.request.GET.get("archivo") == "1"
        prefs = preference_map(
            self.request.user, [recipe.id for recipe in context["recipes"]]
        )
        context["favorite_ids"] = {
            recipe_id for recipe_id, pref in prefs.items() if pref.is_favorite
        }
        return context


def render_recipe_form(request, *, title, form, recipe=None, pasted=""):
    action = (
        reverse("recipes:update", args=[recipe.pk])
        if recipe is not None
        else reverse("recipes:create")
    )
    return render(
        request,
        "recipes/form.html",
        {
            "title": title,
            "form": form,
            "recipe": recipe,
            "pasted": pasted,
            "form_action": action,
            "ai_enabled": bool(settings.GEMINI_API_KEY),
        },
    )


def recipe_form_data(recipe, parsed):
    data = dict(parsed)
    keep_meal = recipe.is_meal if recipe is not None else True
    if keep_meal:
        data["is_meal"] = "on"
    return data


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
        context["ai_enabled"] = bool(settings.GEMINI_API_KEY)
        context["pasted"] = ""
        context["recipe"] = None
        context["form_action"] = reverse("recipes:create")
        return context


class RecipeImportView(HouseholdRequiredMixin, FormView):
    template_name = "recipes/import.html"
    form_class = RecipeImportForm

    def form_valid(self, form):
        result = import_recipes_from_text(self.request.household, form.cleaned_data["text"])
        for error in result.errors:
            messages.error(self.request, error)
        if result.errors and not result.created and not result.skipped:
            return self.form_invalid(form)
        parts = []
        if result.created:
            parts.append(f"Se han importado {len(result.created)} recetas")
        if result.skipped:
            parts.append(f"{len(result.skipped)} ya existían y no se han duplicado")
        if parts:
            messages.success(self.request, ". ".join(parts) + ".")
        return redirect("recipes:list")


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
        context["ai_enabled"] = bool(settings.GEMINI_API_KEY)
        context["pasted"] = ""
        context["recipe"] = self.object
        context["form_action"] = reverse("recipes:update", args=[self.object.pk])
        return context


class RecipeInterpretView(HouseholdRequiredMixin, View):
    def get(self, request):
        return redirect("recipes:create")

    def post(self, request):
        pasted = request.POST.get("source", "")
        recipe = None
        pk = (request.POST.get("pk") or "").strip()
        if pk:
            recipe = get_owned_or_404(recipes_for_household(request.household), pk=pk)
        title = "Editar receta" if recipe is not None else "Nueva receta"
        try:
            parsed = interpret_recipe(pasted)
        except RecipeReadError:
            messages.error(request, "No se pudo leer la receta. Escríbela en el formulario.")
            form = RecipeForm(household=request.household, instance=recipe)
        else:
            form = RecipeForm(
                data=recipe_form_data(recipe, parsed),
                household=request.household,
                instance=recipe,
            )
        return render_recipe_form(
            request, title=title, form=form, recipe=recipe, pasted=pasted
        )


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


class RecipeDeleteView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        recipe = get_owned_or_404(recipes_for_household(request.household), pk=pk)
        archived = reverse("recipes:list") + "?archivo=1"
        try:
            name = recipe.name
            delete_archived_recipe(recipe)
        except RecipeDeleteError as exc:
            messages.error(request, str(exc))
            return redirect(request.POST.get("next") or archived)
        messages.success(request, f"«{name}» se ha eliminado.")
        return redirect(request.POST.get("next") or archived)


class RecipeFavoriteView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        recipe = get_owned_or_404(recipes_for_household(request.household), pk=pk)
        pref = toggle_favorite(request.user, recipe)
        if pref.is_favorite:
            messages.success(request, f"«{recipe.name}» marcada como favorita.")
        else:
            messages.success(request, f"«{recipe.name}» ya no es favorita.")
        return redirect(request.POST.get("next") or reverse("recipes:list"))
