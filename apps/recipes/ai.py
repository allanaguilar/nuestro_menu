import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings

from apps.recipes.models import Recipe
from apps.recipes.quota import record_gemini_use
from apps.recipes.services import guess_recipe_category

logger = logging.getLogger(__name__)

_TIMEOUT = 20


def _error_payload(exc):
    try:
        raw = exc.read().decode("utf-8", "replace")
        data = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        return {}
    error = data.get("error") if isinstance(data, dict) else None
    return error if isinstance(error, dict) else {}


def _retry_phrase(error):
    for detail in error.get("details") or []:
        if not isinstance(detail, dict):
            continue
        delay = str(detail.get("retryDelay") or "")
        if not delay.endswith("s"):
            continue
        try:
            seconds = float(delay[:-1])
        except ValueError:
            continue
        hours = max(1, round(seconds / 3600))
        if hours == 1:
            return "Podrás volver a intentarlo en una hora."
        return f"Podrás volver a intentarlo en unas {hours} horas."
    return "Podrás volver a intentarlo mañana."


def _daily_limit(error):
    for detail in error.get("details") or []:
        if not isinstance(detail, dict):
            continue
        for violation in detail.get("violations") or []:
            if not isinstance(violation, dict):
                continue
            quota_id = str(violation.get("quotaId") or "")
            if "PerDay" not in quota_id or not violation.get("quotaValue"):
                continue
            try:
                return int(violation["quotaValue"])
            except (TypeError, ValueError):
                continue
    return None


def _note_model_use(model_name, exc):
    if isinstance(exc, HTTPError):
        error = _error_payload(exc)
        status = str(error.get("status") or "")
        limit = _daily_limit(error)
        if exc.code == 429 or status == "RESOURCE_EXHAUSTED":
            record_gemini_use(
                model_name,
                counted=False,
                limit=limit,
                exhausted=limit is not None,
            )
        else:
            record_gemini_use(model_name, counted=True)
        return error
    if isinstance(exc, TimeoutError):
        record_gemini_use(model_name, counted=True)
    return {}


def _quota_message(error):
    limit = ""
    for detail in error.get("details") or []:
        if not isinstance(detail, dict):
            continue
        for violation in detail.get("violations") or []:
            if isinstance(violation, dict) and violation.get("quotaValue"):
                limit = str(violation["quotaValue"])
                break
    if limit:
        lead = f"Se han agotado las {limit} lecturas gratuitas de hoy."
    else:
        lead = "Se han agotado las lecturas gratuitas de hoy."
    return f"{lead} {_retry_phrase(error)}"


def _connection_message(exc, error=None):
    if isinstance(exc, HTTPError):
        if error is None:
            error = _error_payload(exc)
        status = str(error.get("status") or "")
        if exc.code == 429 or status == "RESOURCE_EXHAUSTED":
            return _quota_message(error)
        if exc.code in (401, 403):
            return "La clave de la IA no es válida. Revisa la configuración."
        if exc.code == 404:
            return "El modelo de IA no está disponible."
        if exc.code >= 500:
            return "El servicio de IA no responde. Prueba otra vez dentro de un rato."
        return "La IA ha rechazado la lectura. Prueba otra vez dentro de un rato."
    if isinstance(exc, TimeoutError):
        return "La IA ha tardado demasiado en responder. Prueba otra vez."
    return "No hay conexión con la IA. Revisa la red y prueba otra vez."


def _count(value):
    if not isinstance(value, int) or value < 1:
        return ""
    return value


class RecipeReadError(Exception):
    """El modelo no devolvió una receta usable."""


def interpret_recipe(text: str, model: str | None = None) -> dict:
    cleaned = (text or "").strip()
    if not cleaned:
        raise RecipeReadError("Pega el texto de la receta antes de procesarla.")
    if not settings.GEMINI_API_KEY:
        raise RecipeReadError("Falta la clave de la IA.")
    categories = [value for value, _label in Recipe.Category.choices]
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "category": {"type": "string", "enum": categories},
            "servings": {
                "type": "integer",
                "nullable": True,
                "description": (
                    "Número de raciones o platos. "
                    "Si el texto no lo dice, dedúcelo de las cantidades de los ingredientes."
                ),
            },
            "prep_time_minutes": {"type": "integer", "nullable": True},
            "ingredients": {"type": "string"},
            "steps": {"type": "string"},
        },
        "required": [
            "name",
            "category",
            "servings",
            "prep_time_minutes",
            "ingredients",
            "steps",
        ],
    }
    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "Extrae una receta de cocina en español a partir del texto. "
                        "Usa solo los ingredientes y los pasos que están escritos. "
                        "Si el texto dice para cuántas personas o raciones, usa ese número. "
                        "Si no lo dice, deduce las raciones (platos) a partir de las cantidades de los ingredientes. "
                        "Si no hay cantidades suficientes para deducirlo, devuelve null. "
                        "Si falta el tiempo, devuelve null. "
                        "Ingredientes y pasos van en líneas separadas."
                    )
                }
            ]
        },
        "contents": [{"role": "user", "parts": [{"text": cleaned}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }
    model_name = (model or settings.GEMINI_MODEL or "").strip()
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model_name, safe='')}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "x-goog-api-key": settings.GEMINI_API_KEY,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=_TIMEOUT) as response:
            raw = response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        error = _note_model_use(model_name, exc)
        message = _connection_message(exc, error)
        logger.error("Lectura de receta fallida: %s", message)
        raise RecipeReadError(message) from exc
    else:
        record_gemini_use(model_name, counted=True)
    try:
        body = json.loads(raw)
        content = body["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(content)
        name = " ".join(str(data.get("name") or "").split())
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RecipeReadError(
            "La IA no ha devuelto una receta que se pueda usar. Prueba con otro texto."
        ) from exc
    if not name:
        raise RecipeReadError("La IA no ha encontrado el nombre de la receta. Prueba con otro texto.")
    category = str(data.get("category") or "")
    if category not in categories:
        category = guess_recipe_category(name)
    return {
        "name": name,
        "category": category,
        "servings": _count(data.get("servings")),
        "prep_time_minutes": _count(data.get("prep_time_minutes")),
        "ingredients": str(data.get("ingredients") or "").strip(),
        "steps": str(data.get("steps") or "").strip(),
    }
