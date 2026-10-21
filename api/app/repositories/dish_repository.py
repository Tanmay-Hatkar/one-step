"""Read-only access to the dish catalog (api/data/dishes.json)."""

import difflib
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from app.models.dish import Dish
from app.services.diet import with_safe_diet_facts

logger = logging.getLogger(__name__)

# Words too common in dish names to identify one ("chicken curry" says little).
NAME_STOPWORDS = frozenset(
    {"with", "and", "the", "in", "of", "a", "style", "rice", "chicken", "soup", "stew", "curry"}
)
FUZZY_CUTOFF = 0.82  # "biriyani" ~ "biryani", "shakshouka" ~ "shakshuka"


def _words(text: str) -> list[str]:
    """Lowercase words of 3+ letters, with a trailing plural 's' dropped."""
    words = re.findall(r"[a-z]{3,}", text.lower())
    return [w[:-1] if w.endswith("s") and len(w) > 4 else w for w in words]


class DishCatalogError(RuntimeError):
    """The catalog file is missing or invalid."""


class DishRepository:
    """Loads the catalog once and serves it from memory."""

    def __init__(self, path: Path) -> None:
        """Load and validate the catalog.

        Args:
            path: Path to dishes.json.

        Raises:
            DishCatalogError: If the file can't be read or a dish fails validation.
        """
        try:
            raw = json.loads(path.read_text())
            generated = [Dish.model_validate(d) for d in raw]
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise DishCatalogError(f"Cannot load dish catalog at {path}: {exc}") from exc
        # Cross-check allergens and vegetarian status against ingredients (diet filter).
        self._dishes = [with_safe_diet_facts(d) for d in generated]
        corrected = sum(a != b for a, b in zip(generated, self._dishes, strict=True))
        if corrected:
            logger.info("Diet facts tightened for %d dishes", corrected)
        self._by_id = {d.id: d for d in self._dishes}
        self._name_words = {d.id: set(_words(d.name)) - NAME_STOPWORDS for d in self._dishes}
        counts = Counter(w for words in self._name_words.values() for w in words)
        # Rare words identify a dish best ("maqluba" vs "fried").
        self._idf = {w: math.log(len(self._dishes) / n) for w, n in counts.items()}
        logger.info("Loaded %d dishes", len(self._dishes))

    def all(self) -> list[Dish]:
        """Return every dish."""
        return list(self._dishes)

    def get(self, dish_id: str) -> Dish | None:
        """Return one dish by id, or None."""
        return self._by_id.get(dish_id)

    def index_lines(self, text: str | None = None, limit: int = 25) -> str:
        """Return 'id: name (cuisine)' lines, used to let the LLM match known dishes.

        Args:
            text: When given, only dishes whose distinctive name words appear in it
                (spelling-tolerant), best match first — so the prompt stays small
                however big the catalog grows.
            limit: Most dishes listed when filtering by text.

        Returns:
            One line per dish; may be empty if nothing in the text looks like a known dish.
        """
        dishes = self._dishes if text is None else self.likely_mentioned(text, limit)
        return "\n".join(f"{d.id}: {d.name} ({d.cuisine})" for d in dishes)

    def likely_mentioned(self, text: str, limit: int = 25) -> list[Dish]:
        """Catalog dishes the text probably names, best first (code-side shortlist)."""
        said = set(_words(text))
        vocabulary = list(self._idf)
        matched: dict[str, str] = {w: w for w in said if w in self._idf}
        for word in said - set(matched):
            if len(word) >= 5:
                close = difflib.get_close_matches(word, vocabulary, n=1, cutoff=FUZZY_CUTOFF)
                if close:
                    matched[close[0]] = word
        scored = []
        for dish in self._dishes:
            words = self._name_words[dish.id]
            hits = words & set(matched)
            if not hits:
                continue
            score = sum(self._idf[w] for w in hits) / max(1.0, sum(self._idf[w] for w in words))
            scored.append((score, dish))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [d for _, d in scored[:limit]]
