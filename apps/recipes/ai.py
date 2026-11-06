import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings

from apps.recipes.models import Recipe
from apps.recipes.services import guess_recipe_category

logger = logging.getLogger(__name__)

_TIMEOUT = 20


def _count(value):
    if not isinstance(value, int) or value < 1:
        return ""
    return value


class RecipeReadError(Exception):
    """El modelo no devolvió una receta usable."""


def interpret_recipe(text: str) -> dict:
    cleaned = (text or "").strip()
    if not cleaned or not settings.GEMINI_API_KEY:
        raise RecipeReadError("No se pudo leer la receta.")
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
    model = quote(settings.GEMINI_MODEL, safe="")
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
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
        logger.error("No se pudo leer la receta.")
        raise RecipeReadError("No se pudo leer la receta.") from exc
    try:
        body = json.loads(raw)
        content = body["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(content)
        name = " ".join(str(data.get("name") or "").split())
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RecipeReadError("No se pudo leer la receta.") from exc
    if not name:
        raise RecipeReadError("No se pudo leer la receta.")
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
