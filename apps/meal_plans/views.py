from datetime import datetime, timedelta

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import HouseholdRequiredMixin
from apps.core.week import monday_of, weekday_label, weekday_short, week_dates
from apps.meal_plans.forms import ChangeDishForm
from apps.meal_plans.models import MealPlanEntry
from apps.meal_plans.selectors import get_plan_for_week, list_history
from apps.meal_plans.services.generator import (
    ApprovedPlanProtectedError,
    InsufficientRecipesError,
    generate_week_menu,
)
from apps.meal_plans.services.planning import (
    PlanningError,
    approve_plan,
    change_entry,
    suggest_alternative,
)
from apps.recipes.models import Recipe


def _parse_week(value):
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise Http404("Semana no válida.") from exc
    return monday_of(parsed)


class WeeklyMenuView(HouseholdRequiredMixin, TemplateView):
    template_name = "meal_plans/week.html"

    def get_week_start(self):
        raw = self.kwargs.get("week_start")
        if raw:
            return _parse_week(raw)
        return monday_of(timezone.localdate())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        week_start = self.get_week_start()
        today = timezone.localdate()
        plan = get_plan_for_week(self.request.household, week_start)
        entry_map = {}
        if plan:
            entry_map = {item.day: item for item in plan.entries.select_related("recipe")}
        days = []
        for day in week_dates(week_start):
            entry = entry_map.get(day)
            form = ChangeDishForm(
                household=self.request.household,
                current=entry.recipe_id if entry else None,
                auto_id=f"id_%s_{day.isoformat()}",
            )
            if entry:
                source = (
                    "elegido a mano"
                    if entry.selection_source == MealPlanEntry.Source.MANUAL
                    else "propuesto"
                )
                form.fields["recipe"].widget.attrs["data-current"] = str(entry.recipe_id)
                form.fields["recipe"].widget.attrs["data-source"] = source
            days.append(
                {
                    "date": day,
                    "label": weekday_label(day),
                    "short": weekday_short(day),
                    "is_today": day == today,
                    "entry": entry,
                    "form": form,
                }
            )
        context.update(
            {
                "week_start": week_start,
                "week_end": week_start + timedelta(days=6),
                "prev_week": week_start - timedelta(days=7),
                "next_week": week_start + timedelta(days=7),
                "current_week": monday_of(timezone.localdate()),
                "plan": plan,
                "days": days,
                "recipe_count": Recipe.objects.filter(
                    household=self.request.household, is_active=True
                ).count(),
            }
        )
        return context


class GenerateMenuView(HouseholdRequiredMixin, View):
    def post(self, request, week_start):
        start = _parse_week(week_start)
        confirm = request.POST.get("confirm_replace") == "1"
        try:
            generate_week_menu(
                request.household, start, request.user, confirm_replace=confirm
            )
            messages.success(request, "Menú generado como borrador.")
        except ApprovedPlanProtectedError as exc:
            messages.error(request, str(exc))
        except InsufficientRecipesError as exc:
            messages.error(request, str(exc))
        return redirect("meal_plans:week", week_start=start.isoformat())


class ChangeDishView(HouseholdRequiredMixin, View):
    def post(self, request, week_start, day):
        start = _parse_week(week_start)
        try:
            day_date = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError as exc:
            raise Http404("Día no válido.") from exc
        form = ChangeDishForm(request.POST, household=request.household)
        if not form.is_valid():
            messages.error(request, "Elige un plato válido.")
            return redirect("meal_plans:week", week_start=start.isoformat())
        try:
            change_entry(request.household, start, day_date, form.cleaned_data["recipe"])
            messages.success(request, "Plato actualizado.")
        except PlanningError as exc:
            messages.error(request, str(exc))
        if request.headers.get("HX-Request"):
            return redirect("meal_plans:week", week_start=start.isoformat())
        return redirect("meal_plans:week", week_start=start.isoformat())


class AlternativeDishView(HouseholdRequiredMixin, View):
    def post(self, request, week_start, day):
        start = _parse_week(week_start)
        try:
            day_date = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError as exc:
            raise Http404("Día no válido.") from exc
        try:
            alternative = suggest_alternative(request.household, start, day_date)
            change_entry(request.household, start, day_date, alternative)
            messages.success(request, f"Alternativa: {alternative.name}.")
        except PlanningError as exc:
            messages.error(request, str(exc))
        return redirect("meal_plans:week", week_start=start.isoformat())


class ApproveMenuView(HouseholdRequiredMixin, View):
    def post(self, request, week_start):
        start = _parse_week(week_start)
        try:
            approve_plan(request.household, start)
            messages.success(request, "Menú aprobado. Quedará en el historial.")
        except PlanningError as exc:
            messages.error(request, str(exc))
        return redirect("meal_plans:week", week_start=start.isoformat())


class HistoryView(HouseholdRequiredMixin, View):
    def get(self, request):
        plans = list_history(request.household)
        return render(request, "meal_plans/history.html", {"plans": plans})
