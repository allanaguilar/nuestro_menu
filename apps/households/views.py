from django.contrib import messages
from django.contrib.auth import login, views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView

from apps.core.mail import EmailDeliveryError
from apps.core.mixins import HouseholdRequiredMixin
from apps.households.forms import HouseholdSettingsForm, PasswordResetForm, SignUpForm
from apps.households.models import HouseholdInvite
from apps.households.selectors import get_user_membership, list_members
from apps.households.services import (
    InviteError,
    accept_invite,
    create_household_for_user,
    create_invite,
)


class PasswordResetView(auth_views.PasswordResetView):
    form_class = PasswordResetForm

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except EmailDeliveryError:
            form.add_error(
                None,
                "No se pudo enviar el correo. Inténtalo de nuevo en unos minutos.",
            )
            return self.form_invalid(form)


class SignUpView(FormView):
    template_name = "registration/signup.html"
    form_class = SignUpForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def _invite_token(self):
        if self.request.method == "POST":
            return (self.request.POST.get("invite_token") or "").strip()
        return (self.request.GET.get("token") or "").strip()

    def _invite(self):
        token = self._invite_token()
        if not token:
            return None
        return (
            HouseholdInvite.objects.select_related("household")
            .filter(token=token)
            .first()
        )

    def get_initial(self):
        initial = super().get_initial()
        initial["invite_token"] = self._invite_token()
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invite = self._invite()
        context["invited"] = bool(self._invite_token())
        context["invited_household"] = (
            invite.household.name if invite and invite.is_valid else ""
        )
        return context

    def form_valid(self, form):
        user = form.save()
        token = form.cleaned_data.get("invite_token") or ""
        try:
            if token:
                accept_invite(user, token)
            else:
                create_household_for_user(user, form.cleaned_data["household_name"])
        except InviteError as exc:
            user.delete()
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        login(self.request, user)
        messages.success(self.request, "Cuenta creada. Bienvenido a Nuestro Menú.")
        return redirect("core:dashboard")


class OnboardingView(LoginRequiredMixin, TemplateView):
    template_name = "households/onboarding.html"

    def dispatch(self, request, *args, **kwargs):
        if get_user_membership(request.user):
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        name = (request.POST.get("household_name") or "").strip()
        token = (request.POST.get("invite_token") or "").strip()
        if token:
            try:
                accept_invite(request.user, token)
                messages.success(request, "Te has unido al hogar.")
                return redirect("core:dashboard")
            except InviteError as exc:
                messages.error(request, str(exc))
        elif name:
            create_household_for_user(request.user, name)
            messages.success(request, "Hogar creado.")
            return redirect("core:dashboard")
        else:
            messages.error(request, "Indica un nombre o un código de invitación.")
        return render(request, self.template_name)


class HouseholdSettingsView(HouseholdRequiredMixin, FormView):
    template_name = "households/settings.html"
    form_class = HouseholdSettingsForm

    def get_initial(self):
        return {"name": self.request.household.name}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["members"] = list_members(self.request.household)
        context["is_owner"] = (
            self.request.membership.role == self.request.membership.Role.OWNER
        )
        latest_invite = (
            HouseholdInvite.objects.filter(
                household=self.request.household, used_at__isnull=True
            )
            .order_by("-created_at")
            .first()
        )
        context["latest_invite"] = latest_invite
        if latest_invite and latest_invite.is_valid:
            context["invite_url"] = self.request.build_absolute_uri(
                reverse("households:accept_invite", args=[latest_invite.token])
            )
        return context

    def form_valid(self, form):
        household = self.request.household
        household.name = form.cleaned_data["name"]
        household.save(update_fields=["name"])
        messages.success(self.request, "Hogar actualizado.")
        return redirect("households:settings")


class CreateInviteView(HouseholdRequiredMixin, View):
    def post(self, request):
        if request.membership.role != request.membership.Role.OWNER:
            messages.error(request, "Solo la persona propietaria puede invitar.")
            return redirect("households:settings")
        invite = create_invite(request.household, request.user)
        url = request.build_absolute_uri(
            reverse("households:accept_invite", args=[invite.token])
        )
        messages.success(
            request,
            f"Invitación creada. Copia este enlace y envíaselo a la otra persona: {url}",
        )
        return redirect("households:settings")


class AcceptInviteView(View):
    def get(self, request, token):
        try:
            invite = HouseholdInvite.objects.get(token=token)
        except HouseholdInvite.DoesNotExist as exc:
            raise Http404("Invitación no encontrada.") from exc
        if not invite.is_valid:
            messages.error(request, "La invitación no es válida o ha caducado.")
            return redirect("login")
        if not request.user.is_authenticated:
            return redirect(f"{reverse('signup')}?token={token}")
        try:
            accept_invite(request.user, token)
        except InviteError as exc:
            messages.error(request, str(exc))
            return redirect("households:onboarding")
        messages.success(request, f"Te has unido a {invite.household.name}.")
        return redirect("core:dashboard")
