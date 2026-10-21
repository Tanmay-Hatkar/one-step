"""Generate ingredient substitutions (api/data/substitutions.json) with an LLM, once.

Incremental: only ingredients not already in the file are sent, so growing the
catalog later costs only the new ingredients. The output is committed and reviewed
like code. Roles are a closed vocabulary; code (not the model) decides when a swap
is offered and filters every swap against the user's diet.

Usage:
    uv run python -m scripts.generate_substitutions
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI, OpenAIError
from pydantic import BaseModel

from app.config import settings
from app.deps import get_dish_repository
from app.models.substitution import IngredientSwaps
from app.services.ingredients import STAPLES, normalize

logger = logging.getLogger("generate_substitutions")

BATCH_SIZE = 25
WORKERS = 6

SYSTEM_PROMPT = """You are a practical home-cooking expert. For each ingredient, say
what ROLE it plays in a dish and list up to 4 substitutes a home cook is likely to
already have, best first.

Rules:
- A substitute must play the same role (acid for acid, fat for fat, warm spice for
  warm spice) and work in savory home cooking.
- Prefer everyday pantry items over specialty ones.
- `note`: how to use it, under 10 words ("half as much", "add at the end"). May be empty.
- Names: lowercase, singular, generic ("lemon", "white vinegar", "chili powder").
- Role `protein` (the main meat/fish/tofu/egg/legume) and `starch` (rice, noodles,
  pasta, bread, potato as the base): return NO substitutes — changing those makes a
  different dish.
- If there is no reasonable substitute, return an empty list. Never list the
  ingredient itself.
- Return exactly one entry per ingredient given, with `ingredient` copied exactly."""


class SwapBatch(BaseModel):
    """Structured-output wrapper."""

    items: list[IngredientSwaps]


def wanted_ingredients() -> list[str]:
    """Every normalized catalog ingredient, minus staples."""
    names = {normalize(i) for d in get_dish_repository().all() for i in d.key_ingredients}
    return sorted(names - {normalize(s) for s in STAPLES})


def load_existing() -> dict[str, IngredientSwaps]:
    """Current file, keyed by normalized ingredient."""
    if not settings.substitutions_path.exists():
        return {}
    raw = json.loads(settings.substitutions_path.read_text())
    return {item["ingredient"]: IngredientSwaps.model_validate(item) for item in raw}


def generate_batch(client: OpenAI, names: list[str]) -> tuple[list[IngredientSwaps], int, int]:
    """Ask the seed model about one batch. Returns (items, input tokens, output tokens)."""
    try:
        response = client.responses.parse(
            model=settings.seed_model,
            instructions=SYSTEM_PROMPT,
            input="Ingredients:\n" + "\n".join(names),
            text_format=SwapBatch,
            reasoning={"effort": "low"},
        )
    except OpenAIError:
        logger.exception("Batch failed: %s…", names[:3])
        return [], 0, 0
    usage = response.usage
    batch = response.output_parsed
    if batch is None:
        return [], usage.input_tokens, usage.output_tokens
    asked = set(names)
    items = []
    for item in batch.items:
        key = normalize(item.ingredient)
        if key not in asked:
            continue
        subs = [s for s in item.substitutes if normalize(s.name) != key]
        items.append(item.model_copy(update={"ingredient": key, "substitutes": subs}))
    return items, usage.input_tokens, usage.output_tokens


def save(entries: dict[str, IngredientSwaps]) -> None:
    """Write sorted by ingredient."""
    ordered = [entries[k].model_dump() for k in sorted(entries)]
    settings.substitutions_path.write_text(json.dumps(ordered, indent=1, ensure_ascii=False) + "\n")


def main() -> None:
    """Fill in substitutions for ingredients that don't have them yet."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    existing = load_existing()
    todo = [n for n in wanted_ingredients() if n not in existing]
    logger.info("%d ingredients, %d new", len(existing) + len(todo), len(todo))
    if not todo:
        return
    client = OpenAI(api_key=settings.openai_api_key, timeout=180)
    batches = [todo[i : i + BATCH_SIZE] for i in range(0, len(todo), BATCH_SIZE)]
    tokens_in = tokens_out = 0
    with ThreadPoolExecutor(WORKERS) as pool:
        for items, t_in, t_out in pool.map(lambda b: generate_batch(client, b), batches):
            tokens_in += t_in
            tokens_out += t_out
            for item in items:
                existing[item.ingredient] = item
    save(existing)
    missing = [n for n in todo if n not in existing]
    logger.info(
        "Saved %d entries; %d still missing; tokens in=%d out=%d (%s)",
        len(existing),
        len(missing),
        tokens_in,
        tokens_out,
        settings.seed_model,
    )


if __name__ == "__main__":
    main()
