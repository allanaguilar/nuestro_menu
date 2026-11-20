from datetime import timedelta

from django.db.models import Prefetch

from apps.chores.models import Chore, ChorePhoto


def chore_is_visible(chore, today):
    done = chore.done_on
    if chore.cadence in (Chore.Cadence.TODAY, Chore.Cadence.SOMEDAY):
        return done is None or done == today
    if chore.cadence == Chore.Cadence.DAILY:
        return True
    if done is None or done == today:
        return True
    if chore.weekday is None:
        return (today - done).days >= 7
    last_anchor = today - timedelta(days=(today.weekday() - chore.weekday) % 7)
    return done < last_anchor


def chore_meta(chore):
    bits = []
    if chore.cadence != Chore.Cadence.SOMEDAY:
        bits.append(chore.get_cadence_display())
    if chore.assignee_id:
        bits.append(chore.assignee.first_name or chore.assignee.username)
    return " · ".join(bits)


def open_chores(household, today):
    chores = list(
        Chore.objects.filter(household=household)
        .select_related("assignee")
        .prefetch_related(
            Prefetch(
                "photos",
                queryset=ChorePhoto.objects.only("id", "chore_id", "created_at").order_by("created_at"),
            )
        )
    )
    stale = [
        chore.pk
        for chore in chores
        if chore.cadence in (Chore.Cadence.TODAY, Chore.Cadence.SOMEDAY)
        and chore.done_on
        and chore.done_on < today
    ]
    if stale:
        Chore.objects.filter(pk__in=stale).delete()
        chores = [chore for chore in chores if chore.pk not in stale]
    visible = [chore for chore in chores if chore_is_visible(chore, today)]
    visible.sort(key=lambda chore: (chore.done_on == today, chore.created_at))
    for chore in visible:
        chore.meta = chore_meta(chore)
        chore.is_done = chore.done_on == today
        chore.photo_list = list(chore.photos.all())
    hoy = [chore for chore in visible if chore.cadence != Chore.Cadence.SOMEDAY]
    cuando = [chore for chore in visible if chore.cadence == Chore.Cadence.SOMEDAY]
    pending = sum(1 for chore in visible if not chore.is_done)
    return {"hoy": hoy, "cuando": cuando, "pending": pending}
