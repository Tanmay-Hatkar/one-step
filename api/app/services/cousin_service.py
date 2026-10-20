"""Find cousin dishes (code) and write each one up as a diff (LLM), in parallel."""

import asyncio
import logging

from pydantic import BaseModel, Field

from app.llm.client import LLMError
from app.llm.prompts import WRITE_DIFF_INSTRUCTIONS, build_diff_prompt
from app.models.api import Cousin, DiffText
from app.models.dish import Delta, Dish, UserDish
from app.models.labels import technique_label
from app.services.graph_service import GraphService
from app.services.llm_gateway import DailyCapExceeded, LLMGateway

logger = logging.getLogger(__name__)


class _DiffBody(BaseModel):
    """What the LLM writes. The headline is built in code so it's always exact."""

    changes: list[str] = Field(..., min_length=1, max_length=6)
    keep_line: str = Field(..., max_length=160)


def headline_for(anchor: UserDish, dish: Dish) -> str:
    """'Kabsa: your chicken leg with rice, but…' — deterministic, never from the LLM."""
    return f"{dish.name}: your {anchor.name.lower()}, but…"


def fallback_diff(anchor: UserDish, dish: Dish, delta: Delta) -> DiffText:
    """Write a plain diff without the LLM — used when the model is down or capped.

    Args:
        anchor: The user's dish.
        dish: The cousin.
        delta: The computed difference.

    Returns:
        A serviceable, factual DiffText.
    """
    changes: list[str] = []
    if delta.new_ingredients:
        changes.append("Add " + ", ".join(delta.new_ingredients[:5]) + ".")
    for technique in delta.new_techniques[:2]:
        phrase = technique_label(technique)
        changes.append("Try " + phrase + ".")
    if delta.dropped_techniques:
        skipped = " and ".join(technique_label(t) for t in delta.dropped_techniques[:2])
        changes.append(f"Skip {skipped}.")
    if not changes:
        changes.append("Shift the seasoning toward " + dish.cuisine + " flavors.")
    return DiffText(
        headline=headline_for(anchor, dish),
        changes=changes[:5],
        keep_line="Everything else is how you already do it.",
    )


class CousinService:
    """Orchestrates graph search and diff writing."""

    def __init__(self, graph: GraphService, gateway: LLMGateway) -> None:
        """Args: graph service, LLM gateway."""
        self._graph = graph
        self._gateway = gateway

    async def find(self, repertoire: list[UserDish], limit: int) -> list[Cousin]:
        """Return cousins with written diffs, closest first.

        Args:
            repertoire: The user's dishes.
            limit: How many cousins.

        Returns:
            Cousins; a diff falls back to a template if the LLM fails for that one.
        """
        pairs = self._graph.find_cousins(repertoire, limit)
        by_name = {d.name: d for d in repertoire}
        diffs = await asyncio.gather(
            *(self.write_diff(by_name[delta.anchor_name], dish, delta) for dish, delta in pairs)
        )
        return [
            Cousin(dish=dish, delta=delta, diff=diff)
            for (dish, delta), diff in zip(pairs, diffs, strict=True)
        ]

    async def write_diff(self, anchor: UserDish, dish: Dish, delta: Delta) -> DiffText:
        """Write one diff with the LLM, falling back to a template on failure.

        Args:
            anchor: The user's dish.
            dish: The cousin.
            delta: Their computed difference.

        Returns:
            The written diff.
        """
        prompt = build_diff_prompt(
            anchor_name=anchor.name,
            anchor_notes=anchor.notes,
            anchor_ingredients=anchor.key_ingredients,
            dish_name=dish.name,
            dish_summary=dish.summary,
            dish_ingredients=dish.key_ingredients,
            dish_techniques=list(dish.techniques),
            new_ingredients=delta.new_ingredients,
            new_techniques=list(delta.new_techniques),
            dropped_techniques=list(delta.dropped_techniques),
            shared_techniques=list(delta.shared_techniques),
        )
        try:
            body = await self._gateway.run(
                task="write_diff",
                instructions=WRITE_DIFF_INSTRUCTIONS,
                prompt=prompt,
                schema=_DiffBody,
            )
        except (LLMError, DailyCapExceeded):
            logger.warning("Diff for %s fell back to template", dish.id)
            return fallback_diff(anchor, dish, delta)
        return DiffText(
            headline=headline_for(anchor, dish), changes=body.changes[:5], keep_line=body.keep_line
        )
