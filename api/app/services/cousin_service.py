"""Find cousin dishes (code) and write each one up as a diff (LLM), in parallel."""

import asyncio
import logging

from pydantic import BaseModel, Field

from app.llm.client import LLMError
from app.llm.prompts import WRITE_DIFF_INSTRUCTIONS, build_diff_prompt
from app.models.api import (
    Cousin,
    Diet,
    DiffText,
    Have,
    MapCousin,
    MapResponse,
    TonightResponse,
)
from app.models.dish import Delta, Dish, UserDish, ingredients_of
from app.models.labels import technique_label
from app.services.diet import text_mentions_allergen
from app.services.graph_service import DietRule, GraphService, Owned
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
    swapped = {sw.need for sw in delta.swaps}
    to_buy = [i for i in delta.new_ingredients if i not in swapped]
    if to_buy:
        changes.append("Add " + ", ".join(to_buy[:5]) + ".")
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


def to_rule(diet: Diet) -> DietRule:
    """Convert the request's diet into the graph's hard rule."""
    return DietRule(vegetarian=diet.vegetarian, avoid=frozenset(diet.avoid))


def to_owned(have: Have | None) -> Owned:
    """Convert the request's "what I have" into the graph's form."""
    if have is None:
        return Owned()
    return Owned(equipment=frozenset(have.equipment), ingredients=frozenset(have.ingredients))


class CousinService:
    """Orchestrates graph search and diff writing."""

    def __init__(self, graph: GraphService, gateway: LLMGateway) -> None:
        """Args: graph service, LLM gateway."""
        self._graph = graph
        self._gateway = gateway

    async def find(
        self,
        repertoire: list[UserDish],
        limit: int,
        diet: Diet | None = None,
        have: Have | None = None,
    ) -> list[Cousin]:
        """Return cousins with written diffs, closest first.

        Args:
            repertoire: The user's dishes.
            limit: How many cousins.
            diet: Hard diet rule; also guards the written diffs.
            have: Extra equipment and pantry items.

        Returns:
            Cousins; a diff falls back to a template if the LLM fails for that one.
        """
        diet = diet or Diet()
        pairs = self._graph.find_cousins(repertoire, limit, to_rule(diet), to_owned(have))
        return await self._write_all(repertoire, pairs, diet)

    async def tonight(
        self,
        repertoire: list[UserDish],
        diet: Diet | None = None,
        max_minutes: int | None = None,
        skip: list[str] | None = None,
        have: Have | None = None,
    ) -> TonightResponse:
        """Pick tonight's familiar, one-step and stretch dishes, with diffs for the new ones.

        Args:
            repertoire: The user's dishes.
            diet: Hard diet rule.
            max_minutes: Time available; None means any.
            skip: Ids or names the user said 'not tonight' to.
            have: Extra equipment and pantry items.

        Returns:
            The three picks; any may be None.
        """
        diet = diet or Diet()
        picks = self._graph.pick_tonight(
            repertoire, to_rule(diet), max_minutes, frozenset(skip or []), owned=to_owned(have)
        )
        pairs = [p for p in (picks.one_step, picks.stretch) if p is not None]
        written = iter(await self._write_all(repertoire, pairs, diet))
        return TonightResponse(
            familiar=picks.familiar,
            one_step=next(written) if picks.one_step else None,
            stretch=next(written) if picks.stretch else None,
        )

    def map(
        self, repertoire: list[UserDish], diet: Diet | None = None, have: Have | None = None
    ) -> MapResponse:
        """The user's kitchen with its closest cousins, for drawing. No LLM calls.

        Args:
            repertoire: The user's dishes.
            diet: Hard diet rule.
            have: Extra equipment and pantry items.

        Returns:
            Kitchen, cousins (without diffs) and how many dishes are one step away.
        """
        pairs, one_step_count = self._graph.neighbourhood(
            repertoire, to_rule(diet or Diet()), to_owned(have)
        )
        return MapResponse(
            kitchen=repertoire,
            cousins=[MapCousin(dish=d, delta=x) for d, x in pairs],
            one_step_count=one_step_count,
            catalog_size=self._graph.catalog_size,
        )

    async def one(
        self,
        repertoire: list[UserDish],
        dish_id: str,
        diet: Diet | None = None,
        have: Have | None = None,
    ) -> Cousin | None:
        """Write up one dish relative to the user's kitchen (a tap on the map).

        Args:
            repertoire: The user's dishes.
            dish_id: Catalog id.
            diet: Hard diet rule.
            have: Extra equipment and pantry items.

        Returns:
            The cousin with its diff, or None if it can't be shown.
        """
        diet = diet or Diet()
        pair = self._graph.cousin_for(repertoire, dish_id, to_rule(diet), to_owned(have))
        if pair is None:
            return None
        return (await self._write_all(repertoire, [pair], diet))[0]

    async def _write_all(
        self, repertoire: list[UserDish], pairs: list[tuple[Dish, Delta]], diet: Diet
    ) -> list[Cousin]:
        """Write diffs for (dish, delta) pairs in parallel."""
        by_name = {d.name: d for d in repertoire}
        avoid = set(diet.avoid)
        diffs = await asyncio.gather(
            *(
                self.write_diff(by_name[delta.anchor_name], dish, delta, avoid)
                for dish, delta in pairs
            )
        )
        return [
            Cousin(dish=dish, delta=delta, diff=diff)
            for (dish, delta), diff in zip(pairs, diffs, strict=True)
        ]

    async def write_diff(
        self, anchor: UserDish, dish: Dish, delta: Delta, avoid: set[str] | None = None
    ) -> DiffText:
        """Write one diff with the LLM, falling back to a template on failure.

        Args:
            anchor: The user's dish.
            dish: The cousin.
            delta: Their computed difference.
            avoid: Allergens the user avoids; a diff that mentions one is replaced.

        Returns:
            The written diff.
        """
        prompt = build_diff_prompt(
            anchor_name=anchor.name,
            anchor_notes=anchor.notes,
            anchor_ingredients=ingredients_of(anchor),
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
        if avoid and text_mentions_allergen(" ".join([*body.changes, body.keep_line]), avoid):
            logger.warning("Diff for %s mentioned an avoided allergen; using template", dish.id)
            return fallback_diff(anchor, dish, delta)
        return DiffText(
            headline=headline_for(anchor, dish), changes=body.changes[:5], keep_line=body.keep_line
        )
