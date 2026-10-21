"""Ingredient substitutions, loaded once from api/data/substitutions.json."""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.models.substitution import NEVER_SWAPPED, IngredientSwaps, Substitute

logger = logging.getLogger(__name__)


class SubstitutionRepository:
    """Normalized ingredient → stand-ins. Read-only; missing file means no swaps."""

    def __init__(self, path: Path) -> None:
        """Args: path to substitutions.json."""
        self._entries: dict[str, IngredientSwaps] = {}
        try:
            raw = json.loads(path.read_text())
            self._entries = {e["ingredient"]: IngredientSwaps.model_validate(e) for e in raw}
        except FileNotFoundError:
            logger.warning("No substitutions at %s; swaps disabled", path)
        except (json.JSONDecodeError, KeyError, ValidationError):
            logger.exception("Unreadable substitutions at %s; swaps disabled", path)
        logger.info("Loaded substitutions for %d ingredients", len(self._entries))

    def usable(self) -> dict[str, list[Substitute]]:
        """Stand-ins the graph may offer: never for a dish's protein or base starch."""
        return {
            name: entry.substitutes
            for name, entry in self._entries.items()
            if entry.role not in NEVER_SWAPPED and entry.substitutes
        }

    def role_of(self, ingredient: str) -> str | None:
        """The ingredient's role, if known (normalized name)."""
        entry = self._entries.get(ingredient)
        return entry.role if entry else None
