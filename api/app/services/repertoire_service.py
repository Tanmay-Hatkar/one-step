"""Turn a user's free-text description of their cooking into structured dishes."""

import logging

from pydantic import BaseModel

from app.llm.prompts import PARSE_REPERTOIRE_INSTRUCTIONS
from app.models.dish import UserDish
from app.repositories.dish_repository import DishRepository
from app.services.ingredients import STAPLES, normalize
from app.services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)


def _distinct(items: list[str], skip: set[str]) -> list[str]:
    """Ingredients in order, without staples, duplicates or anything in `skip` (normalized)."""
    seen = set(skip) | {normalize(s) for s in STAPLES}
    kept: list[str] = []
    for item in items:
        key = normalize(item)
        if key and key not in seen:
            seen.add(key)
            kept.append(item.strip().lower())
    return kept


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
        """Enforce in code what the prompt asks for — never trust it blindly.

        Drops a matched id the catalog doesn't know; removes staples (salt, oil, water)
        and duplicates; keeps a guess only if it isn't already something they said.
        Parsed dishes are always 'described' (their own words), whatever the model says.
        """
        said = _distinct(dish.key_ingredients, skip=set())
        if not said:  # they named nothing but staples; keep what the model gave
            said = dish.key_ingredients[:1]
        assumed = _distinct(dish.assumed_ingredients, skip={normalize(i) for i in said})
        update: dict[str, object] = {
            "source": "described",
            "key_ingredients": said,
            "assumed_ingredients": assumed,
        }
        if dish.matched_dish_id and self._dishes.get(dish.matched_dish_id) is None:
            logger.info("Dropping unknown matched_dish_id %r", dish.matched_dish_id)
            update["matched_dish_id"] = None
        return dish.model_copy(update=update)
