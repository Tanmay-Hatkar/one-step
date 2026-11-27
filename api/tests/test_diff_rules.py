"""A diff never spends a bullet re-telling a step the cook already does."""

from typing import Any

from app.models.dish import Delta
from app.services.diff_rules import drop_restated, restates_shared_step


def make_delta(**overrides: Any) -> Delta:
    """Dal tadka → mesir wat: same boiling, simmering and blooming; berbere is new."""
    fields: dict[str, Any] = {
        "anchor_name": "Dal Tadka",
        "shared_techniques": ["boil", "simmer", "temper_spices"],
        "new_techniques": [],
        "dropped_techniques": [],
        "new_equipment": [],
        "new_ingredients": ["red lentil", "berbere spice blend", "tomato paste"],
        "new_flavors": [],
        "same_protein": True,
        "same_starch": True,
        "same_family": True,
        "score": 0.9,
        "is_one_step": True,
    }
    return Delta(**{**fields, **overrides})


# Bullets the live app really showed for mesir wat that only repeat dal tadka.
RESTATED = [
    "Boil the lentils until just tender, then simmer gently.",
    "Cook onion and garlic as usual, then bloom whole spices in hot oil.",
]
# Bullets that carry a real change.
REAL_CHANGES = [
    "Use red lentil only, then boil until just tender.",
    "Bloom whole spices in hot oil, then add berbere spice blend.",
    "Simmer longer, until thick and stew-like.",
    "Stir in tomato paste with the onion.",
    "Finish with a squeeze of lime instead of garam masala.",
]


def test_restated_shared_steps_are_caught() -> None:
    delta = make_delta()
    for bullet in RESTATED:
        assert restates_shared_step(bullet, delta), bullet


def test_bullets_with_something_new_are_kept() -> None:
    delta = make_delta()
    for bullet in REAL_CHANGES:
        assert not restates_shared_step(bullet, delta), bullet


def test_new_technique_is_never_a_restatement() -> None:
    delta = make_delta(new_techniques=["roast"])
    assert not restates_shared_step("Roast the lentils, then simmer them.", delta)


def test_nothing_shared_means_nothing_dropped() -> None:
    delta = make_delta(shared_techniques=[])
    assert not restates_shared_step("Boil the lentils, then simmer gently.", delta)


def test_ingredient_words_are_not_technique_cues() -> None:
    """'tomato paste' must not read as making a spice paste."""
    delta = make_delta(shared_techniques=["spice_paste"], new_ingredients=[])
    assert not restates_shared_step("Add a spoon of tomato paste.", delta)


def test_drop_keeps_order() -> None:
    delta = make_delta()
    bullets = [REAL_CHANGES[0], RESTATED[0], REAL_CHANGES[3], RESTATED[1]]
    assert drop_restated(bullets, delta) == [REAL_CHANGES[0], REAL_CHANGES[3]]
