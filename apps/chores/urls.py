from django.urls import path

from apps.chores.views import (
    ChoreListView,
    ChorePhotoFileView,
    ChorePhotoView,
    DeleteChorePhotoView,
    DeleteChoreView,
    ToggleChoreView,
    UpdateChoreView,
)

app_name = "chores"

urlpatterns = [
    path("por-hacer/", ChoreListView.as_view(), name="list"),
    path("por-hacer/<uuid:pk>/hecho/", ToggleChoreView.as_view(), name="toggle"),
    path("por-hacer/<uuid:pk>/editar/", UpdateChoreView.as_view(), name="update"),
    path("por-hacer/<uuid:pk>/borrar/", DeleteChoreView.as_view(), name="delete"),
    path("por-hacer/<uuid:pk>/foto/", ChorePhotoView.as_view(), name="photo"),
    path("por-hacer/<uuid:pk>/foto/<uuid:photo_pk>/", ChorePhotoFileView.as_view(), name="photo_file"),
    path(
        "por-hacer/<uuid:pk>/foto/<uuid:photo_pk>/borrar/",
        DeleteChorePhotoView.as_view(),
        name="photo_delete",
    ),
]
