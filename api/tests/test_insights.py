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


def test_stats_include_llm_cost_per_device(session_factory) -> None:
    from app.models.api import UsageEventIn
    from app.repositories.llm_repository import LLMUsageRepository

    usage = LLMUsageRepository(session_factory)
    service = InsightService(InsightRepository(session_factory), usage, 0.75, 4.50)
    for device in (DEVICE, DEVICE.replace("3f2b", "aaaa")):
        service.record(UsageEvents(device=device, events=[UsageEventIn(name="cooked")]))
    usage.record_call()
    usage.record_call()
    usage.record_tokens(1_000_000, 0)
    usage.record_tokens(0, 1_000_000)
    usage.record_tokens(0, 0)  # nothing to add

    stats = service.stats(days=7)
    assert stats.llm_calls == 2
    assert (stats.llm_input_tokens, stats.llm_output_tokens) == (1_000_000, 1_000_000)
    assert stats.llm_cost_usd == 5.25
    assert stats.devices == 2
    assert stats.llm_cost_per_device_usd == 2.625


def test_stats_without_usage_repo_report_zero_cost(service) -> None:
    stats = service.stats(days=7)
    assert stats.llm_cost_usd == 0.0 and stats.llm_cost_per_device_usd == 0.0


def test_cost_read_failure_degrades_to_zero(session_factory) -> None:
    from unittest.mock import MagicMock

    from sqlalchemy.exc import OperationalError

    usage = MagicMock()
    usage.totals_since.side_effect = OperationalError("x", {}, Exception("down"))
    service = InsightService(InsightRepository(session_factory), usage, 0.75, 4.50)
    assert service.stats(days=7).llm_calls == 0


async def test_gateway_records_tokens_of_real_calls_only(session_factory, make_gateway) -> None:
    from datetime import UTC, datetime

    from pydantic import BaseModel

    from app.repositories.llm_repository import LLMUsageRepository
    from tests.conftest import FakeLLMClient

    class Out(BaseModel):
        text: str

    client = FakeLLMClient(lambda schema, prompt: Out(text=prompt))
    client.last_tokens = (120, 30)
    gateway = make_gateway(client)
    await gateway.run(task="t", instructions="i", prompt="p", schema=Out)
    await gateway.run(task="t", instructions="i", prompt="p", schema=Out)  # cached: no tokens
    totals = LLMUsageRepository(session_factory).totals_since(datetime.now(UTC).date())
    assert totals == (1, 120, 30)
