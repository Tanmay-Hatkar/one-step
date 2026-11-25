"""Paste a recipe from anywhere and get it back as a step from your own kitchen.

The model reads the pasted text once and breaks the dish into the same parts as a catalog
dish. Everything after that is the usual pipeline: code validates the parts, works out
allergens, compares the dish with the user's kitchen, and the model only writes the diff.
"""

import hashlib
import logging
import re

from pydantic import BaseModel, ValidationError

from app.llm.client import Image
from app.llm.prompts import READ_RECIPE_INSTRUCTIONS, READ_RECIPE_PHOTO_PROMPT
from app.models.api import Cousin, Diet, Have, PastedRecipe, PasteResponse
from app.models.dish import Dish, UserDish
from app.models.vocab import (
    DishFamily,
    Effort,
    Equipment,
    Flavor,
    Protein,
    Region,
    Starch,
    Technique,
)
from app.repositories.page_repository import PageRepository
from app.services.cousin_service import CousinService, to_owned, to_rule
from app.services.diet import VEGETARIAN_PROTEINS, ingredient_allergens, is_meat_ingredient
from app.services.graph_service import GraphService
from app.services.ingredients import STAPLES, normalize
from app.services.llm_gateway import LLMGateway
from app.services.recipe_page import recipe_text_from_html

logger = logging.getLogger(__name__)

URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
PASTED_ID_PREFIX = "pasted_"
FALLBACK_CUISINE = "Home"
MAX_INGREDIENT_LINES = 40
MAX_STEPS = 30
MAX_LINE_CHARS = 300
MAX_STEP_CHARS = 600
MIN_TIME_MINUTES, MAX_TIME_MINUTES = 5, 480


# Leading bytes of the picture formats accepted, and the type sent to the model for each.
PHOTO_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)
WEBP_RIFF, WEBP_TAG = b"RIFF", b"WEBP"


class PhotoRejected(ValueError):
    """The upload isn't a JPEG, PNG or WebP picture, or is too large."""


def photo_type(data: bytes) -> str | None:
    """The picture's real type from its first bytes (the upload's own label isn't trusted)."""
    for signature, media_type in PHOTO_SIGNATURES:
        if data.startswith(signature):
            return media_type
    if data[:4] == WEBP_RIFF and data[8:12] == WEBP_TAG:
        return "image/webp"
    return None


class NotARecipe(ValueError):
    """The pasted text (or page) didn't contain a recipe we could break into parts."""


class _ReadRecipe(BaseModel):
    """What the model returns. Deliberately loose: code checks and trims every field."""

    is_recipe: bool
    name: str
    cuisine: str
    region: Region
    summary: str
    time_minutes: int
    family: DishFamily
    protein: Protein
    starch: Starch
    techniques: list[Technique]
    equipment: list[Equipment]
    flavor: list[Flavor]
    key_ingredients: list[str]
    effort: Effort
    ingredients: list[str]
    steps: list[str]


def link_in(text: str, max_note_chars: int) -> str | None:
    """The link to open, if the paste is a link rather than a recipe.

    A share sheet often sends "Title https://…", so a little text around one link still
    counts as a link. A long text that happens to contain links is treated as the recipe.

    Args:
        text: What the user pasted.
        max_note_chars: Most non-link text allowed around the link.

    Returns:
        The URL, or None when the text itself should be read.
    """
    links = URL.findall(text)
    if len(links) != 1:
        return None
    rest = text.replace(links[0], "").strip()
    return links[0].rstrip(".,)") if len(rest) <= max_note_chars else None


def _unique(items: list[str], limit: int) -> list[str]:
    """Items in order without repeats, at most `limit`."""
    return list(dict.fromkeys(items))[:limit]


def _lines(items: list[str], limit: int, max_chars: int) -> list[str]:
    """Non-empty single-line strings, trimmed and capped."""
    cleaned = (" ".join(item.split())[:max_chars] for item in items)
    return [line for line in cleaned if line][:limit]


def _key_ingredients(items: list[str]) -> list[str]:
    """Lowercase names without staples (salt, oil, water) or duplicates."""
    seen = {normalize(s) for s in STAPLES}
    kept: list[str] = []
    for item in items:
        key = normalize(item)
        if key and key not in seen:
            seen.add(key)
            kept.append(item.strip().lower()[:60])
    return kept[:16]


def to_dish(read: _ReadRecipe) -> tuple[Dish, PastedRecipe]:
    """Turn the model's reading into a validated dish, with diet facts worked out in code.

    Allergens and vegetarian status come from keyword rules over both the short ingredient
    names and the full ingredient lines — never from the model.

    Args:
        read: The model's structured reading of the recipe.

    Returns:
        (the dish in catalog shape, the recipe as written).

    Raises:
        NotARecipe: If it isn't a recipe or too little could be read.
    """
    if not read.is_recipe:
        raise NotARecipe("No recipe in that text")
    lines = _lines(read.ingredients, MAX_INGREDIENT_LINES, MAX_LINE_CHARS)
    keys = _key_ingredients(read.key_ingredients)
    name = " ".join(read.name.split())[:60]
    everything = [*keys, *(line.lower() for line in lines)]
    allergens: set[str] = set()
    for item in everything:
        allergens |= ingredient_allergens(item)
    vegetarian = read.protein in VEGETARIAN_PROTEINS and not any(
        is_meat_ingredient(item) for item in everything
    )
    digest = hashlib.sha256("\x1f".join([name.lower(), *keys]).encode()).hexdigest()[:12]
    summary = " ".join(read.summary.split())[:200]
    try:
        dish = Dish(
            id=f"{PASTED_ID_PREFIX}{digest}",
            name=name,
            cuisine=" ".join(read.cuisine.split())[:40] or FALLBACK_CUISINE,
            region=read.region,
            summary=summary if len(summary) >= 10 else f"{name}, from a recipe you brought.",
            time_minutes=min(max(read.time_minutes, MIN_TIME_MINUTES), MAX_TIME_MINUTES),
            family=read.family,
            protein=read.protein,
            starch=read.starch,
            techniques=_unique(read.techniques, 8),
            equipment=_unique(read.equipment, 4) or ["stovetop"],
            flavor=_unique(read.flavor, 8),
            key_ingredients=keys,
            effort=read.effort,
            allergens=sorted(allergens),
            vegetarian=vegetarian,
        )
    except ValidationError as exc:
        logger.info("Pasted recipe was too thin to use: %d problems", exc.error_count())
        raise NotARecipe("Too little could be read from that recipe") from exc
    steps = _lines(read.steps, MAX_STEPS, MAX_STEP_CHARS)
    return dish, PastedRecipe(ingredients=lines, steps=steps, source_url=None)


