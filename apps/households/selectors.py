from apps.households.models import HouseholdMembership


def get_user_membership(user):
    if not user or not user.is_authenticated:
        return None
    return (
        HouseholdMembership.objects.select_related("household", "user")
        .filter(user=user)
        .order_by("joined_at")
        .first()
    )


def get_user_household(user):
    membership = get_user_membership(user)
    return membership.household if membership else None


def list_members(household):
    return (
        HouseholdMembership.objects.select_related("user")
        .filter(household=household)
        .order_by("joined_at")
    )
