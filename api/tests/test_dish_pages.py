"""Public dish pages: related dishes come from the graph, never include the dish itself."""

import pytest
from fastapi.testclient import TestClient

from app.deps import get_dish_repository, get_graph
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_related_are_one_step_and_exclude_self() -> None:
    graph = get_graph()
    related = graph.related("kabsa")
    assert related, "kabsa should have neighbours"
    assert all(delta.is_one_step for _, delta in related)
    assert "kabsa" not in {dish.id for dish, _ in related}
    scores = [delta.score for _, delta in related]
    assert scores == sorted(scores, reverse=True)


def test_related_respects_region_cap_and_count(settings) -> None:
    graph = get_graph()
    for dish in get_dish_repository().all()[:60]:
        related = graph.related(dish.id)
        assert len(related) <= 6
        regions = [d.region for d, _ in related]
        assert all(regions.count(r) <= 2 for r in regions)


def test_related_unknown_dish_is_empty() -> None:
    assert get_graph().related("not_a_dish") == []


def test_dish_page_includes_related(client) -> None:
    body = client.get("/api/dishes/kabsa").json()
    related = body["related"]
    assert 1 <= len(related) <= 6
    first = related[0]
    assert set(first) == {"id", "name", "cuisine", "summary", "new_techniques", "new_ingredients"}
    assert all(len(r["new_ingredients"]) <= 5 for r in related)


def test_dish_index_lists_every_dish_sorted(client) -> None:
    index = client.get("/api/dishes").json()
    assert len(index) == len(get_dish_repository().all())
    names = [e["name"].lower() for e in index]
    assert names == sorted(names)
    assert set(index[0]) == {"id", "name", "cuisine", "region"}


def test_stats_route_still_wins_over_dish_id(client) -> None:
    assert "dishes" in client.get("/api/dishes/stats").json()
