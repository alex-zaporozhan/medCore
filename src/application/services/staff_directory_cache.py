"""Redis cache for staff directory read models (profession categories list)."""

from __future__ import annotations

import logging
from uuid import UUID

from src.core.config import settings
from src.infrastructure.database.redis_client import get_redis

logger = logging.getLogger(__name__)

_PREFIX = "staff:dir:v1"


def profession_categories_cache_key(clinic_id: UUID) -> str:
    return f"{_PREFIX}:pc:{clinic_id}"


async def get_staff_cached_json(key: str) -> str | None:
    if not settings.staff_directory_cache_enabled:
        return None
    try:
        r = await get_redis()
        return await r.get(key)
    except Exception as exc:
        logger.warning("staff_directory_cache_get_failed", extra={"key": key, "error": str(exc)})
        return None


async def set_staff_cached_json(key: str, body: str) -> None:
    if not settings.staff_directory_cache_enabled:
        return
    try:
        r = await get_redis()
        await r.setex(key, settings.staff_directory_cache_ttl_seconds, body)
    except Exception as exc:
        logger.warning("staff_directory_cache_set_failed", extra={"key": key, "error": str(exc)})


async def invalidate_staff_profession_categories_cache(clinic_id: UUID) -> None:
    if not settings.staff_directory_cache_enabled:
        return
    key = profession_categories_cache_key(clinic_id)
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception as exc:
        logger.warning(
            "staff_directory_cache_invalidate_failed",
            extra={"clinic_id": str(clinic_id), "error": str(exc)},
        )
