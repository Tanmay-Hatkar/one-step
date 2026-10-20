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
