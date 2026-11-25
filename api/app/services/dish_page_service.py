"""Public dish pages: one catalog dish, its recipe, and the dishes one step from it."""

import logging

from app.config import Settings
from app.models.api import DishIndexEntry, DishPageResponse, RelatedDish
from app.repositories.dish_repository import DishRepository
from app.repositories.recipe_repository import RecipeRepository
from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)


class DishPageService:
    """Builds the data behind the public, indexable dish pages. No LLM involved."""

    def __init__(
        self,
        dishes: DishRepository,
        recipes: RecipeRepository,
        graph: GraphService,
        settings: Settings,
    ) -> None:
        """Create the service.

        Args:
            dishes: The catalog.
            recipes: Full recipes, where the catalog has one.
            graph: Finds dishes one step from another.
            settings: Display limits.
        """
        self._dishes = dishes
        self._recipes = recipes
        self._graph = graph
        self._settings = settings

    def page(self, dish_id: str) -> DishPageResponse | None:
        """One dish with its recipe and related dishes.

        Args:
            dish_id: Catalog id.

        Returns:
            The page data, or None if the dish is unknown.
        """
        dish = self._dishes.get(dish_id)
        if dish is None:
            return None
        cap = self._settings.related_max_new_ingredients
        related = [
            RelatedDish(
                id=other.id,
                name=other.name,
                cuisine=other.cuisine,
                summary=other.summary,
                new_techniques=list(delta.new_techniques),
                new_ingredients=delta.new_ingredients[:cap],
            )
            for other, delta in self._graph.related(dish_id)
        ]
        return DishPageResponse(dish=dish, recipe=self._recipes.get(dish_id), related=related)

    def index(self) -> list[DishIndexEntry]:
        """Every catalog dish, sorted by name, for the sitemap and directory.

        Returns:
            One entry per dish.
        """
        return sorted(
            (
                DishIndexEntry(id=d.id, name=d.name, cuisine=d.cuisine, region=d.region)
                for d in self._dishes.all()
            ),
            key=lambda e: e.name.lower(),
        )
