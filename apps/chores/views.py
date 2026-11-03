from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.chores.forms import AddChoreForm
from apps.chores.models import Chore
from apps.chores.selectors import open_chores
from apps.chores.services import ChoreError, add_chore, set_chore_done
from apps.core.mixins import HouseholdRequiredMixin, get_owned_or_404


def chore_form(household, data=None):
    form = AddChoreForm(data)
    form.fields["assignee"].queryset = User.objects.filter(
        household_memberships__household=household
    ).order_by("household_memberships__joined_at")
    return form


class ChoreListView(HouseholdRequiredMixin, TemplateView):
    template_name = "chores/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        context["today"] = today
        context["form"] = context.get("form") or chore_form(self.request.household)
        context.update(open_chores(self.request.household, today))
        return context

    def post(self, request):
        form = chore_form(request.household, request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        try:
            add_chore(
                request.household,
                form.cleaned_data["title"],
                form.cleaned_data["cadence"],
                form.cleaned_data["assignee"],
                timezone.localdate(),
            )
        except ChoreError as exc:
            messages.error(request, str(exc))
        return redirect("chores:list")


class ToggleChoreView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        chore = get_owned_or_404(Chore.objects.filter(household=request.household), pk=pk)
        set_chore_done(chore, timezone.localdate(), request.POST.get("done") == "1")
        return redirect("chores:list")
