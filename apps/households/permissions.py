from rest_framework.permissions import BasePermission

from apps.households.selectors import get_user_household, get_user_membership


class HasHousehold(BasePermission):
    message = "Necesitas pertenecer a un hogar."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and get_user_household(request.user))


def household_from_request(request):
    household = get_user_household(request.user)
    if household is None:
        return None
    request.household = household
    request.membership = get_user_membership(request.user)
    return household
