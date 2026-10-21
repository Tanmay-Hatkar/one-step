"""Import savory mains from the Wikibooks Cookbook (CC BY-SA 4.0) into the dish graph.

Input is a JSON list of pre-cleaned candidates (title, url, revid, ingredients, steps),
made from a Wikibooks dump. The LLM only maps each recipe onto the closed vocabulary
(family, techniques, …) and says whether it belongs; the recipe text itself is kept as
written, with attribution, in api/data/recipes.json. Code dedupes by name, merges with
the existing catalog, and validates everything with Pydantic.

Usage:
    uv run python -m scripts.import_wikibooks /path/to/candidates.json
"""

import json
import logging
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.models.dish import Dish
from app.models.recipe import Recipe
from app.services.ingredients import normalize

logger = logging.getLogger("import_wikibooks")

BATCH_SIZE = 5
WORKERS = 8
MAX_STEPS_SHOWN = 8  # enough to judge techniques; full steps are kept from the source

SYSTEM_PROMPT = """You map real recipes onto a fixed dish vocabulary for a cooking app
that suggests everyday HOME dishes connected by cooking method.

For each recipe decide `keep`:
- keep = true only for a savory main dish or hearty soup/stew that a home cook would
  make for dinner, and that clearly fits one of the families. Regional and
  traditional dishes are very welcome.
- keep = false for: sides, snacks, appetizers, salads, sauces, desserts, drinks,
  breads, joke/novelty recipes, near-identical variants ("Meatloaf IV"), and recipes
  that are too vague to cook.
If keep is true, fill `dish`:
- `name`: the dish's common name, cleaned ("Chicken Biryani", "Lomo Saltado").
  No numbering, no "my", no "easy".
- `techniques`: the methods that define it (2-6), from the allowed values.
- `equipment`: minimal (stovetop, oven, …). `key_ingredients`: 5-12 defining ones as
  simple lowercase singular generic names; "chicken stock" for broth/bouillon. Never
  salt, water, cooking oil or black pepper.
- `allergens`: every allergen present. `vegetarian`: true only with no meat or fish.
- `time_minutes` and `effort` (weeknight if under ~45 min active work) from the steps.
- `summary`: one plain sentence. `cuisine`: the country or people it's from.
- `id`: lowercase snake_case of the name."""


class Verdict(BaseModel):
    """One recipe's decision."""

    source_title: str = Field(..., description="Copied exactly from the input")
    keep: bool
    reason: str = Field(..., max_length=120)
    dish: Dish | None = None


class VerdictBatch(BaseModel):
    """Structured-output wrapper."""

    verdicts: list[Verdict]


def slug(name: str) -> str:
    """'Lomo Saltado' → 'lomo_saltado'; 'Fricassée' → 'fricassee'."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")[:60]


def name_key(name: str) -> str:
    """Comparison key for deduping dish names ('Chicken Biryani' == 'chicken biryani')."""
    return normalize(re.sub(r"\(.*?\)", "", name).strip())


def describe(candidate: dict) -> str:
    """The text the model sees for one recipe."""
    steps = candidate["steps"][:MAX_STEPS_SHOWN]
    return (
        f"### {candidate['title']}\n"
        f"Ingredients:\n" + "\n".join(f"- {i}" for i in candidate["ingredients"]) + "\n"
        "Steps:\n" + "\n".join(f"{n}. {s}" for n, s in enumerate(steps, 1))
    )


def judge(client: OpenAI, batch: list[dict]) -> tuple[list[Verdict], int, int]:
    """Ask the model about a few recipes. Returns (verdicts, input tokens, output tokens)."""
    try:
        response = client.responses.parse(
            model=settings.llm_model,
            instructions=SYSTEM_PROMPT,
            input="\n\n".join(describe(c) for c in batch),
            text_format=VerdictBatch,
            reasoning={"effort": "low"},
        )
    except (OpenAIError, ValidationError):
        logger.exception("Batch failed: %s", [c["title"] for c in batch])
        return [], 0, 0
    usage = response.usage
    parsed = response.output_parsed
    return (parsed.verdicts if parsed else []), usage.input_tokens, usage.output_tokens


def recipe_for(candidate: dict) -> Recipe:
    """The source recipe as written, with attribution."""
    return Recipe(
        title=candidate["title"],
        source_url=candidate["url"],
        revision=candidate["revid"],
        ingredients=candidate["ingredients"],
        steps=candidate["steps"],
    )


def main(candidates_path: Path) -> None:
    """Judge every candidate, then merge kept dishes and their recipes into the catalog."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    candidates = json.loads(candidates_path.read_text())
    by_title = {c["title"]: c for c in candidates}
    client = OpenAI(api_key=settings.openai_api_key, timeout=300)
    batches = [candidates[i : i + BATCH_SIZE] for i in range(0, len(candidates), BATCH_SIZE)]

    verdicts: list[Verdict] = []
    tokens_in = tokens_out = 0
    with ThreadPoolExecutor(WORKERS) as pool:
        for found, t_in, t_out in pool.map(lambda b: judge(client, b), batches):
            verdicts += found
            tokens_in += t_in
            tokens_out += t_out

    catalog = [Dish.model_validate(d) for d in json.loads(settings.dishes_path.read_text())]
    by_name = {name_key(d.name): d for d in catalog}
    ids = {d.id for d in catalog}
    recipes: dict[str, dict] = {}
    if settings.recipes_path.exists():
        recipes = json.loads(settings.recipes_path.read_text())

    added = attached = 0
    for verdict in verdicts:
        candidate = by_title.get(verdict.source_title)
        if not (verdict.keep and verdict.dish and candidate):
            continue
        dish = verdict.dish
        existing = by_name.get(name_key(dish.name))
        if existing:  # a dish we already have: give it this recipe if it has none
            if existing.id not in recipes:
                recipes[existing.id] = recipe_for(candidate).model_dump()
                attached += 1
            continue
        dish_id = slug(dish.name)
        if not dish_id or dish_id in ids:
            continue
        dish = dish.model_copy(update={"id": dish_id})
        catalog.append(dish)
        ids.add(dish_id)
        by_name[name_key(dish.name)] = dish
        recipes[dish_id] = recipe_for(candidate).model_dump()
        added += 1

    catalog.sort(key=lambda d: (d.family, d.id))
    settings.dishes_path.write_text(
        json.dumps([d.model_dump() for d in catalog], indent=2, ensure_ascii=False) + "\n"
    )
    settings.recipes_path.write_text(
        json.dumps(dict(sorted(recipes.items())), indent=1, ensure_ascii=False) + "\n"
    )
    kept = sum(1 for v in verdicts if v.keep)
    logger.info(
        "Judged %d/%d; kept %d; added %d new dishes, attached %d recipes to existing; "
        "catalog now %d; tokens in=%d out=%d (%s)",
        len(verdicts),
        len(candidates),
        kept,
        added,
        attached,
        len(catalog),
        tokens_in,
        tokens_out,
        settings.llm_model,
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
