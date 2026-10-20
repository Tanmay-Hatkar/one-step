"""HTTP layer: status codes and shapes, with services replaced by fakes."""

import pytest
from fastapi.testclient import TestClient

from app.deps import get_cousin_service, get_repertoire_service
from app.llm.client import LLMError
from app.main import create_app
from app.services.cousin_service import CousinService
from app.services.graph_service import GraphService
from app.services.llm_gateway import DailyCapExceeded
from app.services.repertoire_service import NoDishesFound
from tests.conftest import FakeLLMClient


class StubRepertoire:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result, self.error = result, error

    async def parse(self, text: str):
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        test_client.app_ref = app  # type: ignore[attr-defined]
        yield test_client
    app.dependency_overrides.clear()


def test_health(client) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_dish_stats(client) -> None:
    stats = client.get("/api/dishes/stats").json()
    assert stats["dishes"] >= 100 and stats["regions"] >= 8


def test_parse_ok(client, chicken_and_rice) -> None:
    client.app_ref.dependency_overrides[get_repertoire_service] = lambda: StubRepertoire(
        [chicken_and_rice]
    )
    response = client.post("/api/repertoire/parse", json={"text": "chicken and rice"})
    assert response.status_code == 200
    assert response.json()["dishes"][0]["name"] == "Chicken leg with rice"


@pytest.mark.parametrize(
    ("error", "status"),
    [(NoDishesFound(), 422), (DailyCapExceeded(), 503), (LLMError(), 502)],
)
def test_parse_errors_map_to_status(client, error, status) -> None:
    client.app_ref.dependency_overrides[get_repertoire_service] = lambda: StubRepertoire(
        error=error
    )
    response = client.post("/api/repertoire/parse", json={"text": "something"})
    assert response.status_code == status
    assert response.json()["detail"]


def test_parse_rejects_oversized_text(client) -> None:
    assert client.post("/api/repertoire/parse", json={"text": "x" * 5000}).status_code == 422


def test_cousins_ok(client, catalog, chicken_and_rice, settings, make_gateway) -> None:
    def responder(schema, prompt):
        return schema(changes=["Add dried lime."], keep_line="Keep the rice.")

    service = CousinService(GraphService(catalog, settings), make_gateway(FakeLLMClient(responder)))
    client.app_ref.dependency_overrides[get_cousin_service] = lambda: service
    response = client.post(
        "/api/cousins", json={"repertoire": [chicken_and_rice.model_dump()], "limit": 2}
    )
    assert response.status_code == 200
    cousins = response.json()["cousins"]
    assert len(cousins) == 2
    assert cousins[0]["diff"]["headline"].endswith("but…")


def test_cousins_rejects_empty_repertoire(client) -> None:
    assert client.post("/api/cousins", json={"repertoire": []}).status_code == 422


def test_tonight_ok(client, catalog, chicken_and_rice, settings, make_gateway) -> None:
    def responder(schema, prompt):
        return schema(changes=["Add dried lime."], keep_line="Keep the rice.")

    service = CousinService(GraphService(catalog, settings), make_gateway(FakeLLMClient(responder)))
    client.app_ref.dependency_overrides[get_cousin_service] = lambda: service
    response = client.post(
        "/api/tonight",
        json={
            "repertoire": [chicken_and_rice.model_dump()],
            "max_minutes": 120,
            "diet": {"vegetarian": False, "avoid": ["dairy"]},
            "skip": ["kabsa"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["familiar"]["name"] == "Chicken leg with rice"
    # Kabsa was skipped and the other close dishes have dairy: nothing one step away fits.
    assert body["one_step"] is None
    assert body["stretch"]["dish"]["id"] == "plov"


def test_cousins_rejects_unknown_allergen(client, chicken_and_rice) -> None:
    response = client.post(
        "/api/cousins",
        json={"repertoire": [chicken_and_rice.model_dump()], "diet": {"avoid": ["kryptonite"]}},
    )
    assert response.status_code == 422


def _service(catalog, settings, make_gateway) -> CousinService:
    def responder(schema, prompt):
        return schema(changes=["Add dried lime."], keep_line="Keep the rice.")

    return CousinService(GraphService(catalog, settings), make_gateway(FakeLLMClient(responder)))


def test_map_ok(client, catalog, chicken_and_rice, settings, make_gateway) -> None:
    service = _service(catalog, settings, make_gateway)
    client.app_ref.dependency_overrides[get_cousin_service] = lambda: service
    body = client.post("/api/map", json={"repertoire": [chicken_and_rice.model_dump()]}).json()
    assert body["catalog_size"] == len(catalog)
    assert body["kitchen"][0]["name"] == "Chicken leg with rice"
    assert body["cousins"] and "diff" not in body["cousins"][0]  # no LLM on the map


def test_one_cousin_ok_and_404(client, catalog, chicken_and_rice, settings, make_gateway) -> None:
    service = _service(catalog, settings, make_gateway)
    client.app_ref.dependency_overrides[get_cousin_service] = lambda: service
    repertoire = [chicken_and_rice.model_dump()]
    ok = client.post("/api/cousin", json={"repertoire": repertoire, "dish_id": "kabsa"})
    assert ok.status_code == 200 and ok.json()["diff"]["changes"] == ["Add dried lime."]
    missing = client.post("/api/cousin", json={"repertoire": repertoire, "dish_id": "nope"})
    assert missing.status_code == 404


def test_evals_endpoint(client) -> None:
    from app.deps import get_eval_repository

    class Repo:
        def __init__(self, results):
            self.results = results

        def latest(self):
            return self.results

    client.app_ref.dependency_overrides[get_eval_repository] = lambda: Repo({"pass_rate": 1.0})
    assert client.get("/api/evals").json() == {"pass_rate": 1.0}
    client.app_ref.dependency_overrides[get_eval_repository] = lambda: Repo(None)
    assert client.get("/api/evals").status_code == 404


def test_eval_repository_reads_file(tmp_path) -> None:
    from app.repositories.eval_repository import EvalResultsRepository

    path = tmp_path / "latest.json"
    assert EvalResultsRepository(path).latest() is None
    path.write_text('{"passed": 3}')
    assert EvalResultsRepository(path).latest() == {"passed": 3}
