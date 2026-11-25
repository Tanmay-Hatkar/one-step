"""Data access for the LLM response cache and the daily usage counter."""

import logging
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.db import LLMCacheEntry, LLMTokenDay, LLMUsageDay

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

    def record_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Add one call's tokens to today's totals. Errors are logged; the call already happened.

        Args:
            input_tokens: Prompt tokens billed.
            output_tokens: Completion (and reasoning) tokens billed.
        """
        if not input_tokens and not output_tokens:
            return
        today = datetime.now(UTC).date()
        try:
            with self._sessions() as session:
                row = session.get(LLMTokenDay, today)
                if row is None:
                    session.add(
                        LLMTokenDay(
                            day=today, input_tokens=input_tokens, output_tokens=output_tokens
                        )
                    )
                else:
                    row.input_tokens += input_tokens
                    row.output_tokens += output_tokens
                session.commit()
        except SQLAlchemyError:
            logger.exception("Token usage write failed")

    def totals_since(self, since: date) -> tuple[int, int, int]:
        """Calls, input tokens and output tokens from `since` (inclusive) to today.

        Raises:
            SQLAlchemyError: If the database is unreachable.
        """
        with self._sessions() as session:
            calls = session.scalar(
                select(func.coalesce(func.sum(LLMUsageDay.calls), 0)).where(
                    LLMUsageDay.day >= since
                )
            )
            tokens_in, tokens_out = session.execute(
                select(
                    func.coalesce(func.sum(LLMTokenDay.input_tokens), 0),
                    func.coalesce(func.sum(LLMTokenDay.output_tokens), 0),
                ).where(LLMTokenDay.day >= since)
            ).one()
        return int(calls or 0), int(tokens_in), int(tokens_out)
