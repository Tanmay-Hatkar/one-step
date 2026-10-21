"""Database engine and tables. SQLite locally and in tests, Postgres in production."""

import logging
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, LargeBinary, String, Text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all tables."""


class LLMCacheEntry(Base):
    """One cached LLM response, keyed by a hash of model + task + prompt."""

    __tablename__ = "llm_cache"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    task: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(60))
    response_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class LLMUsageDay(Base):
    """How many real (uncached) LLM calls were made on one UTC day."""

    __tablename__ = "llm_usage"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    calls: Mapped[int] = mapped_column(Integer, default=0)


class SharedKitchen(Base):
    """A read-only snapshot of someone's kitchen, opened by a short link."""

    __tablename__ = "shared_kitchens"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """An account: nothing but an id. No email, no name — a passkey is the only way in."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Passkey(Base):
    """A WebAuthn credential (the public half; the private key never leaves the device)."""

    __tablename__ = "passkeys"

    id: Mapped[str] = mapped_column(
        String(512), primary_key=True, comment="base64url credential id"
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuthChallenge(Base):
    """A one-time passkey challenge, used once and then deleted."""

    __tablename__ = "auth_challenges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), comment="register | login")
    challenge: Mapped[bytes] = mapped_column(LargeBinary)
    origin: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuthSession(Base):
    """A sign-in. Only a hash of the bearer token is stored."""

    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SyncedKitchen(Base):
    """A signed-in user's kitchen, as the web app saves it."""

    __tablename__ = "synced_kitchens"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    payload_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


def make_engine(database_url: str) -> Engine:
    """Create an engine; normalizes Railway-style postgres:// URLs to psycopg.

    Args:
        database_url: SQLAlchemy URL.

    Returns:
        A configured Engine.
    """
    url = database_url
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def init_db(engine: Engine) -> None:
    """Create tables if they don't exist.

    Args:
        engine: The engine to create tables on.

    Raises:
        SQLAlchemyError: If the database is unreachable.
    """
    Base.metadata.create_all(engine)
    logger.info("Database ready (%s)", engine.url.get_backend_name())


def make_session_factory(engine: Engine) -> sessionmaker:
    """Return a session factory bound to `engine`."""
    return sessionmaker(bind=engine, expire_on_commit=False)
