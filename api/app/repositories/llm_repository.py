"""Data access for the LLM response cache and the daily usage counter."""

import logging
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.db import LLMCacheEntry, LLMUsageDay

logger = logging.getLogger(__name__)


class LLMCacheRepository:
    """Get and store cached LLM responses. Failures degrade to 'no cache', never crash."""

    def __init__(self, session_factory: sessionmaker) -> None:
        """Args: session_factory: SQLAlchemy session factory."""
        self._sessions = session_factory

    def get(self, key: str) -> str | None:
        """Return the cached JSON for `key`, or None (also on DB error)."""
        try:
            with self._sessions() as session:
                entry = session.get(LLMCacheEntry, key)
                return entry.response_json if entry else None
        except SQLAlchemyError:
            logger.exception("Cache read failed")
            return None

    def put(self, key: str, task: str, model: str, response_json: str) -> None:
        """Store a response. Errors are logged and swallowed — the cache is optional."""
        try:
            with self._sessions() as session:
                session.merge(
                    LLMCacheEntry(key=key, task=task, model=model, response_json=response_json)
                )
                session.commit()
        except SQLAlchemyError:
            logger.exception("Cache write failed")


class LLMUsageRepository:
    """Count real LLM calls per UTC day, to enforce the daily spending cap."""

    def __init__(self, session_factory: sessionmaker) -> None:
        """Args: session_factory: SQLAlchemy session factory."""
        self._sessions = session_factory

    def calls_today(self) -> int:
        """Return today's call count.

        Raises:
            SQLAlchemyError: If the database is unreachable (the cap fails closed).
        """
        with self._sessions() as session:
            row = session.get(LLMUsageDay, datetime.now(UTC).date())
            return row.calls if row else 0

    def record_call(self) -> None:
        """Add one to today's count. Errors are logged; the call already happened."""
        today = datetime.now(UTC).date()
        try:
            with self._sessions() as session:
                row = session.get(LLMUsageDay, today)
                if row is None:
                    session.add(LLMUsageDay(day=today, calls=1))
                else:
                    row.calls += 1
                session.commit()
        except SQLAlchemyError:
            logger.exception("Usage write failed")
