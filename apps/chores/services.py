from io import BytesIO

from PIL import Image, UnidentifiedImageError

from apps.chores.models import Chore, ChorePhoto
from apps.households.models import HouseholdMembership

MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_PHOTO_EDGE = 1280
MAX_PHOTOS = 12


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


def update_chore(chore, title, cadence, assignee, today):
    if cadence not in Chore.Cadence.values:
        raise ChoreError("Elige cuándo hay que hacerlo.")
    if assignee and not HouseholdMembership.objects.filter(
        household=chore.household, user=assignee
    ).exists():
        raise ChoreError("Esa persona no está en el hogar.")
    chore.title = title
    chore.cadence = cadence
    chore.assignee = assignee
    if cadence == Chore.Cadence.WEEKLY:
        if chore.weekday is None:
            chore.weekday = today.weekday()
    else:
        chore.weekday = None
    chore.save(update_fields=["title", "cadence", "assignee", "weekday", "updated_at"])
    return chore


def set_chore_done(chore, today, done):
    chore.done_on = today if done else None
    chore.save(update_fields=["done_on", "updated_at"])
    return chore


def save_chore_photo(chore, uploaded):
    if uploaded is None or not getattr(uploaded, "size", 0):
        raise ChoreError("Elige una foto.")
    if chore.photos.count() >= MAX_PHOTOS:
        raise ChoreError("Esta tarea ya tiene 12 fotos.")
    if uploaded.size > MAX_PHOTO_BYTES:
        raise ChoreError("La foto es demasiado grande.")
    try:
        content = _jpeg_bytes(uploaded.read())
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ChoreError("Esa foto no se puede usar.") from exc
    return ChorePhoto.objects.create(
        chore=chore,
        content=content,
        content_type="image/jpeg",
    )


def _jpeg_bytes(raw):
    with Image.open(BytesIO(raw)) as image:
        image.load()
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.thumbnail((MAX_PHOTO_EDGE, MAX_PHOTO_EDGE))
        output = BytesIO()
        image.save(output, format="JPEG", quality=82, optimize=True)
    return output.getvalue()
