"""Data access for passkey accounts: users, passkeys, challenges, sessions, synced kitchens."""

import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.db import AuthChallenge, AuthSession, Passkey, SyncedKitchen, User

logger = logging.getLogger(__name__)


class AccountStoreError(RuntimeError):
    """The account store couldn't be read or written."""


def aware(moment: datetime) -> datetime:
    """SQLite hands back naive datetimes; treat them as UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


class AccountRepository:
    """All account storage. Every method raises AccountStoreError on a database failure."""

    def __init__(self, session_factory: sessionmaker) -> None:
        """Args: session_factory: SQLAlchemy session factory."""
        self._sessions = session_factory

    def add_challenge(self, challenge: AuthChallenge) -> None:
        """Store a new one-time challenge."""
        self._write(lambda s: s.add(challenge), "challenge write")

    def take_challenge(self, challenge_id: str) -> AuthChallenge | None:
        """Return a challenge and delete it, so it can only be used once."""

        def take(session) -> AuthChallenge | None:
            row = session.get(AuthChallenge, challenge_id)
            if row is not None:
                session.delete(row)
            return row

        return self._write(take, "challenge take")

    def purge_challenges(self, before: datetime) -> None:
        """Delete challenges older than `before` (abandoned prompts)."""
        self._write(
            lambda s: s.execute(delete(AuthChallenge).where(AuthChallenge.created_at < before)),
            "challenge purge",
        )

    def create_user(self, user_id: str, passkey: Passkey) -> None:
        """Create an account with its first passkey."""

        def create(session) -> None:
            session.add(User(id=user_id))
            session.flush()
            session.add(passkey)

        self._write(create, "user create")

    def passkey(self, credential_id: str) -> Passkey | None:
        """Look up a passkey by its base64url credential id."""
        return self._read(lambda s: s.get(Passkey, credential_id), "passkey read")

    def set_sign_count(self, credential_id: str, sign_count: int) -> None:
        """Record the authenticator's new signature counter."""

        def update(session) -> None:
            row = session.get(Passkey, credential_id)
            if row is not None:
                row.sign_count = sign_count

        self._write(update, "sign count")

    def add_session(self, token_hash: str, user_id: str, expires_at: datetime) -> None:
        """Store a new sign-in."""
        self._write(
            lambda s: s.add(
                AuthSession(token_hash=token_hash, user_id=user_id, expires_at=expires_at)
            ),
            "session write",
        )

    def session_user(self, token_hash: str, now: datetime) -> str | None:
        """The user id behind a live session, or None if unknown or expired."""
        row = self._read(lambda s: s.get(AuthSession, token_hash), "session read")
        if row is None or aware(row.expires_at) <= now:
            return None
        return row.user_id

    def end_session(self, token_hash: str) -> None:
        """Sign out one device."""
        self._write(
            lambda s: s.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash)),
            "session delete",
        )

    def kitchen(self, user_id: str) -> SyncedKitchen | None:
        """The user's synced kitchen, if any."""
        return self._read(lambda s: s.get(SyncedKitchen, user_id), "kitchen read")

    def save_kitchen(self, user_id: str, payload_json: str, now: datetime) -> None:
        """Create or replace the user's synced kitchen."""

        def save(session) -> None:
            row = session.get(SyncedKitchen, user_id)
            if row is None:
                session.add(
                    SyncedKitchen(user_id=user_id, payload_json=payload_json, updated_at=now)
                )
            else:
                row.payload_json, row.updated_at = payload_json, now

        self._write(save, "kitchen write")

    def delete_user(self, user_id: str) -> None:
        """Delete an account and everything stored for it."""

        def wipe(session) -> None:
            for table in (SyncedKitchen, AuthSession, Passkey):
                session.execute(delete(table).where(table.user_id == user_id))
            session.execute(delete(User).where(User.id == user_id))

        self._write(wipe, "user delete")

    def passkey_count(self, user_id: str) -> int:
        """How many passkeys the user has."""
        rows = self._read(
            lambda s: s.scalars(select(Passkey.id).where(Passkey.user_id == user_id)).all(),
            "passkey count",
        )
        return len(rows)

    def _read(self, fn, what: str):
        try:
            with self._sessions() as session:
                result = fn(session)
                session.expunge_all()
                return result
        except SQLAlchemyError as exc:
            logger.exception("Account store failed: %s", what)
            raise AccountStoreError(what) from exc

    def _write(self, fn, what: str):
        try:
            with self._sessions() as session:
                result = fn(session)
                session.commit()
                return result
        except SQLAlchemyError as exc:
            logger.exception("Account store failed: %s", what)
            raise AccountStoreError(what) from exc
