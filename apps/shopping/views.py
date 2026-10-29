from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import HouseholdRequiredMixin, get_owned_or_404
from apps.shopping.forms import AddShoppingItemForm
from apps.shopping.models import ShoppingItem
from apps.shopping.selectors import shopping_page, touch_presence
from apps.shopping.services import ShoppingError, add_shopping_item, clear_bought


def shop_state(request, form=None):
    touch_presence(request.household, request.user)
    context = shopping_page(request.household, request.user, form)
    context["html"] = render_to_string("shopping/live.html", context, request=request)
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
                add_shopping_item(
                    request.household, form.cleaned_data["name"], request.user
                )
            except ShoppingError as exc:
                form.add_error("name", str(exc))
            else:
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
        clear_bought(request.household)
        return redirect("shopping:list")
