from django.urls import path

from apps.chores.views import ChoreListView, DeleteChoreView, ToggleChoreView

app_name = "chores"

urlpatterns = [
    path("por-hacer/", ChoreListView.as_view(), name="list"),
    path("por-hacer/<uuid:pk>/hecho/", ToggleChoreView.as_view(), name="toggle"),
    path("por-hacer/<uuid:pk>/borrar/", DeleteChoreView.as_view(), name="delete"),
]
