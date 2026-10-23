from django.urls import path

from apps.baby.views import (
    BabyFoodArchiveView,
    BabyFoodListView,
    BabyFoodUpdateView,
    BabyWeekView,
    SetBabyMealView,
    SuggestBabyDayView,
)

app_name = "baby"

urlpatterns = [
    path("bebe/", BabyWeekView.as_view(), name="current"),
    path("bebe/alimentos/", BabyFoodListView.as_view(), name="foods"),
    path("bebe/alimentos/<uuid:pk>/editar/", BabyFoodUpdateView.as_view(), name="edit"),
    path("bebe/alimentos/<uuid:pk>/archivo/", BabyFoodArchiveView.as_view(), name="archive"),
    path("bebe/<slug:week_start>/", BabyWeekView.as_view(), name="week"),
    path(
        "bebe/<slug:week_start>/dia/<slug:day>/",
        SetBabyMealView.as_view(),
        name="set",
    ),
    path(
        "bebe/<slug:week_start>/dia/<slug:day>/alternativa/",
        SuggestBabyDayView.as_view(),
        name="alternative",
    ),
]
