from apps.chores.models import Chore
from apps.households.models import HouseholdMembership


class ChoreError(Exception):
    pass


def add_chore(household, title, cadence, assignee, today):
    if cadence not in Chore.Cadence.values:
        raise ChoreError("Elige cuándo hay que hacerlo.")
    if assignee and not HouseholdMembership.objects.filter(
        household=household, user=assignee
    ).exists():
        raise ChoreError("Esa persona no está en el hogar.")
    return Chore.objects.create(
        household=household,
        title=title,
        cadence=cadence,
        assignee=assignee,
        weekday=today.weekday() if cadence == Chore.Cadence.WEEKLY else None,
    )


def set_chore_done(chore, today, done):
    chore.done_on = today if done else None
    chore.save(update_fields=["done_on", "updated_at"])
    return chore
