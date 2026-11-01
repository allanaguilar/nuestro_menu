from apps.households.selectors import get_user_membership
from apps.core.week import monday_of
from apps.preferences.models import MenuPreference
from django.utils import timezone


def household(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {
            "current_household": None,
            "current_week_start": monday_of(timezone.localdate()),
            "show_baby_menu": False,
        }
    membership = get_user_membership(request.user)
    show_baby = MenuPreference.objects.filter(
        user=request.user, show_baby_menu=True
    ).exists()
    return {
        "current_household": membership.household if membership else None,
        "current_membership": membership,
        "current_week_start": monday_of(timezone.localdate()),
        "show_baby_menu": show_baby,
    }
