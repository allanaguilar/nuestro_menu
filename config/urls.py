from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings

from apps.core.views import HealthView, HomeView, OfflineView, ServiceWorkerView
from apps.households.views import SignUpView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", HealthView.as_view(), name="health"),
    path("offline/", OfflineView.as_view(), name="offline"),
    path("sw.js", ServiceWorkerView.as_view(), name="service-worker"),
    path(
        "manifest.webmanifest",
        RedirectView.as_view(url=settings.STATIC_URL + "manifest.webmanifest", permanent=False),
    ),
    path(
        "cuentas/entrar/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("cuentas/salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("cuentas/registro/", SignUpView.as_view(), name="signup"),
    path(
        "cuentas/clave/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "cuentas/clave/enviada/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "cuentas/clave/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "cuentas/clave/completa/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("api/", include("apps.api.urls")),
    path("", HomeView.as_view(), name="home"),
    path("", include("apps.core.urls")),
    path("", include("apps.households.urls")),
    path("", include("apps.recipes.urls")),
    path("", include("apps.preferences.urls")),
    path("", include("apps.meal_plans.urls")),
    path("", include("apps.baby.urls")),
]
