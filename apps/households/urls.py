from django.urls import path

from apps.households.views import (
    AcceptInviteView,
    CreateInviteView,
    HouseholdSettingsView,
    OnboardingView,
)

app_name = "households"

urlpatterns = [
    path("hogar/", HouseholdSettingsView.as_view(), name="settings"),
    path("hogar/invitar/", CreateInviteView.as_view(), name="create_invite"),
    path("empezar/", OnboardingView.as_view(), name="onboarding"),
    path("invitar/<str:token>/", AcceptInviteView.as_view(), name="accept_invite"),
]
