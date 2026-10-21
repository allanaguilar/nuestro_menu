from django.urls import path

from apps.recipes.views import (
    RecipeArchiveView,
    RecipeCreateView,
    RecipeFavoriteView,
    RecipeImportView,
    RecipeListView,
    RecipeUpdateView,
)

app_name = "recipes"

urlpatterns = [
    path("recetas/", RecipeListView.as_view(), name="list"),
    path("recetas/nueva/", RecipeCreateView.as_view(), name="create"),
    path("recetas/importar/", RecipeImportView.as_view(), name="import"),
    path("recetas/<uuid:pk>/editar/", RecipeUpdateView.as_view(), name="update"),
    path("recetas/<uuid:pk>/archivo/", RecipeArchiveView.as_view(), name="archive"),
    path("recetas/<uuid:pk>/favorita/", RecipeFavoriteView.as_view(), name="favorite"),
]
