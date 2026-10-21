"""Follow-up questions (picked by how much an answer would change), "what I have", and honesty."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.api import Diet, Have, Patch
from app.models.dish import UserDish, ingredients_of
from app.services.graph_service import GraphService, Owned
from app.services.question_service import QuestionService, apply_patch
from app.services.repertoire_service import _distinct
from tests.conftest import make_dish

# A rice dish one step from chicken-and-rice in every way except that it needs an oven.
OVEN_RICE = make_dish(
    id="oven_rice",
    name="Oven chicken rice",
    techniques=["marinate", "rice_in_stock", "bake"],
    equipment=["oven"],
    key_ingredients=["chicken leg", "rice", "chicken stock", "onion", "garlic", "paprika"],
)


@pytest.fixture
def graph(catalog, settings) -> GraphService:
    return GraphService([*catalog, OVEN_RICE], settings)


@pytest.fixture
def service(graph, settings) -> QuestionService:
    return QuestionService(graph, settings)


def test_apply_patch_is_pure(chicken_and_rice) -> None:
    rep, have = [chicken_and_rice], Have()
    dishes, new_have = apply_patch(
        rep, have, Patch(dish=0, add_techniques=["sear", "marinate"], add_equipment=["oven"])
    )
    assert dishes[0].techniques == ["marinate", "rice_in_stock", "sear"]
    assert new_have.equipment == ["oven"]
    assert rep[0].techniques == ["marinate", "rice_in_stock"] and have.equipment == []


def test_apply_patch_sets_protein_and_ignores_bad_index(chicken_and_rice) -> None:
    dishes, _ = apply_patch([chicken_and_rice], Have(), Patch(dish=0, protein="egg"))
    assert dishes[0].protein == "egg"
    same, _ = apply_patch([chicken_and_rice], Have(), Patch(dish=5, protein="egg"))
    assert same[0].protein == "chicken"


def test_oven_is_asked_because_it_unlocks_a_dish(service, chicken_and_rice) -> None:
    questions = service.ask([chicken_and_rice])
    equipment = next(q for q in questions if q.id == "kitchen:equipment")
    labels = [o.label for o in equipment.options]
    assert labels[0] == "Oven"  # the one that changes something comes first
    assert labels[-1] == "None of these"
    assert equipment.multi and equipment.why


def test_only_options_that_change_something(service, chicken_and_rice) -> None:
    equipment = next(q for q in service.ask([chicken_and_rice]) if q.id == "kitchen:equipment")
    # Nothing in the test catalog needs a steamer, so it is never offered.
    assert "Steamer" not in [o.label for o in equipment.options]


def test_dismissed_and_owned_are_not_asked_again(service, chicken_and_rice) -> None:
    assert not any(
        q.id == "kitchen:equipment"
        for q in service.ask([chicken_and_rice], dismissed={"kitchen:equipment"})
    )
    have = Have(equipment=["oven", "wok", "pressure_cooker", "blender", "air_fryer"])
    for q in service.ask([chicken_and_rice], have=have):
        assert all(o.label != "Oven" for o in q.options)


def test_at_most_max_questions(service, settings, chicken_and_rice) -> None:
    assert len(service.ask([chicken_and_rice])) <= settings.max_questions


def test_protein_options_respect_diet(service) -> None:
    pasta = UserDish(
        name="Garlic rice",
        family="rice_with_protein",
        protein="none",
        starch="rice",
        techniques=["rice_in_stock"],
        equipment=["stovetop"],
        flavor=["garlic_ginger"],
        key_ingredients=["rice", "garlic"],
        effort="weeknight",
    )
    candidates = service._candidates([pasta], Diet(vegetarian=True, avoid=["egg"]), Have())
    protein = next(q for q in candidates if q.id.endswith(":protein"))
    labels = [o.label for o in protein.options]
    assert "Chicken" not in labels and "Egg" not in labels and "Paneer" in labels


def test_cooked_dishes_get_no_questions(service, chicken_and_rice) -> None:
    cooked = chicken_and_rice.model_copy(update={"source": "cooked"})
    assert all(q.id == "kitchen:equipment" for q in service._candidates([cooked], Diet(), Have()))


def test_owned_equipment_makes_oven_dishes_one_step(graph, chicken_and_rice) -> None:
    without = graph.one_step_ids([chicken_and_rice])
    with_oven = graph.one_step_ids([chicken_and_rice], owned=Owned(equipment=frozenset({"oven"})))
    assert "oven_rice" not in without and "oven_rice" in with_oven


def test_owned_ingredients_shrink_what_you_need(graph, chicken_and_rice) -> None:
    before = graph.cousin_for([chicken_and_rice], "kabsa")
    after = graph.cousin_for(
        [chicken_and_rice], "kabsa", owned=Owned(ingredients=frozenset({"dried lime"}))
    )
    assert before and after
    assert "dried lime" in before[1].new_ingredients
    assert "dried lime" not in after[1].new_ingredients


def test_guesses_count_as_ingredients(chicken_and_rice) -> None:
    dish = chicken_and_rice.model_copy(update={"assumed_ingredients": ["garam masala"]})
    assert "garam masala" in ingredients_of(dish)


def test_distinct_drops_staples_dupes_and_said() -> None:
    assert _distinct(["Oil", "garlic", "Garlic", "water", "cumin"], skip={"cumin"}) == ["garlic"]


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_questions_route(client, chicken_and_rice) -> None:
    body = {"repertoire": [chicken_and_rice.model_dump()], "have": {"equipment": ["oven"]}}
    response = client.post("/api/questions", json=body)
    assert response.status_code == 200
    for q in response.json()["questions"]:
        assert q["text"] and q["options"] and q["why"]


def test_have_is_validated(client, chicken_and_rice) -> None:
    body = {"repertoire": [chicken_and_rice.model_dump()], "have": {"equipment": ["spaceship"]}}
    assert client.post("/api/map", json=body).status_code == 422
