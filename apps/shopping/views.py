import json

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import HouseholdRequiredMixin, get_owned_or_404
from apps.shopping.forms import AddShoppingItemForm
from apps.shopping.models import ShoppingItem, ShoppingPushSubscription, product_key
from apps.shopping.push import added_notice, cleared_notice, notify_others
from apps.recipes.selectors import recipes_for_household
from apps.shopping.selectors import person_label, shopping_page, touch_presence
from apps.shopping.services import (
    ShoppingError,
    add_recipe_ingredients,
    add_shopping_item,
    clear_bought,
    rename_shopping_item,
    reorder_shopping_items,
)


def shop_client_key(request):
    raw = request.headers.get("X-Shop-Client") or request.POST.get("client_key") or ""
    return raw[:64]


def shop_state(request, form=None):
    client_key = shop_client_key(request)
    touch_presence(request.household, request.user, client_key)
    context = shopping_page(request.household, request.user, form, client_key)
    context["html"] = render_to_string("shopping/live.html", context, request=request)
    context["vapid_public_key"] = settings.VAPID_PUBLIC_KEY
    return context


def shop_json(request, form=None, extra=None):
    state = shop_state(request, form)
    payload = {
        "html": state["html"],
        "revision": state["revision"],
        "viewers": state["viewers"],
        "pending": state["pending_label"],
    }
    if extra:
        payload.update(extra)
    return JsonResponse(payload)


def shop_form_error(form):
    for error in form["name"].errors:
        return str(error)
    return "Escribe lo que falta."


def shop_add_conflict(request, form, message):
    matched = ShoppingItem.objects.filter(
        household=request.household,
        normalized_name=product_key(form.cleaned_data.get("name") or ""),
    ).first()
    extra = {"error": message}
    if matched:
        extra["matched_id"] = str(matched.pk)
    return extra


def wants_shop_fragment(request):
    return request.headers.get("X-Shop") == "1"


class ShoppingListView(HouseholdRequiredMixin, TemplateView):
    template_name = "shopping/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(shop_state(self.request))
        return context


class ShoppingFragmentView(HouseholdRequiredMixin, View):
    def get(self, request):
        return shop_json(request)


class AddShoppingItemView(HouseholdRequiredMixin, View):
    def post(self, request):
        form = AddShoppingItemForm(request.POST)
        if form.is_valid():
            try:
                item = add_shopping_item(
                    request.household, form.cleaned_data["name"], request.user
                )
            except ShoppingError as exc:
                if wants_shop_fragment(request):
                    return shop_json(request, form, shop_add_conflict(request, form, str(exc)))
                form.add_error("name", str(exc))
            else:
                notify_others(
                    request.household,
                    request.user,
                    shop_client_key(request),
                    added_notice(request.user, item.name),
                )
                if wants_shop_fragment(request):
                    return shop_json(request, extra={"created_id": str(item.pk)})
                return redirect("shopping:list")
        if wants_shop_fragment(request):
            return shop_json(request, form, {"error": shop_form_error(form)})
        return render(
            request,
            "shopping/list.html",
            shop_state(request, form),
        )


def ingredients_message(added, skipped):
    if added == 0:
        return "Esos ingredientes ya estaban en la lista."
    if added == 1 and skipped == 0:
        return "1 ingrediente añadido a la compra."
    if added == 1:
        return "1 ingrediente añadido. El resto ya estaba en la lista."
    if skipped:
        return f"{added} ingredientes añadidos. El resto ya estaba en la lista."
    return f"{added} ingredientes añadidos a la compra."


def same_site_next(request):
    target = (request.POST.get("next") or "").strip()
    if target.startswith("/") and not target.startswith("//"):
        return target
    return reverse("shopping:list")


class AddRecipeIngredientsView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        recipe = get_owned_or_404(recipes_for_household(request.household), pk=pk)
        if not recipe.ingredient_lines:
            messages.error(request, "Esta receta no tiene ingredientes.")
            return redirect(same_site_next(request))
        added, skipped = add_recipe_ingredients(request.household, recipe, request.user)
        if added:
            notify_others(
                request.household,
                request.user,
                shop_client_key(request),
                f"{person_label(request.user)} añadió ingredientes de {recipe.name}",
            )
        messages.success(request, ingredients_message(added, skipped))
        return redirect(same_site_next(request))


class ToggleShoppingItemView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        item = get_owned_or_404(
            ShoppingItem.objects.filter(household=request.household), pk=pk
        )
        item.done = request.POST.get("done") == "1"
        item.save(update_fields=["done", "updated_at"])
        if wants_shop_fragment(request):
            return shop_json(request)
        return redirect("shopping:list")


class RenameShoppingItemView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        item = get_owned_or_404(
            ShoppingItem.objects.filter(household=request.household), pk=pk
        )
        try:
            rename_shopping_item(item, request.POST.get("name", ""))
        except ShoppingError as exc:
            if wants_shop_fragment(request):
                return shop_json(request, extra={"error": str(exc)})
            messages.error(request, str(exc))
            return redirect("shopping:list")
        if wants_shop_fragment(request):
            return shop_json(request)
        return redirect("shopping:list")


class ReorderShoppingView(HouseholdRequiredMixin, View):
    def post(self, request):
        ordered = [part for part in (request.POST.get("order") or "").split(",") if part]
        reorder_shopping_items(request.household, ordered)
        if wants_shop_fragment(request):
            return shop_json(request)
        return redirect("shopping:list")


class ClearBoughtView(HouseholdRequiredMixin, View):
    def post(self, request):
        removed = clear_bought(request.household, request.user)
        if removed:
            notify_others(
                request.household,
                request.user,
                shop_client_key(request),
                cleared_notice(request.user),
            )
        if wants_shop_fragment(request):
            return shop_json(request)
        return redirect("shopping:list")


class ShoppingPushView(HouseholdRequiredMixin, View):
    def post(self, request):
        try:
            payload = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"ok": False}, status=400)
        endpoint = str(payload.get("endpoint") or "").strip()
        keys = payload.get("keys") or {}
        p256dh = str(keys.get("p256dh") or "").strip()
        auth = str(keys.get("auth") or "").strip()
        client_key = str(payload.get("client_key") or "")[:64]
        if (
            not endpoint.startswith("https://")
            or len(endpoint) > 2000
            or not p256dh
            or len(p256dh) > 255
            or not auth
            or len(auth) > 255
        ):
            return JsonResponse({"ok": False}, status=400)
        ShoppingPushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "household": request.household,
                "user": request.user,
                "client_key": client_key,
                "p256dh": p256dh,
                "auth": auth,
            },
        )
        return JsonResponse({"ok": True})
