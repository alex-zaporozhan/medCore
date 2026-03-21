"""Shared read-path for ERP L2 vitrines (aggregate vs raw fallback)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Awaitable, Callable, TypeVar
from uuid import UUID

from src.core.metrics import (
    erp_aggregate_empty_trusted_total,
    erp_aggregate_lag_seconds,
    erp_aggregate_read_fallback_total,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def resolve_erp_aggregate_rows(
    *,
    use_aggregate: bool,
    fetch_agg: Callable[[], Awaitable[list[T]]],
    max_updated_for_range: Callable[[], Awaitable[datetime | None]],
    fetch_raw: Callable[[], Awaitable[list[T]]],
    report_type: str,
    aggregate_kind: str,
    stale_limit_seconds: int,
    now: datetime,
    clinic_id: UUID,
    stale_log_event: str,
    empty_log_event: str,
    trust_empty_if: Callable[[], Awaitable[bool]] | None = None,
) -> tuple[list[T], str | None, datetime | None, bool | None]:
    """Return rows and metadata; mirrors revenue-by-period L2 behavior."""
    if not use_aggregate:
        rows = await fetch_raw()
        return rows, "raw", None, None

    agg_rows = await fetch_agg()
    mx_range = await max_updated_for_range()
    stale_limit = max(0, stale_limit_seconds)

    if agg_rows:
        is_stale = mx_range is None
        if mx_range is not None:
            lag = max(0.0, (now - mx_range).total_seconds())
            erp_aggregate_lag_seconds.labels(aggregate_kind=aggregate_kind).observe(lag)
            is_stale = lag > stale_limit
        if is_stale:
            erp_aggregate_read_fallback_total.labels(
                report_type=report_type,
                reason="stale_range",
            ).inc()
            logger.warning(
                stale_log_event,
                extra={
                    "clinic_id": str(clinic_id),
                    "report": report_type,
                    "aggregate_max_updated_at": mx_range.isoformat() if mx_range else None,
                },
            )
            rows = await fetch_raw()
            return rows, "raw", mx_range, True
        return agg_rows, "aggregate", mx_range, False

    if trust_empty_if is not None:
        try:
            if await trust_empty_if():
                erp_aggregate_empty_trusted_total.labels(aggregate_kind=aggregate_kind).inc()
                logger.info(
                    "erp_aggregate_empty_trusted_by_watermark",
                    extra={
                        "clinic_id": str(clinic_id),
                        "report": report_type,
                        "aggregate_kind": aggregate_kind,
                    },
                )
                return [], "aggregate", mx_range, False
        except Exception:  # noqa: BLE001
            logger.exception(
                "trust_empty_if failed",
                extra={"clinic_id": str(clinic_id), "report": report_type},
            )

    erp_aggregate_read_fallback_total.labels(
        report_type=report_type,
        reason="empty_vitrine",
    ).inc()
    logger.warning(
        empty_log_event,
        extra={"clinic_id": str(clinic_id), "report": report_type},
    )
    rows = await fetch_raw()
    return rows, "raw", mx_range, None
