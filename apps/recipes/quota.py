from zoneinfo import ZoneInfo

from django.db.models import F
from django.utils import timezone

from apps.recipes.models import GeminiDailyUse

PACIFIC = ZoneInfo("America/Los_Angeles")

RECIPE_MODELS = (
    ("gemini-3.8-flash", "Gemini 3.8 Flash"),
    ("gemini-3.6-flash", "Gemini 3.6 Flash"),
    ("gemini-3.5-flash", "Gemini 3.5 Flash"),
    ("gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite"),
    ("gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite"),
    ("gemini-2.5-flash", "Gemini 2.5 Flash"),
    ("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite"),
)


def pacific_today():
    return timezone.now().astimezone(PACIFIC).date()


def allowed_model(name):
    return name in dict(RECIPE_MODELS)


def record_gemini_use(model_name, *, counted=True, limit=None, exhausted=False):
    day = pacific_today()
    row, _created = GeminiDailyUse.objects.get_or_create(model_name=model_name, day=day)
    if counted:
        GeminiDailyUse.objects.filter(pk=row.pk).update(count=F("count") + 1)
        row.refresh_from_db()
    if limit:
        row.daily_limit = limit
    if exhausted:
        row.exhausted = True
        if limit:
            row.count = max(row.count, limit)
    if limit or exhausted:
        row.save(update_fields=["daily_limit", "exhausted", "count"])
    return row


def quota_text(row):
    if row is None or row.count == 0 and not row.exhausted:
        return "0 hoy"
    if row.exhausted and row.daily_limit:
        return f"agotado, {row.daily_limit} de {row.daily_limit} hoy"
    if row.daily_limit:
        return f"{row.count} de {row.daily_limit} hoy"
    return f"{row.count} hoy"


def gemini_model_options(selected):
    uses = {
        row.model_name: row
        for row in GeminiDailyUse.objects.filter(day=pacific_today())
    }
    pairs = list(RECIPE_MODELS)
    known = dict(RECIPE_MODELS)
    if selected and selected not in known:
        pairs.append((selected, selected))
    options = []
    seen = set()
    for name, label in pairs:
        if name in seen:
            continue
        seen.add(name)
        options.append({"name": name, "label": label, "quota": quota_text(uses.get(name))})
    return options