def breaks_diet(dish: Dish, diet: Diet) -> list[str]:
    """Which of the user's diet rules this dish breaks (allergen ids, 'vegetarian')."""
    broken = sorted(set(diet.avoid) & set(dish.allergens))
    if diet.vegetarian and not dish.vegetarian:
        broken.append("vegetarian")
    return broken


class RecipeImportService:
    """Reads a pasted recipe and writes it up relative to the user's kitchen."""

    def __init__(
        self,
        gateway: LLMGateway,
        graph: GraphService,
        cousins: CousinService,
        pages: PageRepository,
        max_chars: int,
        link_note_max_chars: int,
        max_photo_bytes: int = 4_000_000,
    ) -> None:
        """Args: gateway, graph, cousin service (writes the diff), page reader, max_chars
        of recipe text sent to the model, link_note_max_chars (see `link_in`),
        max_photo_bytes (largest picture read)."""
        self._max_photo_bytes = max_photo_bytes
        self._gateway = gateway
        self._graph = graph
        self._cousins = cousins
        self._pages = pages
        self._max_chars = max_chars
        self._link_note_max_chars = link_note_max_chars

    async def paste(
        self,
        text: str,
        repertoire: list[UserDish],
        diet: Diet | None = None,
        have: Have | None = None,
    ) -> PasteResponse:
        """Rewrite a recipe from anywhere as a change to something the user already cooks.

        Args:
            text: A link to a recipe page, or the recipe's text.
            repertoire: The user's dishes (at least one).
            diet: The user's diet. A pasted dish that breaks it is still shown (they chose
                it) but flagged in `breaks_diet`; swaps always respect the diet.
            have: Extra equipment and pantry items.

        Returns:
            The dish, its delta and written diff, the recipe as written, and diet flags.

        Raises:
            NotARecipe: Nothing usable was found.
            PageUnreadable, LinkNotSupported: The link couldn't be read.
            DailyCapExceeded, LLMError: From the gateway (reading the recipe).
        """
        diet = diet or Diet()
        link = link_in(text, self._link_note_max_chars)
        if link:
            source = recipe_text_from_html(await self._pages.read(link), self._max_chars)
        else:
            source = text.strip()[: self._max_chars]
        if not source:
            raise NotARecipe("Nothing readable on that page")
        read = await self._gateway.run(
            task="read_recipe",
            instructions=READ_RECIPE_INSTRUCTIONS,
            prompt=source,
            schema=_ReadRecipe,
        )
        return await self._write_up(read, link, repertoire, diet, have)

    async def paste_photo(
        self,
        photo: bytes,
        repertoire: list[UserDish],
        diet: Diet | None = None,
        have: Have | None = None,
    ) -> PasteResponse:
        """Like `paste`, for a screenshot or photo of a recipe.

        Args:
            photo: The picture's bytes (JPEG, PNG or WebP).
            repertoire: The user's dishes (at least one).
            diet: The user's diet (flagged, not hidden; see `paste`).
            have: Extra equipment and pantry items.

        Returns:
            The same shape as `paste`, with no source link.

        Raises:
            PhotoRejected: Not a picture we read, or too large.
            NotARecipe: No recipe could be read from it.
            DailyCapExceeded, LLMError: From the gateway.
        """
        media_type = photo_type(photo)
        if media_type is None or len(photo) > self._max_photo_bytes:
            raise PhotoRejected("Not a JPEG, PNG or WebP picture within the size limit")
        read = await self._gateway.run(
            task="read_recipe_photo",
            instructions=READ_RECIPE_INSTRUCTIONS,
            prompt=READ_RECIPE_PHOTO_PROMPT,
            schema=_ReadRecipe,
            image=Image(photo, media_type),
        )
        return await self._write_up(read, None, repertoire, diet or Diet(), have)

    async def _write_up(
        self,
        read: _ReadRecipe,
        link: str | None,
        repertoire: list[UserDish],
        diet: Diet,
        have: Have | None,
    ) -> PasteResponse:
        """Validate what the model read, compare it with the kitchen, and write the diff."""
        dish, recipe = to_dish(read)
        broken = breaks_diet(dish, diet)
        delta = self._graph.delta_for(repertoire, dish, to_rule(diet), to_owned(have))
        anchor = next(d for d in repertoire if d.name == delta.anchor_name)
        # A dish that already breaks the diet is flagged instead; the allergen guard on
        # the written diff would otherwise reject every honest description of it.
        avoid = None if broken else set(diet.avoid)
        diff = await self._cousins.write_diff(anchor, dish, delta, avoid)
        return PasteResponse(
            cousin=Cousin(dish=dish, delta=delta, diff=diff),
            recipe=recipe.model_copy(update={"source_url": link}),
            breaks_diet=broken,
        )
