"""Turn a user's free-text description of their cooking into structured dishes."""

import logging

from pydantic import BaseModel

from app.llm.prompts import PARSE_REPERTOIRE_INSTRUCTIONS
from app.models.dish import UserDish
from app.repositories.dish_repository import DishRepository
from app.services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)


class NoDishesFound(ValueError):
    """The text didn't describe any dish."""


class _ParsedRepertoire(BaseModel):
    """Structured-output wrapper."""

    dishes: list[UserDish]


class RepertoireService:
    """Parses repertoire text with the LLM, then validates the result in code."""

    def __init__(self, gateway: LLMGateway, dishes: DishRepository, max_dishes: int) -> None:
        """Args: gateway, dish repository (for known-dish matching), max_dishes."""
        self._gateway = gateway
        self._dishes = dishes
        self._max_dishes = max_dishes

    async def parse(self, text: str) -> list[UserDish]:
        """Parse the user's description.

        Args:
            text: e.g. "Most nights chicken leg with Indian spices and rice…"

        Returns:
            The user's dishes (at most `max_dishes`).

        Raises:
            NoDishesFound: If nothing in the text is a dish.
            DailyCapExceeded, LLMError: From the gateway.
        """
        instructions = PARSE_REPERTOIRE_INSTRUCTIONS.format(dish_index=self._dishes.index_lines())
        parsed = await self._gateway.run(
            task="parse_repertoire",
            instructions=instructions,
            prompt=text.strip(),
            schema=_ParsedRepertoire,
        )
        dishes = [self._clean(d) for d in parsed.dishes[: self._max_dishes]]
        if not dishes:
            raise NoDishesFound("No dishes found in that description")
        return dishes

    def _clean(self, dish: UserDish) -> UserDish:
        """Drop a matched id the catalog doesn't know — never trust it blindly."""
        if dish.matched_dish_id and self._dishes.get(dish.matched_dish_id) is None:
            logger.info("Dropping unknown matched_dish_id %r", dish.matched_dish_id)
            return dish.model_copy(update={"matched_dish_id": None})
        return dish
