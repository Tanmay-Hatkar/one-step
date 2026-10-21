"""Generate a small illustrative photo per catalog dish (web/public/dishes/<id>.webp), once.

Incremental: dishes that already have a photo are skipped. Photos are AI-generated
illustrations and the web app labels them as such. Low quality at 1024px, then
downscaled to 512px WebP (~25 KB each) so the whole set stays small.

Usage:
    uv run python -m scripts.generate_photos            # every dish without a photo
    uv run python -m scripts.generate_photos kabsa      # just these ids
"""

import base64
import io
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI, OpenAIError
from PIL import Image

from app.config import REPO_ROOT, settings
from app.deps import get_dish_repository
from app.models.dish import Dish

logger = logging.getLogger("generate_photos")

PHOTOS_DIR = REPO_ROOT / "web" / "public" / "dishes"
MODEL = "gpt-image-1-mini"
QUALITY = "low"
SIZE_PX = 512
WEBP_QUALITY = 72
WORKERS = 3  # new accounts get ~20 images/min


def prompt_for(dish: Dish) -> str:
    """A consistent, appetizing, honest home-cooking shot."""
    return (
        f"Overhead food photograph of {dish.name} ({dish.cuisine}): {dish.summary} "
        "Home-cooked, served in a simple bowl or plate on a wooden kitchen table, soft "
        "natural window light, realistic portion. No text, no labels, no people, no hands."
    )


def generate(client: OpenAI, dish: Dish) -> int:
    """Make one photo. Returns image output tokens used (0 on failure)."""
    try:
        response = client.images.generate(
            model=MODEL,
            prompt=prompt_for(dish),
            size="1024x1024",
            quality=QUALITY,
            output_format="webp",
            n=1,
        )
    except OpenAIError:
        logger.exception("Photo failed for %s", dish.id)
        return 0
    raw = base64.b64decode(response.data[0].b64_json or "")
    image = Image.open(io.BytesIO(raw)).convert("RGB").resize((SIZE_PX, SIZE_PX), Image.LANCZOS)
    image.save(PHOTOS_DIR / f"{dish.id}.webp", "WEBP", quality=WEBP_QUALITY, method=6)
    return response.usage.output_tokens if response.usage else 0


def main(only: list[str]) -> None:
    """Fill in missing photos."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    dishes = get_dish_repository().all()
    todo = [
        d for d in dishes if (d.id in only if only else not (PHOTOS_DIR / f"{d.id}.webp").exists())
    ]
    logger.info("%d dishes, %d photos to make", len(dishes), len(todo))
    client = OpenAI(api_key=settings.openai_api_key, timeout=180, max_retries=8)
    with ThreadPoolExecutor(WORKERS) as pool:
        tokens = list(pool.map(lambda d: generate(client, d), todo))
    made = sum(1 for t in tokens if t)
    logger.info(
        "Made %d/%d photos; image output tokens=%d (%s, %s)",
        made,
        len(todo),
        sum(tokens),
        MODEL,
        QUALITY,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
