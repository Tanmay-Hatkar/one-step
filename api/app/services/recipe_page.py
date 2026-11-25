"""Pull the recipe out of a web page's HTML. Pure functions, no I/O.

Most recipe sites embed the recipe as schema.org JSON-LD (it's what search engines read),
which gives clean ingredients and steps. Pages without it fall back to their visible text,
starting near the word "ingredients" so a long blog intro doesn't crowd the recipe out.
"""

import json
import re
from contextlib import suppress
from html import unescape
from html.parser import HTMLParser
from typing import Any

JSON_LD = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)
TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")
SKIPPED_TAGS = frozenset({"script", "style", "noscript", "svg", "template", "iframe"})
BLOCK_TAGS = frozenset({"p", "li", "br", "div", "tr", "h1", "h2", "h3", "h4", "section"})
# How much text before the word "ingredients" to keep (usually the title and intro line).
LEAD_IN_CHARS = 400


def recipe_text_from_html(html: str, max_chars: int) -> str:
    """Return the recipe on a page as plain text, ready for the model to read.

    Args:
        html: The page source.
        max_chars: Longest text returned.

    Returns:
        The structured recipe if the page embeds one, else its visible text. May be empty.
    """
    recipe = _find_recipe(html)
    text = _recipe_to_text(recipe) if recipe else _visible_text(html)
    return text[:max_chars]


def _find_recipe(html: str) -> dict[str, Any] | None:
    """The first schema.org Recipe object in the page's JSON-LD blocks."""
    for block in JSON_LD.findall(html):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        found = _walk(data)
        if found:
            return found
    return None


def _walk(node: Any, depth: int = 0) -> dict[str, Any] | None:
    """Search nested JSON-LD (lists, @graph) for a Recipe."""
    if depth > 6:
        return None
    if isinstance(node, list):
        for item in node:
            found = _walk(item, depth + 1)
            if found:
                return found
    elif isinstance(node, dict):
        kind = node.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if "Recipe" in kinds:
            return node
        return _walk(node.get("@graph"), depth + 1)
    return None


def _clean(value: Any) -> str:
    """A JSON-LD string as plain text: no tags, entities decoded, single spaces."""
    if not isinstance(value, str):
        return ""
    return SPACE.sub(" ", unescape(TAG.sub(" ", value))).strip()


def _steps(node: Any, depth: int = 0) -> list[str]:
    """Flatten recipeInstructions: strings, HowToStep objects, and HowToSection groups."""
    if depth > 4:
        return []
    if isinstance(node, str):
        return [s for s in (_clean(part) for part in node.split("\n")) if s]
    if isinstance(node, list):
        return [step for item in node for step in _steps(item, depth + 1)]
    if isinstance(node, dict):
        if "itemListElement" in node:
            return _steps(node["itemListElement"], depth + 1)
        text = _clean(node.get("text") or node.get("name"))
        return [text] if text else []
    return []


def _recipe_to_text(recipe: dict[str, Any]) -> str:
    """Lay a JSON-LD Recipe out as title, time, ingredients and numbered steps."""
    lines = [f"Recipe: {_clean(recipe.get('name'))}"]
    for label, key in (("Cuisine", "recipeCuisine"), ("Total time", "totalTime")):
        value = recipe.get(key)
        value = (
            ", ".join(v for v in value if isinstance(v, str)) if isinstance(value, list) else value
        )
        if _clean(value):
            lines.append(f"{label}: {_clean(value)}")
    ingredients = recipe.get("recipeIngredient") or recipe.get("ingredients") or []
    if isinstance(ingredients, list):
        lines.append("Ingredients:")
        lines += [f"- {_clean(i)}" for i in ingredients if _clean(i)]
    steps = _steps(recipe.get("recipeInstructions"))
    if steps:
        lines.append("Steps:")
        lines += [f"{n}. {step}" for n, step in enumerate(steps, 1)]
    return "\n".join(lines)


class _TextCollector(HTMLParser):
    """Collects visible text, one line per block element."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIPPED_TAGS:
            self._skipping += 1
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIPPED_TAGS and self._skipping:
            self._skipping -= 1

    def handle_data(self, data: str) -> None:
        if not self._skipping:
            self.parts.append(data)


def _visible_text(html: str) -> str:
    """The page's readable text, starting just before the ingredients if they're found."""
    collector = _TextCollector()
    with suppress(AssertionError, ValueError):  # malformed markup: keep what was read
        collector.feed(html)
    lines = (SPACE.sub(" ", line).strip() for line in "".join(collector.parts).split("\n"))
    text = "\n".join(line for line in lines if line)
    start = text.lower().find("ingredients")
    return text[max(0, start - LEAD_IN_CHARS) :] if start > LEAD_IN_CHARS else text
