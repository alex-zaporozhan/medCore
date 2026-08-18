"""Database base configuration with async SQLAlchemy."""

import logging
import os
from typing import Any, AsyncGenerator

from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings

logger = logging.getLogger(__name__)

_TESTING = os.environ.get("TESTING", "").lower() in ("1", "true", "yes")

_LOCAL_PG_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "db", "postgres"})


def _asyncpg_connect_args(dsn: str) -> dict[str, Any]:
    """asyncpg defaults to an SSL upgrade probe; Docker/Windows Postgres often RST that handshake (WinError 10054).

    Honor explicit sslmode in the DSN. Otherwise skip SSL for tests and for typical compose/local hosts.
    """
    args: dict[str, Any] = {}
    url = make_url(dsn)
    query = {str(k).lower(): str(v).lower() for k, v in url.query.items()}
    sslmode = query.get("sslmode") or query.get("ssl") or ""
    if sslmode in ("require", "verify-full", "verify-ca", "true", "1"):
        args["ssl"] = True
        return args
    if sslmode in ("disable", "allow", "prefer", "false", "0"):
        # prefer/allow still skip the SSLRequest probe: local Docker Postgres on Windows RST it (WinError 10054).
        args["ssl"] = False
        return args
    host = (url.host or "").lower()
    if _TESTING or host in _LOCAL_PG_HOSTS:
        args["ssl"] = False
    return args


def _make_engine(*, url: str | None = None):
    """Build async engine. In TESTING use NullPool to avoid asyncpg event-loop issues."""
    dsn = url or settings.database_url
    kwargs: dict[str, Any] = {
        "pool_pre_ping": True,  # avoid "connection is closed" when pool returns a stale connection
        "echo": settings.debug,
        "connect_args": _asyncpg_connect_args(dsn),
    }
    if _TESTING:
        from sqlalchemy.pool import NullPool
        kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
    return create_async_engine(dsn, **kwargs)


def _reporting_dsn() -> str:
    """Read-only reporting path: replica DSN when configured (ADR-005)."""
    if settings.database_replica_url:
        return settings.database_replica_url
    return settings.database_url


if _TESTING:
    # Defer engine/session creation to test event loop (see tests/conftest.py).
    engine = None  # type: ignore[assignment]
    AsyncSessionLocal = None  # type: ignore[assignment]
    engine_reporting = None  # type: ignore[assignment]
    AsyncSessionLocalReporting = None  # type: ignore[assignment]

    def init_engine_for_testing() -> None:
        global engine, AsyncSessionLocal, engine_reporting, AsyncSessionLocalReporting
        if engine is not None:
            return
        engine = _make_engine()
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        # Tests use single DB; replica routing is disabled unless DATABASE_REPLICA_URL is set in env.
        engine_reporting = engine
        AsyncSessionLocalReporting = AsyncSessionLocal
        logger.info("[dental-booking] Test database engine initialized (NullPool)")
else:
    engine = _make_engine()
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    engine_reporting = _make_engine(url=settings.database_replica_url) if settings.database_replica_url else engine
    AsyncSessionLocalReporting = async_sessionmaker(
        engine_reporting,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_reporting() -> AsyncGenerator[AsyncSession, None]:
    """Read-heavy admin reporting path: optional replica + statement_timeout (Wave 5)."""
    async with AsyncSessionLocalReporting() as session:
        try:
            ms = int(settings.db_reporting_statement_timeout_ms)
            if ms > 0:
                await session.execute(text(f"SET LOCAL statement_timeout = {ms}"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Canary log for database initialization (non-testing only)
if not _TESTING:
    logger.info(
        "[dental-booking] Database engine initialized",
        extra={"component": "database", "pool_size": settings.db_pool_size},
    )
