"""Shared kitchens: storage round-trip, unknown ids, and the HTTP layer."""

import pytest
from fastapi.testclient import TestClient

from app.deps import get_share_service
from app.main import create_app
from app.repositories.share_repository import ShareRepository, ShareStoreError
from app.services.share_service import ShareService


@pytest.fixture
def service(session_factory) -> ShareService:
    return ShareService(ShareRepository(session_factory, id_bytes=6))


def test_share_round_trip(service, chicken_and_rice) -> None:
    share_id = service.create([chicken_and_rice])
    assert len(share_id) == 8
    shared = service.get(share_id)
    assert shared is not None
    assert shared.dishes == [chicken_and_rice]


def test_unknown_share_is_none(service) -> None:
    assert service.get("nope1234") is None


class BrokenRepo:
    def create(self, payload_json: str) -> str:
        raise ShareStoreError("down")

    def get(self, share_id: str):
        raise ShareStoreError("down")


@pytest.fixture
def client(service) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_share_service] = lambda: service
    with TestClient(app) as test_client:
        test_client.app_ref = app  # type: ignore[attr-defined]
        yield test_client


def test_share_routes(client, chicken_and_rice) -> None:
    created = client.post("/api/shares", json={"dishes": [chicken_and_rice.model_dump()]})
    assert created.status_code == 201
    share_id = created.json()["id"]
    opened = client.get(f"/api/shares/{share_id}")
    assert opened.status_code == 200
    assert opened.json()["dishes"][0]["name"] == "Chicken leg with rice"
    assert client.get("/api/shares/missing1").status_code == 404
    assert client.get("/api/shares/bad!id").status_code == 422


def test_share_store_down_is_503(client, chicken_and_rice) -> None:
    client.app_ref.dependency_overrides[get_share_service] = lambda: ShareService(BrokenRepo())
    response = client.post("/api/shares", json={"dishes": [chicken_and_rice.model_dump()]})
    assert response.status_code == 503
    assert client.get("/api/shares/abcd1234").status_code == 503


def test_share_rejects_empty_kitchen(client) -> None:
    assert client.post("/api/shares", json={"dishes": []}).status_code == 422
