from django.urls import path

from apps.shopping.views import (
    AddRecipeIngredientsView,
    AddShoppingItemView,
    ClearBoughtView,
    RenameShoppingItemView,
    ReorderShoppingView,
    ShoppingFragmentView,
    ShoppingListView,
    ShoppingPushView,
    ToggleShoppingItemView,
)

app_name = "shopping"

urlpatterns = [
    path("lista/", ShoppingListView.as_view(), name="list"),
    path("lista/fragmento/", ShoppingFragmentView.as_view(), name="fragment"),
    path("lista/anadir/", AddShoppingItemView.as_view(), name="add"),
    path(
        "lista/desde-receta/<uuid:pk>/",
        AddRecipeIngredientsView.as_view(),
        name="from_recipe",
    ),
    path("lista/orden/", ReorderShoppingView.as_view(), name="order"),
    path("lista/<uuid:pk>/hecho/", ToggleShoppingItemView.as_view(), name="toggle"),
    path("lista/<uuid:pk>/nombre/", RenameShoppingItemView.as_view(), name="rename"),
    path("lista/vaciar/", ClearBoughtView.as_view(), name="clear"),
    path("lista/avisos/", ShoppingPushView.as_view(), name="push"),
]
