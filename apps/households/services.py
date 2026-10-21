from django.db import transaction
from django.utils import timezone

from apps.households.models import Household, HouseholdInvite, HouseholdMembership


class InviteError(Exception):
    pass


@transaction.atomic
def create_household_for_user(user, name):
    household = Household.objects.create(name=name.strip())
    HouseholdMembership.objects.create(
        household=household,
        user=user,
        role=HouseholdMembership.Role.OWNER,
    )
    return household


@transaction.atomic
def accept_invite(user, token):
    try:
        invite = HouseholdInvite.objects.select_for_update().get(token=token)
    except HouseholdInvite.DoesNotExist as exc:
        raise InviteError("La invitación no es válida.") from exc
    if invite.is_used:
        raise InviteError("Esta invitación ya se ha utilizado.")
    if invite.is_expired:
        raise InviteError("Esta invitación ha caducado.")
    if HouseholdMembership.objects.filter(
        household=invite.household, user=user
    ).exists():
        raise InviteError("Ya formas parte de este hogar.")
    if HouseholdMembership.objects.filter(user=user).exists():
        raise InviteError("Ya perteneces a otro hogar.")
    HouseholdMembership.objects.create(
        household=invite.household,
        user=user,
        role=HouseholdMembership.Role.MEMBER,
    )
    invite.used_at = timezone.now()
    invite.used_by = user
    invite.save(update_fields=["used_at", "used_by"])
    return invite.household


def create_invite(household, created_by):
    return HouseholdInvite.issue(household=household, created_by=created_by)
