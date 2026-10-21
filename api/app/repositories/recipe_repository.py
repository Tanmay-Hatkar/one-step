"""Full recipes for catalog dishes, loaded once from api/data/recipes.json."""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.models.recipe import Recipe

logger = logging.getLogger(__name__)


class RecipeRepository:
    """Dish id → recipe. Read-only; a missing file means no recipes."""

    def __init__(self, path: Path) -> None:
        """Args: path to recipes.json."""
        self._recipes: dict[str, Recipe] = {}
        try:
            raw = json.loads(path.read_text())
            self._recipes = {k: Recipe.model_validate(v) for k, v in raw.items()}
        except FileNotFoundError:
            logger.warning("No recipes at %s", path)
        except (json.JSONDecodeError, ValidationError):
            logger.exception("Unreadable recipes at %s", path)
        logger.info("Loaded %d recipes", len(self._recipes))

    def get(self, dish_id: str) -> Recipe | None:
        """The recipe for a dish, if there is one."""
        return self._recipes.get(dish_id)

    def ids(self) -> list[str]:
        """Every dish id that has a recipe, sorted."""
        return sorted(self._recipes)
