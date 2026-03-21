"""Redis read-through cache for heavy admin report GETs (Wave 5 / QA_ARCH A9)."""

from __future__ import annotations

import logging
from uuid import UUID

from src.core.config import settings
from src.core.metrics import (
    erp_dashboard_cache_invalidations_total,
    erp_dashboard_cache_requests_total,
)
from src.infrastructure.database.redis_client import get_redis

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "erp:rpt:v1"


def dashboard_cache_key(clinic_id: UUID, *, anchor: str, period: str) -> str:
    """Stable key for clinic dashboard (day/week/month around anchor date)."""
    return f"{_CACHE_PREFIX}:{clinic_id}:dashboard:{anchor}:{period}"


def owner_dashboard_cache_key(
    clinic_id: UUID,
    *,
    day: str,
    date_from: str,
    date_to: str,
) -> str:
    return f"{_CACHE_PREFIX}:{clinic_id}:owner_dashboard:{day}:{date_from}:{date_to}"


async def get_cached_json(key: str) -> str | None:
    if not settings.erp_dashboard_cache_enabled:
        return None
    try:
        r = await get_redis()
        v = await r.get(key)
        if v is not None:
            erp_dashboard_cache_requests_total.labels(result="hit").inc()
        else:
            erp_dashboard_cache_requests_total.labels(result="miss").inc()
        return v
    except Exception as exc:
        erp_dashboard_cache_requests_total.labels(result="error").inc()
        logger.warning("erp_report_cache_get_failed", extra={"key": key, "error": str(exc)})
        return None


async def set_cached_json(key: str, body: str) -> None:
    if not settings.erp_dashboard_cache_enabled:
        return
    try:
        r = await get_redis()
        await r.setex(key, settings.erp_dashboard_cache_ttl_seconds, body)
    except Exception as exc:
        logger.warning("erp_report_cache_set_failed", extra={"key": key, "error": str(exc)})


async def invalidate_clinic_erp_report_cache(clinic_id: UUID) -> None:
    """Remove all cached report JSON for a clinic (after vitrine refresh)."""
    if not settings.erp_dashboard_cache_enabled:
        return
    pattern = f"{_CACHE_PREFIX}:{clinic_id}:*"
    try:
        r = await get_redis()
        async for k in r.scan_iter(match=pattern):
            await r.delete(k)
        erp_dashboard_cache_invalidations_total.inc()
    except Exception as exc:
        logger.warning(
            "erp_report_cache_invalidate_failed",
            extra={"clinic_id": str(clinic_id), "error": str(exc)},
        )
