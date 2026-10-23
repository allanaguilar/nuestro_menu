from django.urls import path

from apps.baby.views import (
    BabyFoodArchiveView,
    BabyFoodListView,
    BabyWeekView,
    SetBabyMealView,
)

app_name = "baby"

urlpatterns = [
    path("bebe/", BabyWeekView.as_view(), name="current"),
    path("bebe/alimentos/", BabyFoodListView.as_view(), name="foods"),
    path("bebe/alimentos/<uuid:pk>/archivo/", BabyFoodArchiveView.as_view(), name="archive"),
    path("bebe/<slug:week_start>/", BabyWeekView.as_view(), name="week"),
    path(
        "bebe/<slug:week_start>/dia/<slug:day>/<slug:slot>/",
        SetBabyMealView.as_view(),
        name="set",
    ),
]
