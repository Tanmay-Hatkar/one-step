"""Rules for a written diff that must hold whatever the model writes.

The promise is "only what's different". A bullet that just re-tells a step the cook
already does (e.g. "Boil the lentils, then simmer" for someone who makes dal) breaks it,
so code drops those bullets instead of trusting the prompt.
"""

import re

from app.models.dish import Delta
from app.services.ingredients import normalize

# Words that show a technique is being talked about. Kept narrow on purpose: a cue must
# not also be an ingredient word ("paste" would match "tomato paste").
TECHNIQUE_CUES: dict[str, tuple[str, ...]] = {
    "marinate": ("marinat",),
    "spice_paste": ("spice paste",),
    "temper_spices": ("bloom", "temper", "tadka"),
    "sear": ("sear",),
    "pan_fry": ("pan-fr", "pan fr", "shallow-fr", "shallow fr"),
    "stir_fry": ("stir-fr", "stir fr"),
    "deep_fry": ("deep-fr", "deep fr"),
    "roast": ("roast",),
    "grill": ("grill", "char"),
    "braise": ("brais",),
    "simmer": ("simmer",),
    "steam": ("steam",),
    "boil": ("boil",),
    "bake": ("bake", "baking"),
    "rice_in_stock": ("rice in stock", "rice in the stock", "rice in broth"),
    "plain_rice": ("plain rice",),
    "layered_dum": ("layer", "dum"),
    "scramble": ("scrambl",),
    "knead_dough": ("knead",),
    "wrap_and_roll": ("wrap", "roll"),
    "poach": ("poach",),
    "blend_puree": ("blend", "pur"),
}

# Words that mean a shared step is being changed, not just repeated.
CHANGE_MARKERS: tuple[str, ...] = (
    "instead",
    "rather than",
    "only",
    "skip",
    "don't",
    "do not",
    "without",
    "longer",
    "shorter",
    "less",
    "more",
    "extra",
    "swap",
    "replace",
    "switch",
    "thick",
    "thin",
    "?",
)

MIN_BULLETS = 2


def _mentions_cue(text: str, techniques: list[str]) -> bool:
    """True if `text` talks about any of `techniques`."""
    lowered = text.lower()
    return any(
        re.search(rf"\b{re.escape(cue)}", lowered)
        for technique in techniques
        for cue in TECHNIQUE_CUES.get(technique, ())
    )


def _mentions_ingredient(text: str, ingredients: list[str]) -> bool:
    """True if `text` names any of `ingredients` (as words, plain or normalized)."""
    lowered = text.lower()
    for ingredient in ingredients:
        for form in {ingredient.lower(), normalize(ingredient)}:
            if form and re.search(rf"\b{re.escape(form)}", lowered):
                return True
    return False


def restates_shared_step(bullet: str, delta: Delta) -> bool:
    """True if a bullet only repeats a step the cook already does.

    Args:
        bullet: One written change.
        delta: The computed difference between their dish and the new one.

    Returns:
        True when the bullet mentions a shared technique and nothing new: no new
        ingredient, no new or dropped technique, and no word saying what changes.
    """
    shared = list(delta.shared_techniques)
    if not shared or not _mentions_cue(bullet, shared):
        return False
    if _mentions_ingredient(bullet, delta.new_ingredients):
        return False
    if _mentions_cue(bullet, [*delta.new_techniques, *delta.dropped_techniques]):
        return False
    lowered = bullet.lower()
    return not any(marker in lowered for marker in CHANGE_MARKERS)


def drop_restated(changes: list[str], delta: Delta) -> list[str]:
    """Remove bullets that only repeat shared steps.

    Args:
        changes: The written bullets, most important first.
        delta: The computed difference.

    Returns:
        The bullets that say something new, in their original order.
    """
    return [b for b in changes if not restates_shared_step(b, delta)]
