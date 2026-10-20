"""Ingredient normalization decides what counts as 'new' — it has to be right."""

import pytest

from app.services.ingredients import missing_ingredients, normalize, pantry_of


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Chicken Drumsticks", "chicken"),
        ("chicken thigh", "chicken"),
        ("chicken leg", "chicken"),
        ("chicken stock", "chicken stock"),
        ("chicken broth cube", "chicken stock"),
        ("stock cube", "chicken stock"),
        ("basmati rice", "rice"),
        ("jasmine rice", "rice"),
        ("red onions", "onion"),
        ("tomatoes", "tomato"),
        ("lemon juice", "lemon"),
        ("garlic cloves", "garlic"),
        ("coriander leaves", "cilantro"),
        ("curd", "yogurt"),
        ("ground cumin", "cumin"),
        ("  Kabsa   Spice ", "kabsa spice"),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


def test_pantry_includes_staples_and_user_items() -> None:
    pantry = pantry_of([["chicken leg", "basmati rice"]])
    assert {"salt", "oil", "chicken", "rice"} <= pantry


def test_missing_ingredients_keeps_original_names_and_dedupes() -> None:
    pantry = pantry_of([["chicken leg", "rice", "onion"]])
    needed = ["chicken thigh", "basmati rice", "dried lime", "lime juice", "raisins", "salt"]
    assert missing_ingredients(needed, pantry) == ["dried lime", "raisins"]
