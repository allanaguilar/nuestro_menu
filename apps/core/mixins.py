from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect

from apps.households.selectors import get_user_household, get_user_membership


class HouseholdRequiredMixin(LoginRequiredMixin):
    """Exige sesión y una membresía de hogar activa."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        membership = get_user_membership(request.user)
        if membership is None:
            return redirect("households:onboarding")
        request.membership = membership
        request.household = membership.household
        return super().dispatch(request, *args, **kwargs)


def require_household(user):
    household = get_user_household(user)
    if household is None:
        raise PermissionDenied("Necesitas pertenecer a un hogar.")
    return household


def get_owned_or_404(queryset, **kwargs):
    try:
        return queryset.get(**kwargs)
    except queryset.model.DoesNotExist as exc:
        raise Http404("No encontrado.") from exc
