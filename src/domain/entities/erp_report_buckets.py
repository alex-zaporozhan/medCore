"""Stable UUID buckets for NULL keys in ERP report pre-aggregate PKs (Engine L2)."""

from __future__ import annotations

import uuid
from datetime import date

# NULL booking_id from raw reports → stable bucket for composite PKs.
NULL_BOOKING_BUCKET = uuid.UUID("00000000-0000-0000-0000-000000000000")
NULL_TRAFFIC_SOURCE_BUCKET = uuid.UUID("00000000-0000-0000-0000-000000000001")
NULL_CAMPAIGN_BUCKET = uuid.UUID("00000000-0000-0000-0000-000000000002")

# Sentinel dates for nullable salary period bounds in aggregate PK (mapped back to None in API).
NULL_PERIOD_SENTINEL_START = date(1, 1, 1)
NULL_PERIOD_SENTINEL_END = date(9999, 12, 31)


def payroll_period_keys_for_storage(
    period_start: date | None, period_end: date | None
) -> tuple[date, date]:
    return (
        period_start if period_start is not None else NULL_PERIOD_SENTINEL_START,
        period_end if period_end is not None else NULL_PERIOD_SENTINEL_END,
    )


def payroll_period_from_storage(
    period_start_key: date,
    period_end_key: date,
    *,
    period_start_is_null: bool,
    period_end_is_null: bool,
) -> tuple[date | None, date | None]:
    """Decode API values; flags disambiguate real dates that equal sentinel storage values."""
    return (
        None if period_start_is_null else period_start_key,
        None if period_end_is_null else period_end_key,
    )
