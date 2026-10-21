"""Recipes from the Wikibooks Cookbook: integrity, attribution, and the dish page."""

import pytest
from fastapi.testclient import TestClient

from app.deps import get_dish_repository, get_recipe_repository
from app.main import create_app


def test_every_recipe_belongs_to_a_catalog_dish() -> None:
    dish_ids = {d.id for d in get_dish_repository().all()}
    recipe_ids = get_recipe_repository().ids()
    assert len(recipe_ids) > 500
    assert set(recipe_ids) <= dish_ids


def test_every_recipe_is_attributed() -> None:
    repo = get_recipe_repository()
    for dish_id in repo.ids():
        recipe = repo.get(dish_id)
        assert recipe is not None
        assert recipe.source_url.startswith("https://en.wikibooks.org/wiki/Cookbook:")
        assert recipe.license == "CC BY-SA 4.0" and recipe.revision > 0
        assert recipe.ingredients and recipe.steps


def test_cleaned_of_wiki_markup() -> None:
    repo = get_recipe_repository()
    for dish_id in repo.ids():
        recipe = repo.get(dish_id)
        assert recipe is not None
        for line in recipe.ingredients + recipe.steps:
            assert "[[" not in line and "{{" not in line and "'''" not in line, (dish_id, line)


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_dish_page_with_recipe(client) -> None:
    dish_id = get_recipe_repository().ids()[0]
    body = client.get(f"/api/dishes/{dish_id}").json()
    assert body["dish"]["id"] == dish_id
    assert body["recipe"]["license"] == "CC BY-SA 4.0"


def test_dish_page_unknown_and_invalid(client) -> None:
    assert client.get("/api/dishes/not_a_dish").status_code == 404
    assert client.get("/api/dishes/Bad-Id").status_code == 422


def test_recipe_ids_and_stats_routes(client) -> None:
    assert len(client.get("/api/recipes").json()) > 500
    assert client.get("/api/dishes/stats").json()["dishes"] >= 700
