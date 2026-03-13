"""Database base configuration with async SQLAlchemy."""

import logging
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings

logger = logging.getLogger(__name__)

_TESTING = os.environ.get("TESTING", "").lower() in ("1", "true", "yes")


def _make_engine():
    """Build async engine. In TESTING use NullPool to avoid asyncpg event-loop issues."""
    kwargs = {
        "pool_pre_ping": True,  # avoid "connection is closed" when pool returns a stale connection
        "echo": settings.debug,
    }
    if _TESTING:
        from sqlalchemy.pool import NullPool
        kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
    return create_async_engine(settings.database_url, **kwargs)


if _TESTING:
    # Defer engine/session creation to test event loop (see tests/conftest.py).
    engine = None  # type: ignore[assignment]
    AsyncSessionLocal = None  # type: ignore[assignment]

    def init_engine_for_testing() -> None:
        global engine, AsyncSessionLocal
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


# Canary log for database initialization (non-testing only)
if not _TESTING:
    logger.info(
        "[dental-booking] Database engine initialized",
        extra={"component": "database", "pool_size": settings.db_pool_size},
    )
