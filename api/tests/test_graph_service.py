"""The dish graph: distance, one-step rules, exclusion and diversity."""

from datetime import date

from app.config import Settings
from app.models.dish import Dish, UserDish
from app.services.graph_service import DietRule, GraphService
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


def test_protein_swap_is_not_one_step(catalog, chicken_and_rice, settings) -> None:
    graph = GraphService(catalog, settings)
    plov = next(d for d in catalog if d.id == "plov")  # lamb instead of chicken
    delta = _delta(graph, chicken_and_rice, plov)
    assert not delta.same_protein
    assert not delta.is_one_step


def test_diet_rule_is_a_hard_filter(catalog, chicken_and_rice, settings) -> None:
    graph = GraphService(catalog, settings)
    everything = {d.id for d, _ in graph.find_cousins([chicken_and_rice], limit=10)}
    no_dairy = {
        d.id
        for d, _ in graph.find_cousins(
            [chicken_and_rice], limit=10, diet=DietRule(avoid=frozenset({"dairy"}))
        )
    }
    assert "tandoori_chicken" in everything
    assert "tandoori_chicken" not in no_dairy
    vegetarian = graph.find_cousins([chicken_and_rice], limit=10, diet=DietRule(vegetarian=True))
    assert vegetarian == []  # every test dish has meat or fish


def test_tonight_picks_one_step_and_stretch(catalog, chicken_and_rice, settings) -> None:
    graph = GraphService(catalog, settings)
    picks = graph.pick_tonight([chicken_and_rice], today=date(2026, 10, 20))
    assert picks.familiar == chicken_and_rice
    assert picks.one_step is not None and picks.one_step[1].is_one_step
    assert picks.stretch is not None
    stretch_dish, stretch_delta = picks.stretch
    assert not stretch_delta.is_one_step
    assert not stretch_delta.new_equipment  # never needs gear the user lacks
    assert stretch_dish.id != picks.one_step[0].id


def test_tonight_respects_time_and_skips(catalog, chicken_and_rice, settings) -> None:
    graph = GraphService(catalog, settings)
    first = graph.pick_tonight([chicken_and_rice])
    assert first.one_step is not None
    skipped = graph.pick_tonight([chicken_and_rice], skip=frozenset({first.one_step[0].id}))
    assert skipped.one_step is None or skipped.one_step[0].id != first.one_step[0].id

    quick = graph.pick_tonight([chicken_and_rice], max_minutes=30)
    assert quick.one_step is None and quick.stretch is None  # every test dish takes 90 min
    assert quick.familiar == chicken_and_rice  # your own dish always fits


def test_tonight_familiar_rotates_and_prefers_weeknight(
    catalog, chicken_and_rice, settings
) -> None:
    biryani = chicken_and_rice.model_copy(update={"name": "Biryani", "effort": "weekend"})
    graph = GraphService(catalog, settings)
    days = {
        graph.pick_tonight([chicken_and_rice, biryani], today=date(2026, 10, d)).familiar.name
        for d in (20, 21)
    }
    assert days == {"Chicken leg with rice", "Biryani"}
    for d in (20, 21):
        quick = graph.pick_tonight(
            [chicken_and_rice, biryani], max_minutes=45, today=date(2026, 10, d)
        )
        assert quick.familiar.name == "Chicken leg with rice"
    skipped = graph.pick_tonight([chicken_and_rice], skip=frozenset({"Chicken leg with rice"}))
    assert skipped.familiar is None


def test_changing_the_base_is_not_one_step(chicken_and_rice, settings) -> None:
    from tests.conftest import make_dish

    pasta = make_dish(
        id="aglio_olio",
        name="Aglio e Olio",
        family="noodles",
        protein="none",
        starch="pasta",
        techniques=["boil", "pan_fry"],
        flavor=["garlic_ginger", "chili_heat"],
        key_ingredients=["spaghetti", "garlic", "chili flake", "parsley"],
    )
    delta = _delta(GraphService([pasta], settings), chicken_and_rice, pasta)
    assert not delta.same_family and not delta.same_starch
    assert not delta.is_one_step


def test_own_dish_anchors_when_both_are_one_step(catalog, chicken_and_rice, settings) -> None:
    from tests.conftest import make_dish

    # A cooked dish that is even closer to kabsa than the user's own dish.
    maqluba = make_dish(
        id="maqluba", name="Maqluba", techniques=["sear", "simmer", "rice_in_stock"]
    )
    cooked = UserDish.model_validate(
        {**maqluba.model_dump(), "notes": "", "source": "cooked", "matched_dish_id": "maqluba"}
    )
    graph = GraphService(catalog, settings)
    found = dict((d.id, x) for d, x in graph.find_cousins([cooked, chicken_and_rice], 10))
    assert found["kabsa"].is_one_step
    assert found["kabsa"].anchor_name == "Chicken leg with rice"
