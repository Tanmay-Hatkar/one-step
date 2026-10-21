"""Generate technique how-to cards (api/data/techniques.json) with an LLM, once.

Usage:
    uv run python -m scripts.generate_techniques
"""

import json
import logging
from typing import get_args

from openai import OpenAI, OpenAIError
from pydantic import BaseModel

from app.config import settings
from app.models.labels import technique_label
from app.models.technique import TechniqueGuide
from app.models.vocab import Technique

logger = logging.getLogger("generate_techniques")

SYSTEM_PROMPT = """You write tiny, practical how-to cards for home cooks who already
cook a few dishes and are trying ONE new technique.

For each technique:
- `title`: plain name, with a well-known alternative name in brackets if useful.
- `steps`: 3-5 short imperative steps, each under 20 words, in order. Concrete cues
  (sizzle, color, smell, time) rather than vague advice. No brand names.
- `tip`: the single most common mistake and how to avoid it, one sentence.
- `watch_query`: a search query that finds a good short video of the technique.
Be accurate and safe (hot oil, steam). No hype, no emoji."""


class GuideBatch(BaseModel):
    """Structured-output wrapper."""

    guides: list[TechniqueGuide]


def main() -> None:
    """Write one guide per technique in the vocabulary."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ids = list(get_args(Technique))
    prompt = "Techniques (id: meaning):\n" + "\n".join(f"{t}: {technique_label(t)}" for t in ids)
    client = OpenAI(api_key=settings.openai_api_key, timeout=300)
    try:
        response = client.responses.parse(
            model=settings.seed_model,
            instructions=SYSTEM_PROMPT,
            input=prompt,
            text_format=GuideBatch,
            reasoning={"effort": "low"},
        )
    except OpenAIError:
        logger.exception("Generation failed")
        return
    batch = response.output_parsed
    if batch is None:
        logger.error("No parsed output")
        return
    by_id = {g.id: g for g in batch.guides}
    missing = [t for t in ids if t not in by_id]
    settings.techniques_path.write_text(
        json.dumps([by_id[t].model_dump() for t in ids if t in by_id], indent=1) + "\n"
    )
    usage = response.usage
    logger.info(
        "Wrote %d guides (missing %s); tokens in=%d out=%d",
        len(by_id),
        missing,
        usage.input_tokens,
        usage.output_tokens,
    )


if __name__ == "__main__":
    main()
