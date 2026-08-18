"""Database base configuration with async SQLAlchemy."""

import asyncio
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

_TEST_POOL_SIZE = 12
_TEST_POOL_MAX_OVERFLOW = 8
_TEST_POOL_RECYCLE_SEC = 90
_TEST_CONNECT_ATTEMPTS = 4


def _is_transient_connect_error(exc: BaseException) -> bool:
    """Windows Docker Desktop NAT frequently RST's host→published-port Postgres (WinError 10054)."""
    if isinstance(
        exc,
        (ConnectionResetError, ConnectionRefusedError, ConnectionAbortedError, TimeoutError),
    ):
        return True
    if isinstance(exc, OSError) and getattr(exc, "winerror", None) == 10054:
        return True
    msg = str(exc).lower()
    return "10054" in msg or "connection reset" in msg or "connection was closed" in msg


def _asyncpg_connect_args(dsn: str) -> dict[str, Any]:
    """asyncpg defaults to an SSL upgrade probe; Docker/Windows Postgres often RST that handshake (WinError 10054).

    Honor explicit sslmode in the DSN. Otherwise skip SSL for tests and for typical compose/local hosts.
    """
    args: dict[str, Any] = {
        "timeout": 30,
        "command_timeout": 120,
    }
    if _TESTING:
        # Reconnects after RST must not reuse prepared-statement names from a dead backend.
        args["statement_cache_size"] = 0
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


async def _asyncpg_connect(dsn: str):
    """Open one asyncpg connection; retry transient Windows/Docker RST on connect."""
    import asyncpg

    url = make_url(dsn)
    kwargs: dict[str, Any] = {
        "host": url.host,
        "port": url.port or 5432,
        "user": url.username,
        "password": url.password,
        "database": url.database,
        **_asyncpg_connect_args(dsn),
    }
    last: BaseException | None = None
    delay = 0.2
    for attempt in range(1, _TEST_CONNECT_ATTEMPTS + 1):
        try:
            return await asyncpg.connect(**kwargs)
        except Exception as exc:
            last = exc
            if attempt >= _TEST_CONNECT_ATTEMPTS or not _is_transient_connect_error(exc):
                raise
            logger.warning(
                "asyncpg connect retry %s/%s after transient error: %s",
                attempt,
                _TEST_CONNECT_ATTEMPTS,
                exc,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 2.0)
    assert last is not None
    raise last


def _make_engine(*, url: str | None = None):
    """Build async engine.

    TESTING shares one pytest session loop, so a small recycled pool is safe and avoids
    NullPool's per-checkout TCP handshake through Docker Desktop NAT (WinError 10054 after
    a long suite). Production keeps a sized pool from settings.
    """
    dsn = url or settings.database_url
    kwargs: dict[str, Any] = {
        "pool_pre_ping": True,  # avoid "connection is closed" when pool returns a stale connection
        "echo": settings.debug,
    }
    if _TESTING:
        async def _creator():
            return await _asyncpg_connect(dsn)

        kwargs["async_creator"] = _creator
        kwargs["pool_size"] = _TEST_POOL_SIZE
        kwargs["max_overflow"] = _TEST_POOL_MAX_OVERFLOW
        kwargs["pool_recycle"] = _TEST_POOL_RECYCLE_SEC
        kwargs["pool_timeout"] = 30
    else:
        kwargs["connect_args"] = _asyncpg_connect_args(dsn)
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
        logger.info("[dental-booking] Test database engine initialized (recycled pool)")
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
