import re


def normalize_recipe_name(name: str) -> str:
    collapsed = re.sub(r"\s+", " ", (name or "").strip())
    return collapsed.casefold()
