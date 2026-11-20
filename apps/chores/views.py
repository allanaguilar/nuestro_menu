from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.chores.forms import AddChoreForm
from apps.chores.models import Chore, ChorePhoto
from apps.chores.selectors import open_chores
from apps.chores.services import ChoreError, add_chore, save_chore_photo, set_chore_done
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


class ChorePhotoView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        chore = get_owned_or_404(Chore.objects.filter(household=request.household), pk=pk)
        uploads = request.FILES.getlist("foto") or [None]
        for uploaded in uploads:
            try:
                save_chore_photo(chore, uploaded)
            except ChoreError as exc:
                messages.error(request, str(exc))
                break
        return redirect("chores:list")


class ChorePhotoFileView(HouseholdRequiredMixin, View):
    def get(self, request, pk, photo_pk):
        photo = get_owned_or_404(
            ChorePhoto.objects.filter(chore__household=request.household, chore_id=pk),
            pk=photo_pk,
        )
        response = HttpResponse(bytes(photo.content), content_type=photo.content_type)
        response["Cache-Control"] = "private, max-age=3600"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class DeleteChorePhotoView(HouseholdRequiredMixin, View):
    def post(self, request, pk, photo_pk):
        photo = get_owned_or_404(
            ChorePhoto.objects.filter(chore__household=request.household, chore_id=pk),
            pk=photo_pk,
        )
        photo.delete()
        return redirect("chores:list")


class DeleteChoreView(HouseholdRequiredMixin, View):
    def post(self, request, pk):
        chore = get_owned_or_404(Chore.objects.filter(household=request.household), pk=pk)
        chore.delete()
        return redirect("chores:list")
