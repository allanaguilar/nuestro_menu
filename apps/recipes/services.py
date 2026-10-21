from __future__ import annotations

import re
from dataclasses import dataclass, field

from apps.recipes.models import Recipe
from apps.recipes.utils import normalize_recipe_name

_BULLET_RE = re.compile(r"^\s*(?:[-*•]+|\d+[.)])\s*")
_CATEGORY_BY_ALIAS = {
    value.casefold(): value for value, _label in Recipe.Category.choices
}
_CATEGORY_BY_ALIAS.update(
    {label.casefold(): value for value, label in Recipe.Category.choices}
)
_CATEGORY_KEYWORDS = (
    (Recipe.Category.PASTA, ("pasta", "espagueti", "macarrón", "macarron", "boloñesa", "bolognesa", "fideo", "lasaña", "lasana")),
    (Recipe.Category.ARROZ, ("arroz",)),
    (Recipe.Category.LEGUMBRES, ("lenteja", "garbanzo", "alubia", "judía", "judia", "fabada")),
    (Recipe.Category.PESCADO, ("pescado", "salmón", "salmon", "merluza", "gallo", "atún", "atun", "bacalao")),
    (Recipe.Category.HUEVOS, ("huevo", "tortilla")),
    (Recipe.Category.CARNE, ("carne", "chuleta", "filete", "pollo", "ternera", "cerdo", "guisad")),
    (Recipe.Category.VERDURAS, ("crema", "verdura", "vegetal", "ensalada", "gazpacho", "calabac", "brócoli", "brocoli")),
)


@dataclass
class RecipeImportResult:
    created: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def guess_recipe_category(name: str) -> str:
    haystack = (name or "").casefold()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return category
    return Recipe.Category.OTROS


def parse_recipe_import_text(text: str) -> list[dict]:
    rows = []
    seen = set()
    for raw_line in (text or "").splitlines():
        line = _BULLET_RE.sub("", raw_line).strip()
        if not line or line.startswith("#"):
            continue
        parts = _split_import_line(line)
        name = parts[0] if parts else ""
        if not name:
            continue
        category = ""
        notes = ""
        if len(parts) > 1:
            category = parts[1]
        if len(parts) > 2:
            notes = " | ".join(parts[2:]).strip()
        key = normalize_recipe_name(name)
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append({"name": name, "category": category, "notes": notes})
    return rows


def _split_import_line(line: str) -> list[str]:
    if "|" in line:
        return [part.strip() for part in line.split("|")]
    if "\t" in line:
        return [part.strip() for part in line.split("\t")]
    parts = [part.strip() for part in line.split(";")]
    if len(parts) >= 2 and parts[1].casefold() in _CATEGORY_BY_ALIAS:
        return parts
    return [line.strip()]


def import_recipes_from_text(household, text: str) -> RecipeImportResult:
    result = RecipeImportResult()
    for row in parse_recipe_import_text(text):
        name = row["name"]
        notes = row["notes"]
        category_raw = row["category"].casefold()
        if category_raw:
            category = _CATEGORY_BY_ALIAS.get(category_raw)
            if category is None:
                result.errors.append(f"«{name}»: categoría desconocida ({row['category']}).")
                continue
        else:
            category = guess_recipe_category(name)
        normalized = normalize_recipe_name(name)
        if Recipe.objects.filter(household=household, normalized_name=normalized).exists():
            result.skipped.append(name)
            continue
        recipe = Recipe.objects.create(
            household=household,
            name=name,
            category=category,
            notes=notes,
        )
        result.created.append(recipe)
    return result


def archive_recipe(recipe: Recipe):
    recipe.is_active = False
    recipe.save(update_fields=["is_active", "updated_at"])
    return recipe


def reactivate_recipe(recipe: Recipe):
    recipe.is_active = True
    recipe.save(update_fields=["is_active", "updated_at"])
    return recipe
