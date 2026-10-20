"""Gateway (cache + cap), repertoire parsing, and cousin diff writing — with a fake LLM."""

import pytest
from pydantic import BaseModel

from app.llm.client import LLMError
from app.models.dish import UserDish
from app.repositories.dish_repository import DishRepository
from app.services.cousin_service import CousinService, fallback_diff
from app.services.graph_service import GraphService
from app.services.llm_gateway import DailyCapExceeded
from app.services.repertoire_service import NoDishesFound, RepertoireService
from tests.conftest import FakeLLMClient


class Echo(BaseModel):
    value: str


def echo_responder(schema, prompt):
    return Echo(value=prompt)


async def test_gateway_caches_identical_requests(make_gateway) -> None:
    client = FakeLLMClient(echo_responder)
    gateway = make_gateway(client)
    first = await gateway.run(task="t", instructions="i", prompt="hello", schema=Echo)
    second = await gateway.run(task="t", instructions="i", prompt="hello", schema=Echo)
    assert first == second == Echo(value="hello")
    assert client.calls == 1


async def test_gateway_enforces_daily_cap(make_gateway) -> None:
    client = FakeLLMClient(echo_responder)
    gateway = make_gateway(client, cap=2)
    await gateway.run(task="t", instructions="i", prompt="a", schema=Echo)
    await gateway.run(task="t", instructions="i", prompt="b", schema=Echo)
    with pytest.raises(DailyCapExceeded):
        await gateway.run(task="t", instructions="i", prompt="c", schema=Echo)
    # Cached answers are still served once the cap is hit.
    assert await gateway.run(task="t", instructions="i", prompt="a", schema=Echo)


async def test_gateway_propagates_llm_errors(make_gateway) -> None:
    client = FakeLLMClient(echo_responder)
    client.fail = True
    with pytest.raises(LLMError):
        await make_gateway(client).run(task="t", instructions="i", prompt="x", schema=Echo)


@pytest.fixture
def dish_repo(tmp_path, catalog) -> DishRepository:
    import json

    path = tmp_path / "dishes.json"
    path.write_text(json.dumps([d.model_dump() for d in catalog]))
    return DishRepository(path)


async def test_repertoire_drops_unknown_matched_ids(
    make_gateway, dish_repo, chicken_and_rice
) -> None:
    fake = chicken_and_rice.model_copy(update={"matched_dish_id": "made_up_dish"})
    real = chicken_and_rice.model_copy(
        update={"name": "Biryani", "matched_dish_id": "chicken_biryani"}
    )

    def responder(schema, prompt):
        return schema(dishes=[fake, real])

    service = RepertoireService(make_gateway(FakeLLMClient(responder)), dish_repo, 10)
    dishes = await service.parse("chicken and rice, and biryani")
    assert [d.matched_dish_id for d in dishes] == [None, "chicken_biryani"]


async def test_repertoire_with_no_dishes_raises(make_gateway, dish_repo) -> None:
    service = RepertoireService(
        make_gateway(FakeLLMClient(lambda s, p: s(dishes=[]))), dish_repo, 10
    )
    with pytest.raises(NoDishesFound):
        await service.parse("I like music")


async def test_repertoire_caps_dish_count(make_gateway, dish_repo, chicken_and_rice) -> None:
    many = [chicken_and_rice.model_copy(update={"name": f"Dish {i}"}) for i in range(5)]
    service = RepertoireService(
        make_gateway(FakeLLMClient(lambda s, p: s(dishes=many))), dish_repo, 3
    )
    assert len(await service.parse("lots")) == 3


def diff_responder(schema, prompt):
    return schema(
        changes=["Add dried lime.", "Sear the chicken first."],
        keep_line="Keep cooking the rice in stock.",
    )


async def test_cousins_get_code_built_headlines(
    make_gateway, catalog, chicken_and_rice, settings
) -> None:
    service = CousinService(
        GraphService(catalog, settings), make_gateway(FakeLLMClient(diff_responder))
    )
    cousins = await service.find([chicken_and_rice], limit=2)
    assert len(cousins) == 2
    for cousin in cousins:
        assert cousin.diff.headline == f"{cousin.dish.name}: your chicken leg with rice, but…"
        assert cousin.diff.changes == ["Add dried lime.", "Sear the chicken first."]


async def test_cousins_fall_back_when_llm_fails(
    make_gateway, catalog, chicken_and_rice, settings
) -> None:
    client = FakeLLMClient(diff_responder)
    client.fail = True
    service = CousinService(GraphService(catalog, settings), make_gateway(client))
    cousins = await service.find([chicken_and_rice], limit=1)
    assert cousins[0].diff.changes  # template, not an error
    assert cousins[0].diff.headline.endswith("but…")


def test_fallback_diff_reads_naturally(catalog, chicken_and_rice, settings) -> None:
    graph = GraphService(catalog, settings)
    kabsa = next(d for d in catalog if d.id == "kabsa")
    dish, delta = next(
        (d, x) for d, x in graph.find_cousins([chicken_and_rice], 10) if d.id == kabsa.id
    )
    diff = fallback_diff(chicken_and_rice, dish, delta)
    text = " ".join(diff.changes)
    assert "kabsa spice" in text and "dried lime" in text
    assert "Skip marinating." in diff.changes
    assert "_" not in text  # no raw technique ids


def test_user_dish_schema_requires_parts() -> None:
    with pytest.raises(ValueError):
        UserDish.model_validate({"name": "x"})
