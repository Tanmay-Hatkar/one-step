"""Prompt text. Kept apart from code so prompt changes show up clearly in diffs and evals."""

from app.models.labels import technique_label

PARSE_REPERTOIRE_INSTRUCTIONS = """You turn a home cook's casual description of what
they usually cook into structured dishes. Capture THEIR version, not a textbook one.

Rules:
- One entry per distinct dish they describe. Ignore anything that isn't a dish.
- `name`: a short name for their dish in their terms ("Chicken leg with rice").
- `notes`: one line on how THEY make it, in their words.
- `key_ingredients`: simple lowercase singular generic names. If they say something
  vague like "Indian spices", list the spices such a cook would typically use
  (e.g. turmeric, chili powder, cumin, coriander, garam masala). Use
  "chicken stock" for broth / stock cube / bouillon. Never include salt, water,
  oil or black pepper.
- `techniques`: the methods they actually use. Rice cooked in broth or stock is
  rice_in_stock — including rice-cooker rice made with a stock or broth cube. Rice
  cooked only in water is plain_rice. Pick ONE of the two for a given rice, never both. If they
  marinate, include marinate.
- `equipment`: what they use; "electric cooker" / "rice cooker" → rice_cooker.
  Include stovetop and/or oven when implied (roasting implies oven unless they say pan).
- `matched_dish_id`: ONLY if their dish clearly IS one of the known dishes below
  (e.g. they say "biryani" → the biryani id). A plain "chicken with rice" is not a
  known dish → null.
- `effort`: weekend if they say it takes long or they make it on special days.

Known dishes (id: name):
{dish_index}"""

WRITE_DIFF_INSTRUCTIONS = """You write a short note telling a home cook how to make
a new dish as a set of CHANGES to a dish they already cook. They know their own dish
well, so only tell them what is different.

Rules:
- `changes`: 3-5 short imperative bullets, most important first, each one change,
  at most 18 words. Cover the new ingredients and new techniques you are given.
- Ingredients: name new-dish ingredients freely. Mention the cook's OWN ingredients
  only (a) as a stand-in for a missing one ("No kabsa spice? Mix your cumin,
  coriander and turmeric.") or (b) as something that stays. Never add the cook's
  own spices to a dish that doesn't use them. Never invent ingredients.
- Write techniques in plain words exactly as given; never use code-like names.
- `keep_line`: one sentence, at most 18 words, naming what stays the same.
- Plain, warm, no hype, no emoji."""


def build_diff_prompt(
    *,
    anchor_name: str,
    anchor_notes: str,
    anchor_ingredients: list[str],
    dish_name: str,
    dish_summary: str,
    dish_ingredients: list[str],
    dish_techniques: list[str],
    new_ingredients: list[str],
    new_techniques: list[str],
    dropped_techniques: list[str],
    shared_techniques: list[str],
) -> str:
    """Assemble the diff-writing prompt from pre-computed facts.

    Technique ids are converted to plain phrases here so the model never sees
    (or echoes) internal names like 'rice_in_stock'.

    Returns:
        The user-level prompt text.
    """

    def phrases(techniques: list[str]) -> str:
        return ", ".join(technique_label(t) for t in techniques) or "none"

    return (
        f"Their dish: {anchor_name}\n"
        f"How they make it: {anchor_notes or 'not specified'}\n"
        f"Their ingredients: {', '.join(anchor_ingredients)}\n\n"
        f"New dish: {dish_name} — {dish_summary}\n"
        f"New dish ingredients: {', '.join(dish_ingredients)}\n"
        f"New dish techniques: {phrases(dish_techniques)}\n\n"
        f"Ingredients they need that they don't have: {', '.join(new_ingredients) or 'none'}\n"
        f"New techniques: {phrases(new_techniques)}\n"
        f"Steps from their version they skip: {phrases(dropped_techniques)}\n"
        f"Techniques that stay the same: {phrases(shared_techniques)}"
    )
