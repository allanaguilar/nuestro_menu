from django.urls import path

from apps.api.views import (
    HouseholdView,
    InvitationAcceptView,
    InvitationView,
    MealPlanApproveView,
    MealPlanDetailView,
    MealPlanEntryView,
    MealPlanGenerateView,
    MealPlanHistoryView,
    PreferenceListView,
    RecipeBulkImportView,
    RecipeDetailView,
    RecipeListCreateView,
)

urlpatterns = [
    path("recipes/", RecipeListCreateView.as_view()),
    path("recipes/import/", RecipeBulkImportView.as_view()),
    path("recipes/<uuid:pk>/", RecipeDetailView.as_view()),
    path("meal-plans/", MealPlanHistoryView.as_view()),
    path("meal-plans/<slug:week_start>/", MealPlanDetailView.as_view()),
    path("meal-plans/<slug:week_start>/generate/", MealPlanGenerateView.as_view()),
    path(
        "meal-plans/<slug:week_start>/entries/<slug:day>/",
        MealPlanEntryView.as_view(),
    ),
    path("meal-plans/<slug:week_start>/approve/", MealPlanApproveView.as_view()),
    path("preferences/", PreferenceListView.as_view()),
    path("household/", HouseholdView.as_view()),
    path("invitations/", InvitationView.as_view()),
    path("invitations/accept/", InvitationAcceptView.as_view()),
]
