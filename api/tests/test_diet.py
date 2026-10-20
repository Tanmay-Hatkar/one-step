"""Diet safety net: allergens and vegetarian status from ingredients, and the hard filter."""

import pytest

from app.services.diet import (
    allows,
    ingredient_allergens,
    is_meat_ingredient,
    text_mentions_allergen,
    user_dish_allows,
    with_safe_diet_facts,
)
from tests.conftest import make_dish


@pytest.mark.parametrize(
    ("ingredient", "expected"),
    [
        ("fish sauce", {"fish"}),
        ("soy sauce", {"soy", "gluten"}),
        ("egg noodles", {"egg", "gluten"}),
        ("peanut butter", {"peanut"}),
        ("ghee", {"dairy"}),
        ("roasted cashews", {"tree_nut"}),
        ("oyster sauce", {"shellfish", "gluten"}),
        ("tahini", {"sesame"}),
        # Look-alikes that must not trigger.
        ("coconut milk", set()),
        ("eggplant", set()),
        ("rice noodle", set()),
        ("rice flour", set()),
        ("corn tortilla", set()),
        ("red fermented bean curd", set()),
        ("nutmeg", set()),
    ],
)
def test_ingredient_allergens(ingredient, expected) -> None:
    assert ingredient_allergens(ingredient) == expected


@pytest.mark.parametrize(
    ("ingredient", "meat"),
    [
        ("chicken stock", True),
        ("anchovy", True),
        ("dried shrimp", True),
        ("bacon", True),
        ("paneer", False),
        ("vegetable stock", False),
        ("graham cracker", False),
    ],
)
def test_is_meat_ingredient(ingredient, meat) -> None:
    assert is_meat_ingredient(ingredient) is meat


def test_safe_facts_add_missed_allergens_and_never_remove_tags() -> None:
    dish = make_dish(key_ingredients=["chicken", "rice", "soy sauce"], allergens=["sesame"])
    safe = with_safe_diet_facts(dish)
    assert set(safe.allergens) == {"sesame", "soy", "gluten"}


def test_safe_facts_overrule_a_wrong_vegetarian_tag() -> None:
    dish = make_dish(
        protein="legumes", vegetarian=True, key_ingredients=["lentil", "chicken stock"]
    )
    assert not with_safe_diet_facts(dish).vegetarian


def test_safe_facts_keep_a_true_vegetarian() -> None:
    dish = make_dish(protein="legumes", vegetarian=True, key_ingredients=["lentil", "onion"])
    assert with_safe_diet_facts(dish).vegetarian


def test_allows_applies_vegetarian_and_allergens() -> None:
    dish = make_dish(vegetarian=False, allergens=["dairy"])
    assert allows(dish, vegetarian=False, avoid=set())
    assert not allows(dish, vegetarian=True, avoid=set())
    assert not allows(dish, vegetarian=False, avoid={"dairy"})
    assert allows(dish, vegetarian=False, avoid={"peanut"})


def test_user_dish_allows(chicken_and_rice) -> None:
    assert user_dish_allows(chicken_and_rice, vegetarian=False, avoid={"peanut"})
    assert not user_dish_allows(chicken_and_rice, vegetarian=True, avoid=set())


def test_text_mentions_allergen() -> None:
    assert text_mentions_allergen("Finish with crushed peanuts.", {"peanut"})
    assert text_mentions_allergen("Stir in a knob of butter.", {"dairy"})
    assert not text_mentions_allergen("Stir in coconut milk.", {"dairy"})
    assert not text_mentions_allergen("Add the eggplant.", {"egg"})
