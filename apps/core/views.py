from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django.http import FileResponse, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.baby.selectors import baby_meals_on
from apps.core.mixins import HouseholdRequiredMixin
from apps.core.week import monday_of, weekday_label, weekday_short
from apps.households.selectors import get_user_membership
from apps.meal_plans.selectors import get_plan_for_week
from apps.recipes.selectors import list_active_recipes, recipe_count


class HealthView(View):
    def get(self, request):
        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            db_ok = False
        status = 200 if db_ok else 503
        return JsonResponse({"status": "ok" if db_ok else "error", "database": db_ok}, status=status)


class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        membership = get_user_membership(request.user)
        if membership is None:
            return redirect("households:onboarding")
        return redirect("core:dashboard")


class DashboardView(HouseholdRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        week_start = monday_of(today)
        plan = get_plan_for_week(self.request.household, week_start)
        entries = []
        entry_map = {}
        if plan:
            entry_map = {item.day: item for item in plan.entries.select_related("recipe").all()}
        for day in range(7):
            from datetime import timedelta

            current = week_start + timedelta(days=day)
            entry = entry_map.get(current)
            entries.append(
                {
                    "date": current,
                    "label": weekday_label(current),
                    "short": weekday_short(current),
                    "is_today": current == today,
                    "entry": entry,
                }
            )
        baby = baby_meals_on(self.request.household, today)
        context.update(
            {
                "week_start": week_start,
                "plan": plan,
                "entries": entries,
                "recipe_total": recipe_count(self.request.household),
                "active_recipes": list_active_recipes(self.request.household).count(),
                "baby_lunch": baby.get("comida"),
                "baby_snack": baby.get("merienda"),
            }
        )
        return context


class OfflineView(TemplateView):
    template_name = "offline.html"


class ServiceWorkerView(View):
    def get(self, request):
        path = settings.BASE_DIR / "static" / "service-worker.js"
        response = FileResponse(path.open("rb"), content_type="application/javascript")
        response["Service-Worker-Allowed"] = "/"
        response["Cache-Control"] = "no-cache"
        return response


class InstallView(HouseholdRequiredMixin, TemplateView):
    template_name = "core/install.html"
