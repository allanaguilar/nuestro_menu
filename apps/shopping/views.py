import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import HouseholdRequiredMixin, get_owned_or_404
from apps.shopping.forms import AddShoppingItemForm
from apps.shopping.models import ShoppingItem, ShoppingPushSubscription
from apps.shopping.push import added_notice, cleared_notice, notify_others
from apps.shopping.selectors import shopping_page, touch_presence
from apps.shopping.services import ShoppingError, add_shopping_item, clear_bought


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


def shop_json(request, form=None):
    state = shop_state(request, form)
    return JsonResponse(
        {
            "html": state["html"],
            "revision": state["revision"],
            "viewers": state["viewers"],
            "pending": state["pending_label"],
        }
    )


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
                form.add_error("name", str(exc))
            else:
                notify_others(
                    request.household,
                    request.user,
                    shop_client_key(request),
                    added_notice(request.user, item.name),
                )
                return redirect("shopping:list")
        return render(
            request,
            "shopping/list.html",
            shop_state(request, form),
        )


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


class MoveShoppingItemView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        item = get_owned_or_404(
            ShoppingItem.objects.filter(household=request.household), pk=pk
        )
        aisle = request.POST.get("aisle", "")
        if aisle in ShoppingItem.Aisle.values and not item.done:
            item.aisle = aisle
            item.save(update_fields=["aisle", "updated_at"])
        if wants_shop_fragment(request):
            return shop_json(request)
        return redirect("shopping:list")


class ClearBoughtView(HouseholdRequiredMixin, View):
    def post(self, request):
        removed = clear_bought(request.household)
        if removed:
            notify_others(
                request.household,
                request.user,
                shop_client_key(request),
                cleared_notice(request.user),
            )
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
