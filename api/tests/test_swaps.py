"""Substitutions by role: offered only from what you have, never against your diet."""

import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.models.substitution import Substitute
from app.repositories.substitution_repository import SubstitutionRepository
from app.services.cousin_service import fallback_diff
from app.services.graph_service import DietRule, GraphService, Owned
from tests.conftest import make_dish

LARB = make_dish(
    id="larb_rice",
    name="Larb rice",
    key_ingredients=["chicken leg", "rice", "chicken stock", "fish sauce", "lime", "mint"],
)
SUBS = {
    "fish sauce": [Substitute(name="anchovy paste"), Substitute(name="soy sauce", note="same")],
    "lime": [Substitute(name="lemon", note="add at the end")],
}


def graph(settings, subs=SUBS) -> GraphService:
    return GraphService([LARB], settings, substitutes=subs)


def owning(*items: str) -> Owned:
    return Owned(ingredients=frozenset(items))


def test_swap_uses_what_you_have(settings, chicken_and_rice) -> None:
    pair = graph(settings).cousin_for([chicken_and_rice], "larb_rice", owned=owning("lemon"))
    assert pair is not None
    swaps = pair[1].swaps
    assert [(s.need, s.use, s.note) for s in swaps] == [("lime", "lemon", "add at the end")]
    assert "lime" in pair[1].new_ingredients  # still listed; the swap is an alternative


def test_no_swap_without_the_stand_in(settings, chicken_and_rice) -> None:
    pair = graph(settings).cousin_for([chicken_and_rice], "larb_rice")
    assert pair is not None and pair[1].swaps == []


def test_swaps_respect_diet(settings, chicken_and_rice) -> None:
    g, owned = graph(settings), owning("anchovy paste", "soy sauce")
    best = g.cousin_for([chicken_and_rice], "larb_rice", owned=owned)
    assert best and best[1].swaps[0].use == "anchovy paste"
    # Avoiding fish: anchovy paste is skipped for the next stand-in.
    no_fish = g.compute_delta(
        chicken_and_rice, LARB, set(owned.ingredients), set(), DietRule(avoid=frozenset({"fish"}))
    )
    assert [s.use for s in no_fish.swaps] == ["soy sauce"]
    # Avoiding soy too: nothing safe to offer.
    neither = g.compute_delta(
        chicken_and_rice,
        LARB,
        set(owned.ingredients),
        set(),
        DietRule(avoid=frozenset({"fish", "soy"})),
    )
    assert neither.swaps == []


def test_vegetarian_never_gets_meat_stand_in(settings, chicken_and_rice) -> None:
    subs = {"lime": [Substitute(name="bacon fat")]}
    delta = graph(settings, subs).compute_delta(
        chicken_and_rice, LARB, {"bacon fat"}, set(), DietRule(vegetarian=True)
    )
    assert delta.swaps == []


def test_swaps_make_a_dish_closer(settings, chicken_and_rice) -> None:
    g = graph(settings)
    before = g.cousin_for([chicken_and_rice], "larb_rice")
    after = g.cousin_for([chicken_and_rice], "larb_rice", owned=owning("lemon", "soy sauce"))
    assert before and after and after[1].score > before[1].score


def test_repository_never_swaps_protein_or_base(tmp_path) -> None:
    path = tmp_path / "subs.json"
    path.write_text(
        json.dumps(
            [
                {"ingredient": "chicken", "role": "protein", "substitutes": [{"name": "tofu"}]},
                {"ingredient": "rice", "role": "starch", "substitutes": [{"name": "quinoa"}]},
                {"ingredient": "lime", "role": "acid", "substitutes": [{"name": "lemon"}]},
            ]
        )
    )
    repo = SubstitutionRepository(path)
    assert set(repo.usable()) == {"lime"}
    assert repo.role_of("chicken") == "protein"


def test_repository_missing_file_means_no_swaps(tmp_path) -> None:
    assert SubstitutionRepository(tmp_path / "nope.json").usable() == {}


def test_fallback_diff_leaves_swapped_items_to_the_swap_list(settings, chicken_and_rice) -> None:
    pair = graph(settings).cousin_for([chicken_and_rice], "larb_rice", owned=owning("lemon"))
    assert pair is not None
    diff = fallback_diff(chicken_and_rice, LARB, pair[1])
    assert not any("lime" in c for c in diff.changes)  # shown as "No lime? Use your lemon"


def test_real_data_loads_and_is_safe() -> None:
    from app.deps import get_substitution_repository

    usable = get_substitution_repository().usable()
    assert len(usable) > 100
    for need, subs in usable.items():
        assert all(s.name != need for s in subs)


def test_techniques_endpoint() -> None:
    with TestClient(create_app()) as client:
        guides = client.get("/api/techniques").json()
    assert len(guides) == 22
    assert all(3 <= len(g["steps"]) <= 5 and g["tip"] for g in guides)
