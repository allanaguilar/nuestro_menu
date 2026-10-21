from django.urls import path

from apps.meal_plans.views import (
    AlternativeDishView,
    ApproveMenuView,
    ChangeDishView,
    GenerateMenuView,
    HistoryView,
    WeeklyMenuView,
)

app_name = "meal_plans"

urlpatterns = [
    path("menu/", WeeklyMenuView.as_view(), name="current"),
    path("menu/<slug:week_start>/", WeeklyMenuView.as_view(), name="week"),
    path("menu/<slug:week_start>/generar/", GenerateMenuView.as_view(), name="generate"),
    path(
        "menu/<slug:week_start>/dia/<slug:day>/cambiar/",
        ChangeDishView.as_view(),
        name="change",
    ),
    path(
        "menu/<slug:week_start>/dia/<slug:day>/alternativa/",
        AlternativeDishView.as_view(),
        name="alternative",
    ),
    path("menu/<slug:week_start>/aprobar/", ApproveMenuView.as_view(), name="approve"),
    path("historial/", HistoryView.as_view(), name="history"),
]
