"""Feedback, anonymous usage events, and the owner-only stats."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import settings as app_settings
from app.deps import get_insight_service
from app.main import create_app
from app.models.api import UsageEventIn, UsageEvents
from app.repositories.insight_repository import InsightRepository
from app.services.insight_service import InsightService

DEVICE = "3f2b9c1e-0d4a-4c55-9e1a-7b6c5d4e3f21"


@pytest.fixture
def service(session_factory) -> InsightService:
    return InsightService(InsightRepository(session_factory))


@pytest.fixture
def api(service):
    app = create_app()
    app.dependency_overrides[get_insight_service] = lambda: service
    with TestClient(app) as client:
        yield client


def test_feedback_and_events_are_stored_and_counted(api, service, monkeypatch) -> None:
    assert api.post("/api/feedback", json={"message": "  Love the tiles  "}).status_code == 204
    body = {
        "device": DEVICE,
        "events": [{"name": "kitchen_built"}, {"name": "dish_opened", "dish_id": "kabsa"}],
    }
    assert api.post("/api/events", json=body).status_code == 204

    stats = service.stats(7)
    assert stats.devices == 1 and stats.returning_devices == 0
    assert stats.events == {"kitchen_built": 1, "dish_opened": 1}
    assert stats.top_dishes == [("kabsa", 1)]
    assert stats.feedback == ["Love the tiles"]


def test_events_reject_free_text(api) -> None:
    bad_name = {"device": DEVICE, "events": [{"name": "my secret recipe"}]}
    bad_dish = {"device": DEVICE, "events": [{"name": "saved", "dish_id": "Not An Id!"}]}
    assert api.post("/api/events", json=bad_name).status_code == 422
    assert api.post("/api/events", json=bad_dish).status_code == 422


def test_returning_device_counts_once_on_two_days(service, session_factory) -> None:
    from app.db import UsageEvent

    service.record(UsageEvents(device=DEVICE, events=[UsageEventIn(name="cooked")]))
    with session_factory() as session:
        session.add(
            UsageEvent(
                device=DEVICE, name="saved", created_at=datetime.now(UTC) - timedelta(days=2)
            )
        )
        session.commit()
    assert service.stats(7).returning_devices == 1


def test_stats_need_the_owner_token(api, monkeypatch) -> None:
    assert api.get("/api/admin/stats").status_code == 404  # off when no token is set
    monkeypatch.setattr(app_settings, "admin_token", "owner-secret")
    assert api.get("/api/admin/stats", headers={"Authorization": "Bearer nope"}).status_code == 404
    ok = api.get("/api/admin/stats", headers={"Authorization": "Bearer owner-secret"})
    assert ok.status_code == 200 and ok.json()["devices"] == 0
