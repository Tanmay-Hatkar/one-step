"""Generate the seed dish graph (api/data/dishes.json) with an LLM, once.

The output is committed and reviewed like code ("data as code", ADR-0002). Every
dish is validated against the controlled vocabulary by Pydantic, so the LLM can't
invent a technique or equipment the graph doesn't understand.

Usage:
    uv run python -m scripts.generate_dishes            # all families
    uv run python -m scripts.generate_dishes noodles    # one family (merged in)
"""

import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import get_args

from openai import OpenAI, OpenAIError
from pydantic import BaseModel

from app.config import settings
from app.models.dish import Dish
from app.models.vocab import DishFamily

logger = logging.getLogger("generate_dishes")

DISHES_PER_FAMILY = 19

# Dishes that must exist so the founding user's repertoire has real cousins,
# and so each family covers the well-known members of its cuisine "cousin set".
MUST_INCLUDE: dict[str, list[str]] = {
    "rice_with_protein": [
        "chicken biryani",
        "chicken pulao",
        "kabsa",
        "chicken mandi",
        "plov",
        "jollof rice with chicken",
        "arroz con pollo",
        "paella valenciana",
        "hainanese chicken rice",
        "takikomi gohan",
        "maqluba",
        "chicken fried rice",
        "nasi goreng",
        "jambalaya",
        "bibimbap",
        "kabuli palaw",
    ],
    "roast_and_grill": [
        "tandoori chicken",
        "chicken tikka",
        "peri-peri chicken",
        "jerk chicken",
        "yakitori",
        "gochujang chicken",
        "lemon herb roast chicken",
        "pollo asado",
        "chicken souvlaki",
        "chicken 65",
        "chicken satay",
        "shish tawook",
    ],
    "curry_and_stew": [
        "butter chicken",
        "chicken curry (home style)",
        "chicken korma",
        "rogan josh",
        "thai green curry",
        "chicken adobo",
        "chicken tagine",
        "doro wat",
        "japanese curry",
        "goulash",
        "coq au vin",
        "palak paneer",
    ],
    "noodles": [
        "hakka noodles",
        "pad thai",
        "chicken lo mein",
        "chow mein",
        "shoyu ramen",
        "spaghetti aglio e olio",
        "dan dan noodles",
        "japchae",
        "mee goreng",
        "khao soi",
    ],
    "flatbread_and_wraps": [
        "chicken kathi roll",
        "chicken shawarma wrap",
        "chicken quesadilla",
        "chicken tacos",
        "aloo paratha",
        "chicken frankie",
        "doner kebab",
        "gyro",
    ],
    "egg_dishes": [
        "egg bhurji",
        "masala omelette",
        "shakshuka",
        "egg curry",
        "frittata",
        "tamagoyaki",
        "huevos rancheros",
        "menemen",
        "egg fried rice",
    ],
    "lentils_and_beans": [
        "dal tadka",
        "chana masala",
        "rajma",
        "khichdi",
        "dal makhani",
        "feijoada",
        "chili con carne",
        "mujaddara",
        "misir wot",
    ],
    "soups": [
        "chicken soup",
        "pho ga",
        "tom yum",
        "tom kha gai",
        "harira",
        "chicken corn soup",
        "soto ayam",
        "avgolemono",
        "mulligatawny",
    ],
}

SYSTEM_PROMPT = """You are a culinary data expert building a structured dish catalog.
Describe authentic, well-known HOME-COOKING dishes accurately.

Rules:
- `family` must be the family you are asked for.
- `techniques`: the cooking methods that actually define the dish (2-6).
  Use rice_in_stock when rice absorbs seasoned stock; plain_rice when rice is cooked
  in water and served alongside; layered_dum only for sealed layered steaming.
- `equipment`: what a home cook needs (stovetop, oven, rice_cooker, ...). Minimal.
- `key_ingredients`: 5-12 defining ingredients as simple lowercase singular generic
  names ("chicken thigh", "chicken stock", "cumin", "basmati rice", "lemon").
  Use "chicken stock" for broth/bouillon/stock cube. Never include salt, water,
  cooking oil, or black pepper.
- `allergens`: every allergen present in a typical version.
- `id`: lowercase snake_case slug of the name.
- `summary`: one plain sentence on what it is.
- `time_minutes`: realistic total time for a home cook. `effort`: weeknight if
  under ~45 minutes of active work, else weekend.
- Cover many regions; avoid near-duplicates."""


class DishBatch(BaseModel):
    """Structured-output wrapper: one family's dishes."""

    dishes: list[Dish]


def generate_family(client: OpenAI, family: str) -> list[Dish]:
    """Ask the seed model for one family's dishes.

    Args:
        client: OpenAI client.
        family: A DishFamily value.

    Returns:
        Validated dishes for that family (may be empty on failure).
    """
    must = ", ".join(MUST_INCLUDE.get(family, []))
    prompt = (
        f"Family: {family}\n"
        f"Return {DISHES_PER_FAMILY} dishes. You MUST include: {must}. "
        "Fill the rest with other popular home dishes of this family from regions "
        "not yet covered."
    )
    try:
        response = client.responses.parse(
            model=settings.seed_model,
            instructions=SYSTEM_PROMPT,
            input=prompt,
            text_format=DishBatch,
            reasoning={"effort": "medium"},
        )
    except OpenAIError:
        logger.exception("Generation failed for family %s", family)
        return []
    batch = response.output_parsed
    if batch is None:
        logger.error("No parsed output for family %s", family)
        return []
    kept = [d for d in batch.dishes if d.family == family]
    logger.info(
        "%s: %d dishes (%d off-family dropped)", family, len(kept), len(batch.dishes) - len(kept)
    )
    return kept


def load_existing() -> list[Dish]:
    """Load the current catalog, if any, so single-family runs merge in."""
    if not settings.dishes_path.exists():
        return []
    raw = json.loads(settings.dishes_path.read_text())
    return [Dish.model_validate(d) for d in raw]


def save(dishes: list[Dish]) -> None:
    """Write the catalog sorted by family then id, deduplicated by id."""
    unique: dict[str, Dish] = {}
    for dish in dishes:
        unique.setdefault(dish.id, dish)
    ordered = sorted(unique.values(), key=lambda d: (d.family, d.id))
    settings.dishes_path.parent.mkdir(parents=True, exist_ok=True)
    settings.dishes_path.write_text(
        json.dumps([d.model_dump() for d in ordered], indent=2, ensure_ascii=False) + "\n"
    )
    logger.info("Wrote %d dishes to %s", len(ordered), settings.dishes_path)


def main() -> None:
    """Generate the requested families (default: all) and merge into the catalog."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    families = sys.argv[1:] or list(get_args(DishFamily))
    client = OpenAI(api_key=settings.openai_api_key, timeout=300)
    keep = [d for d in load_existing() if d.family not in families]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for dishes in pool.map(lambda f: generate_family(client, f), families):
            keep.extend(dishes)
    save(keep)


if __name__ == "__main__":
    main()
