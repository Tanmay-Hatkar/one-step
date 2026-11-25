"""Data access for feedback and anonymous usage events."""

import logging
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.db import Feedback, UsageEvent

logger = logging.getLogger(__name__)


class InsightStoreError(RuntimeError):
    """Feedback or usage events couldn't be read or written."""


class InsightRepository:
    """Write feedback and events; read them back for the owner's stats."""

    def __init__(self, session_factory: sessionmaker) -> None:
        """Args: session_factory: SQLAlchemy session factory."""
        self._sessions = session_factory

    def _write(self, rows: Sequence[Feedback | UsageEvent]) -> None:
        try:
            with self._sessions() as session:
                session.add_all(rows)
                session.commit()
        except SQLAlchemyError as exc:
            logger.exception("Insight write failed")
            raise InsightStoreError("Could not save") from exc

    def add_feedback(self, message: str, page: str) -> None:
        """Store one feedback message.

        Raises:
            InsightStoreError: If the database write fails.
        """
        self._write([Feedback(message=message, page=page)])

    def add_events(self, device: str, events: list[tuple[str, str | None]]) -> None:
        """Store (name, dish_id) events for one device.

        Raises:
            InsightStoreError: If the database write fails.
        """
        self._write([UsageEvent(device=device, name=n, dish_id=d) for n, d in events])

    def events_since(self, since: datetime) -> list[tuple[str, str, str | None, datetime]]:
        """(device, name, dish_id, created_at) for every event since a time.

        Raises:
            InsightStoreError: If the database read fails.
        """
        query = select(
            UsageEvent.device, UsageEvent.name, UsageEvent.dish_id, UsageEvent.created_at
        ).where(UsageEvent.created_at >= since)
        try:
            with self._sessions() as session:
                return [tuple(row) for row in session.execute(query)]
        except SQLAlchemyError as exc:
            logger.exception("Insight read failed")
            raise InsightStoreError("Could not read events") from exc

    def recent_feedback(self, since: datetime, limit: int) -> list[str]:
        """Newest feedback messages since a time.

        Raises:
            InsightStoreError: If the database read fails.
        """
        query = (
            select(Feedback.message)
            .where(Feedback.created_at >= since)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
        )
        try:
            with self._sessions() as session:
                return list(session.scalars(query))
        except SQLAlchemyError as exc:
            logger.exception("Insight read failed")
            raise InsightStoreError("Could not read feedback") from exc
