from django.urls import path

from apps.core.views import DashboardView, HouseChatView, InstallView, SummaryView

app_name = "core"

urlpatterns = [
    path("inicio/", DashboardView.as_view(), name="dashboard"),
    path("instalar/", InstallView.as_view(), name="install"),
    path("resumen/", SummaryView.as_view(), name="summary"),
    path("casa/", HouseChatView.as_view(), name="house-chat"),
]
