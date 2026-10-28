"""Feedback from the app, anonymous usage events, and the owner's stats."""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from app.config import settings
from app.deps import get_insight_service
from app.limiter import limiter
from app.models.api import FeedbackRequest, UsageEvents, UsageStats
from app.repositories.insight_repository import InsightStoreError
from app.services.insight_service import InsightService

router = APIRouter(prefix="/api")

DOWN_MESSAGE = "Couldn't send that just now. Please try again."


@router.post("/feedback", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.feedback_rate_limit)
async def feedback(
    request: Request,
    body: FeedbackRequest,
    service: InsightService = Depends(get_insight_service),
) -> None:
    """Store a message from the feedback box."""
    try:
        service.feedback(body.message, body.page)
    except InsightStoreError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, DOWN_MESSAGE) from exc


@router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.events_rate_limit)
async def events(
    request: Request,
    body: UsageEvents,
    service: InsightService = Depends(get_insight_service),
) -> None:
    """Store a batch of anonymous usage events."""
    try:
        service.record(body)
    except InsightStoreError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, DOWN_MESSAGE) from exc


def owner(authorization: str | None = Header(default=None)) -> None:
    """Only the owner (ADMIN_TOKEN) may read stats; with no token set, stats don't exist."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not settings.admin_token or not secrets.compare_digest(token, settings.admin_token):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")


@router.get("/admin/stats", response_model=UsageStats, dependencies=[Depends(owner)])
async def stats(
    days: int = Query(default=settings.stats_default_days, ge=1, le=365),
    service: InsightService = Depends(get_insight_service),
) -> UsageStats:
    """Usage over the last `days`: devices, returning devices, events, top dishes, feedback."""
    try:
        return service.stats(days)
    except InsightStoreError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, DOWN_MESSAGE) from exc
