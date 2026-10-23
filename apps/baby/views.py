from datetime import datetime, timedelta

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.baby.forms import BabyFoodForm, BabyMealForm
from apps.baby.models import BabyFood, BabyPlanEntry
from apps.baby.selectors import active_baby_foods, get_baby_plan
from apps.baby.services import BabyPlanningError, new_foods_this_week, set_baby_meal
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
            slots = []
            for slot, label in BabyPlanEntry.Slot.choices:
                entry = entry_map.get((day, slot))
                current = entry.food_id if entry else None
                slots.append(
                    {
                        "slot": slot,
                        "label": label,
                        "entry": entry,
                        "form": BabyMealForm(
                            household=self.request.household,
                            current=current,
                            initial={"food": current},
                            auto_id=f"id_%s_{day.isoformat()}_{slot}",
                        ),
                    }
                )
            days.append(
                {
                    "date": day,
                    "label": weekday_label(day),
                    "short": weekday_short(day),
                    "is_today": day == today,
                    "slots": slots,
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
    def post(self, request, week_start, day, slot):
        start = _parse_week(week_start)
        day_date = _parse_day(day)
        form = BabyMealForm(request.POST, household=request.household)
        if not form.is_valid():
            messages.error(request, "Elige un alimento válido.")
            return redirect("baby:week", week_start=start.isoformat())
        try:
            set_baby_meal(
                request.household, start, day_date, slot, form.cleaned_data["food"]
            )
            messages.success(request, "Comida del bebé actualizada.")
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
