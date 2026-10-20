"""The dish graph: distance, one-step rules, exclusion and diversity."""

from app.config import Settings
from app.models.dish import Dish, UserDish
from app.services.graph_service import GraphService
from app.services.ingredients import pantry_of


def _delta(graph: GraphService, user: UserDish, dish: Dish):
    pantry = pantry_of([user.key_ingredients])
    return graph.compute_delta(user, dish, pantry, set(user.equipment))


def test_kabsa_is_one_step_from_chicken_and_rice(catalog, chicken_and_rice, settings) -> None:
    graph = GraphService(catalog, settings)
    kabsa = next(d for d in catalog if d.id == "kabsa")
    delta = _delta(graph, chicken_and_rice, kabsa)

    assert delta.is_one_step
    assert delta.same_family and delta.same_protein and delta.same_starch
    assert delta.shared_techniques == ["rice_in_stock"]
    assert set(delta.new_techniques) == {"sear", "simmer"}  # basic: not new skills
    assert delta.dropped_techniques == ["marinate"]
    assert delta.new_ingredients == ["tomato", "kabsa spice", "dried lime", "raisin"]


def test_new_equipment_breaks_one_step(catalog, chicken_and_rice, settings) -> None:
    graph = GraphService(catalog, settings)
    tandoori = next(d for d in catalog if d.id == "tandoori_chicken")
    delta = _delta(graph, chicken_and_rice, tandoori)
    assert delta.new_equipment == ["oven"]
    assert not delta.is_one_step


def test_far_dish_scores_below_close_dish(catalog, chicken_and_rice, settings) -> None:
    graph = GraphService(catalog, settings)
    by_id = {d.id: d for d in catalog}
    assert (
        _delta(graph, chicken_and_rice, by_id["kabsa"]).score
        > _delta(graph, chicken_and_rice, by_id["pad_thai"]).score
    )


def test_find_cousins_ranks_close_dishes_first(catalog, chicken_and_rice, settings) -> None:
    graph = GraphService(catalog, settings)
    ids = [d.id for d, _ in graph.find_cousins([chicken_and_rice], limit=3)]
    assert ids[0] in {"kabsa", "chicken_pulao"}
    assert "pad_thai" not in ids


def test_find_cousins_excludes_dishes_already_cooked(catalog, chicken_and_rice, settings) -> None:
    biryani = chicken_and_rice.model_copy(
        update={
            "name": "My biryani",
            "matched_dish_id": "chicken_biryani",
            "techniques": ["marinate", "layered_dum"],
        }
    )
    named_pulao = chicken_and_rice.model_copy(update={"name": "Chicken Pulao"})
    graph = GraphService(catalog, settings)
    ids = {d.id for d, _ in graph.find_cousins([biryani, named_pulao], limit=10)}
    assert "chicken_biryani" not in ids  # matched by id
    assert "chicken_pulao" not in ids  # matched by name


def test_find_cousins_caps_per_region(catalog, chicken_and_rice) -> None:
    strict = Settings(_env_file=None, max_cousins_per_region=1)
    graph = GraphService(catalog, strict)
    regions = [d.region for d, _ in graph.find_cousins([chicken_and_rice], limit=10)]
    assert len(regions) == len(set(regions))


def test_cousin_must_change_something(chicken_and_rice, settings) -> None:
    from tests.conftest import make_dish

    twin = make_dish(
        id="twin",
        name="Twin",
        techniques=["marinate", "rice_in_stock"],
        flavor=["warm_spices"],
        key_ingredients=["chicken", "rice", "onion"],
    )
    graph = GraphService([twin], settings)
    assert graph.find_cousins([chicken_and_rice], limit=5) == []


def test_empty_repertoire_returns_nothing(catalog, settings) -> None:
    assert GraphService(catalog, settings).find_cousins([], limit=5) == []


def test_best_anchor_is_used(catalog, chicken_and_rice, settings) -> None:
    noodles = chicken_and_rice.model_copy(
        update={
            "name": "Hakka noodles",
            "family": "noodles",
            "starch": "wheat_noodles",
            "techniques": ["stir_fry", "boil"],
            "equipment": ["wok"],
        }
    )
    graph = GraphService(catalog, settings)
    found = dict(
        (d.id, delta) for d, delta in graph.find_cousins([chicken_and_rice, noodles], limit=10)
    )
    assert found["kabsa"].anchor_name == "Chicken leg with rice"
    assert found["pad_thai"].anchor_name == "Hakka noodles"
