from datetime import datetime, timedelta

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, UpdateView

from apps.baby.forms import BabyDayForm, BabyFoodForm
from apps.baby.models import BabyFood, BabyPlanEntry
from apps.baby.selectors import active_baby_foods, get_baby_plan
from apps.baby.services import (
    BabyPlanningError,
    new_foods_this_week,
    set_baby_meal,
    suggest_baby_day,
)
from apps.core.mixins import HouseholdRequiredMixin, get_owned_or_404
from apps.core.week import monday_of, week_dates, weekday_label, weekday_short


def _parse_week(value):
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise Http404("Semana no válida.") from exc
    return monday_of(parsed)


def _parse_day(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise Http404("Día no válido.") from exc


class BabyWeekView(HouseholdRequiredMixin, TemplateView):
    template_name = "baby/week.html"

    def get_week_start(self):
        raw = self.kwargs.get("week_start")
        if raw:
            return _parse_week(raw)
        return monday_of(timezone.localdate())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        week_start = self.get_week_start()
        today = timezone.localdate()
        plan = get_baby_plan(self.request.household, week_start)
        entry_map = {}
        if plan:
            entry_map = {(item.day, item.slot): item for item in plan.entries.all()}
        days = []
        for day in week_dates(week_start):
            lunch = entry_map.get((day, BabyPlanEntry.Slot.LUNCH))
            snack = entry_map.get((day, BabyPlanEntry.Slot.SNACK))
            days.append(
                {
                    "date": day,
                    "label": weekday_label(day),
                    "short": weekday_short(day),
                    "is_today": day == today,
                    "lunch": lunch,
                    "snack": snack,
                    "form": BabyDayForm(
                        household=self.request.household,
                        lunch=lunch.food_id if lunch else None,
                        snack=snack.food_id if snack else None,
                        initial={
                            "comida": lunch.food_id if lunch else None,
                            "merienda": snack.food_id if snack else None,
                        },
                        auto_id=f"id_%s_{day.isoformat()}",
                    ),
                }
            )
        new_foods = list(new_foods_this_week(plan))
        context.update(
            {
                "week_start": week_start,
                "prev_week": week_start - timedelta(days=7),
                "next_week": week_start + timedelta(days=7),
                "days": days,
                "new_foods": new_foods,
                "food_count": active_baby_foods(self.request.household).count(),
            }
        )
        return context


class SetBabyMealView(HouseholdRequiredMixin, View):
    def post(self, request, week_start, day):
        start = _parse_week(week_start)
        day_date = _parse_day(day)
        lunch = None
        snack = None
        plan = get_baby_plan(request.household, start)
        if plan:
            for entry in plan.entries.filter(day=day_date):
                if entry.slot == BabyPlanEntry.Slot.LUNCH:
                    lunch = entry.food_id
                elif entry.slot == BabyPlanEntry.Slot.SNACK:
                    snack = entry.food_id
        form = BabyDayForm(request.POST, household=request.household, lunch=lunch, snack=snack)
        if not form.is_valid():
            messages.error(request, "Elige alimentos válidos.")
            return redirect("baby:week", week_start=start.isoformat())
        try:
            set_baby_meal(
                request.household,
                start,
                day_date,
                BabyPlanEntry.Slot.LUNCH,
                form.cleaned_data["comida"],
            )
            set_baby_meal(
                request.household,
                start,
                day_date,
                BabyPlanEntry.Slot.SNACK,
                form.cleaned_data["merienda"],
            )
            messages.success(request, "Día del bebé actualizado.")
        except BabyPlanningError as exc:
            messages.error(request, str(exc))
        return redirect("baby:week", week_start=start.isoformat())


class SuggestBabyDayView(HouseholdRequiredMixin, View):
    def post(self, request, week_start, day):
        start = _parse_week(week_start)
        day_date = _parse_day(day)
        try:
            suggest_baby_day(request.household, start, day_date)
            messages.success(request, "Propuesta nueva para ese día.")
        except BabyPlanningError as exc:
            messages.error(request, str(exc))
        return redirect("baby:week", week_start=start.isoformat())


class BabyFoodListView(HouseholdRequiredMixin, TemplateView):
    template_name = "baby/foods.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or BabyFoodForm()
        context["foods"] = BabyFood.objects.filter(
            household=self.request.household
        ).order_by("-is_active", "name")
        return context

    def post(self, request):
        form = BabyFoodForm(request.POST)
        if form.is_valid():
            food = form.save(commit=False)
            food.household = request.household
            food.save()
            messages.success(request, f"«{food.name}» añadido.")
            return redirect("baby:foods")
        return self.render_to_response(self.get_context_data(form=form))


class BabyFoodUpdateView(HouseholdRequiredMixin, UpdateView):
    model = BabyFood
    form_class = BabyFoodForm
    template_name = "baby/food_form.html"
    context_object_name = "food"

    def get_queryset(self):
        return BabyFood.objects.filter(household=self.request.household)

    def form_valid(self, form):
        messages.success(self.request, f"«{form.instance.name}» actualizado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("baby:foods")


class BabyFoodArchiveView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        food = get_owned_or_404(
            BabyFood.objects.filter(household=request.household), pk=pk
        )
        food.is_active = not food.is_active
        food.save(update_fields=["is_active", "updated_at"])
        if food.is_active:
            messages.success(request, f"«{food.name}» vuelve a estar disponible.")
        else:
            messages.success(request, f"«{food.name}» archivado.")
        return redirect("baby:foods")
