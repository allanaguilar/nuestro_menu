from django.urls import path

from apps.shopping.views import (
    AddShoppingItemView,
    ClearBoughtView,
    MoveShoppingItemView,
    ShoppingFragmentView,
    ShoppingListView,
    ToggleShoppingItemView,
)

app_name = "shopping"

urlpatterns = [
    path("lista/", ShoppingListView.as_view(), name="list"),
    path("lista/fragmento/", ShoppingFragmentView.as_view(), name="fragment"),
    path("lista/anadir/", AddShoppingItemView.as_view(), name="add"),
    path("lista/<uuid:pk>/hecho/", ToggleShoppingItemView.as_view(), name="toggle"),
    path("lista/<uuid:pk>/pasillo/", MoveShoppingItemView.as_view(), name="aisle"),
    path("lista/vaciar/", ClearBoughtView.as_view(), name="clear"),
]
