from django.urls import path

from apps.preferences.views import PreferenceListView

app_name = "preferences"

urlpatterns = [
    path("preferencias/", PreferenceListView.as_view(), name="list"),
]
