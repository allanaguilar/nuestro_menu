from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import HouseholdRequiredMixin, get_owned_or_404
from apps.shopping.forms import AddShoppingItemForm
from apps.shopping.models import ShoppingItem
from apps.shopping.selectors import shopping_page
from apps.shopping.services import ShoppingError, add_shopping_item, clear_bought


class ShoppingListView(HouseholdRequiredMixin, TemplateView):
    template_name = "shopping/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(shopping_page(self.request.household))
        return context


class AddShoppingItemView(HouseholdRequiredMixin, View):
    def post(self, request):
        form = AddShoppingItemForm(request.POST)
        if form.is_valid():
            try:
                add_shopping_item(request.household, form.cleaned_data["name"])
            except ShoppingError as exc:
                form.add_error("name", str(exc))
            else:
                return redirect("shopping:list")
        return render(request, "shopping/list.html", shopping_page(request.household, form))


class ToggleShoppingItemView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        item = get_owned_or_404(
            ShoppingItem.objects.filter(household=request.household), pk=pk
        )
        item.done = request.POST.get("done") == "1"
        item.save(update_fields=["done", "updated_at"])
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
        return redirect("shopping:list")


class ClearBoughtView(HouseholdRequiredMixin, View):
    def post(self, request):
        clear_bought(request.household)
        return redirect("shopping:list")
