"""Read-only access to the dish catalog (api/data/dishes.json)."""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.models.dish import Dish

logger = logging.getLogger(__name__)


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
            self._dishes = [Dish.model_validate(d) for d in raw]
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise DishCatalogError(f"Cannot load dish catalog at {path}: {exc}") from exc
        self._by_id = {d.id: d for d in self._dishes}
        logger.info("Loaded %d dishes", len(self._dishes))

    def all(self) -> list[Dish]:
        """Return every dish."""
        return list(self._dishes)

    def get(self, dish_id: str) -> Dish | None:
        """Return one dish by id, or None."""
        return self._by_id.get(dish_id)

    def index_lines(self) -> str:
        """Return 'id: name (cuisine)' lines, used to let the LLM match known dishes."""
        return "\n".join(f"{d.id}: {d.name} ({d.cuisine})" for d in self._dishes)
