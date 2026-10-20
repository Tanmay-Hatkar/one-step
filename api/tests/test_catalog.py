"""The real seed catalog (data/dishes.json) — checked on every CI run like code."""

from collections import Counter
from typing import get_args

import pytest

from app.config import Settings
from app.models.vocab import DishFamily
from app.repositories.dish_repository import DishRepository
from app.services.graph_service import GraphService

MIN_DISHES_PER_FAMILY = 12
FOUNDING_USER_COUSINS = {
    "kabsa",
    "plov",
    "arroz_con_pollo",
    "jollof_rice_with_chicken",
    "maqluba",
    "chicken_mandi",
    "paella_valenciana",
    "jambalaya",
    "hainanese_chicken_rice",
    "chicken_pulao",
    "kabuli_palaw",
}


@pytest.fixture(scope="module")
def repo() -> DishRepository:
    return DishRepository(Settings(_env_file=None).dishes_path)


def test_ids_are_unique(repo) -> None:
    ids = [d.id for d in repo.all()]
    assert len(ids) == len(set(ids))


def test_every_family_is_well_covered(repo) -> None:
    counts = Counter(d.family for d in repo.all())
    for family in get_args(DishFamily):
        assert counts[family] >= MIN_DISHES_PER_FAMILY, family


def test_allergen_sanity(repo) -> None:
    """Spot-check that obvious allergens are tagged (the v0.2 filter will rely on these)."""
    for dish in repo.all():
        ingredients = " ".join(dish.key_ingredients)
        if "yogurt" in ingredients or "paneer" in ingredients or "cream" in ingredients:
            assert "dairy" in dish.allergens, dish.id
        if "peanut" in ingredients:
            assert "peanut" in dish.allergens, dish.id
        if "shrimp" in ingredients or "prawn" in ingredients:
            assert "shellfish" in dish.allergens, dish.id


def test_founding_user_gets_real_cousins(repo, chicken_and_rice) -> None:
    """The scenario the product was born from: chicken + broth rice → rice cousins abroad."""
    graph = GraphService(repo.all(), Settings(_env_file=None))
    found = graph.find_cousins([chicken_and_rice], limit=5)
    ids = {d.id for d, _ in found}
    assert len(ids & FOUNDING_USER_COUSINS) >= 3, ids
    assert len({d.region for d, _ in found}) >= 3
