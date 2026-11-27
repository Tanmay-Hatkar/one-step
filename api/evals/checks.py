"""Deterministic checks used by the eval runner. Each returns (passed, detail)."""

import re

from app.models.api import DiffText, PasteResponse
from app.models.dish import Delta, Dish, UserDish
from app.services.diff_rules import restates_shared_step
from app.services.ingredients import normalize

MAX_BULLET_WORDS = 22
# A cook's own ingredient may appear when swapped out, skipped, kept, or used as a stand-in.
SUBSTITUTION_MARKERS = (
    "instead",
    "no ",
    "?",
    "swap",
    "replace",
    "skip",
    "keep",
    "stand-in",
    "use your",
    "or your",
)

Check = tuple[str, bool, str]


def _mentions(text: str, ingredient: str) -> bool:
    """True if `ingredient` (or its normalized form) appears as words in `text`."""
    lowered = text.lower()
    for form in {ingredient.lower(), normalize(ingredient)}:
        if re.search(rf"\b{re.escape(form)}", lowered):
            return True
    return False


def check_parsed_dish(dish: UserDish, expected: dict) -> list[Check]:
    """Compare one parsed dish to its expectations."""
    checks: list[Check] = []
    for field in ("family", "protein", "starch", "effort"):
        if field in expected:
            actual = getattr(dish, field)
            checks.append((field, actual == expected[field], f"{actual} vs {expected[field]}"))
    for technique in expected.get("techniques", []):
        checks.append(
            (f"technique:{technique}", technique in dish.techniques, str(dish.techniques))
        )
    for item in expected.get("equipment", []):
        checks.append((f"equipment:{item}", item in dish.equipment, str(dish.equipment)))
    names = {normalize(i) for i in dish.key_ingredients}
    for ingredient in expected.get("ingredients", []):
        checks.append(
            (f"ingredient:{ingredient}", normalize(ingredient) in names, str(dish.key_ingredients))
        )
    # Honesty: things they never said must not be recorded as said (guesses are fine).
    for ingredient in expected.get("not_said", []):
        checks.append(
            (
                f"not_said:{ingredient}",
                normalize(ingredient) not in names,
                str(dish.key_ingredients),
            )
        )
    if "has_guesses" in expected:
        has = bool(dish.assumed_ingredients)
        checks.append(
            ("has_guesses", has == expected["has_guesses"], str(dish.assumed_ingredients))
        )
    if "matched" in expected:
        checks.append(
            (
                "matched_dish_id",
                dish.matched_dish_id == expected["matched"],
                f"{dish.matched_dish_id} vs {expected['matched']}",
            )
        )
    return checks


def check_diff(diff: DiffText, anchor: UserDish, dish: Dish, delta: Delta) -> list[Check]:
    """Grounding and readability checks for one written diff."""
    checks: list[Check] = []
    bullets = diff.changes
    checks.append(("bullet_count", 2 <= len(bullets) <= 5, str(len(bullets))))
    longest = max(len(b.split()) for b in bullets)
    checks.append(("bullet_length", longest <= MAX_BULLET_WORDS, f"longest {longest} words"))
    text = " ".join([*bullets, diff.keep_line])
    checks.append(("no_raw_ids", "_" not in text, text[:80]))

    if delta.new_ingredients:
        covered = [i for i in delta.new_ingredients if _mentions(text, i)]
        ratio = len(covered) / len(delta.new_ingredients)
        checks.append(
            (
                "new_ingredient_coverage",
                ratio >= 0.6,
                f"{len(covered)}/{len(delta.new_ingredients)}",
            )
        )

    dish_keys = {normalize(i) for i in dish.key_ingredients}
    user_only = [i for i in anchor.key_ingredients if normalize(i) not in dish_keys]
    leaks = [
        i
        for i in user_only
        for b in bullets
        if _mentions(b, i) and not any(m in b.lower() for m in SUBSTITUTION_MARKERS)
    ]
    checks.append(("no_foreign_ingredients", not leaks, ", ".join(sorted(set(leaks))) or "ok"))

    restated = [b for b in bullets if restates_shared_step(b, delta)]
    checks.append(("only_what_changes", not restated, "; ".join(restated)[:80] or "ok"))
    return checks


def check_pasted(pasted: PasteResponse, expected: dict) -> list[Check]:
    """Checks for one pasted recipe: the parts the model read and what code made of them.

    Args:
        pasted: The service's result.
        expected: A PASTE_CASES entry.

    Returns:
        One check per expectation the case states.
    """
    dish, delta = pasted.cousin.dish, pasted.cousin.delta
    checks: list[Check] = []
    for part in ("family", "starch", "protein"):
        if part in expected:
            got = getattr(dish, part)
            checks.append((part, got == expected[part], got))
    for technique in expected.get("techniques", []):
        checks.append((f"has_{technique}", technique in dish.techniques, str(dish.techniques)))
    for technique in expected.get("not_techniques", []):
        checks.append((f"no_{technique}", technique not in dish.techniques, str(dish.techniques)))
    for item in expected.get("equipment", []):
        checks.append((f"needs_{item}", item in dish.equipment, str(dish.equipment)))
    for ingredient in expected.get("ingredients", []):
        found = any(_mentions(i, ingredient) for i in dish.key_ingredients)
        checks.append((f"ingredient:{ingredient}", found, str(dish.key_ingredients)))
    for allergen in expected.get("allergens", []):
        checks.append((f"allergen:{allergen}", allergen in dish.allergens, str(dish.allergens)))
    if "one_step" in expected:
        checks.append(("one_step", delta.is_one_step == expected["one_step"], str(delta.score)))
    checks.append(("has_steps", len(pasted.recipe.steps) >= 2, str(len(pasted.recipe.steps))))
    return checks
