"""Data access for shared kitchen snapshots."""

import logging
import secrets

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.db import SharedKitchen

logger = logging.getLogger(__name__)


class ShareStoreError(RuntimeError):
    """The share store couldn't be read or written."""


class ShareRepository:
    """Create and read shared kitchens. Unlike the LLM cache, failures are reported."""

    def __init__(self, session_factory: sessionmaker, id_bytes: int) -> None:
        """Args: session_factory: SQLAlchemy session factory; id_bytes: randomness per id."""
        self._sessions = session_factory
        self._id_bytes = id_bytes

    def create(self, payload_json: str) -> str:
        """Store a snapshot and return its new short id.

        Raises:
            ShareStoreError: If the database write fails.
        """
        share_id = secrets.token_urlsafe(self._id_bytes)
        try:
            with self._sessions() as session:
                session.add(SharedKitchen(id=share_id, payload_json=payload_json))
                session.commit()
        except SQLAlchemyError as exc:
            logger.exception("Share write failed")
            raise ShareStoreError("Could not save the shared kitchen") from exc
        return share_id

    def get(self, share_id: str) -> SharedKitchen | None:
        """Return a snapshot by id, or None if there is none.

        Raises:
            ShareStoreError: If the database read fails.
        """
        try:
            with self._sessions() as session:
                return session.get(SharedKitchen, share_id)
        except SQLAlchemyError as exc:
            logger.exception("Share read failed")
            raise ShareStoreError("Could not read the shared kitchen") from exc
