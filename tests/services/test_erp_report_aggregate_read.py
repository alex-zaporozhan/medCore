"""resolve_erp_aggregate_rows: watermark trust_empty_if (QA_ARCH A5 read path)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.services.erp_report_aggregate_read import resolve_erp_aggregate_rows


@pytest.mark.asyncio
async def test_trust_empty_skips_raw_when_true() -> None:
    clinic_id = uuid4()
    now = datetime.now(timezone.utc)
    fetch_raw = AsyncMock(side_effect=AssertionError("fetch_raw must not run"))

    rows, src, mx, stale = await resolve_erp_aggregate_rows(
        use_aggregate=True,
        fetch_agg=AsyncMock(return_value=[]),
        max_updated_for_range=AsyncMock(return_value=now),
        fetch_raw=fetch_raw,
        report_type="revenue-by-period",
        aggregate_kind="visit_revenue",
        stale_limit_seconds=7200,
        now=now,
        clinic_id=clinic_id,
        stale_log_event="stale",
        empty_log_event="empty",
        trust_empty_if=AsyncMock(return_value=True),
    )
    assert rows == []
    assert src == "aggregate"
    assert stale is False
    fetch_raw.assert_not_called()


@pytest.mark.asyncio
async def test_trust_empty_false_falls_back_to_raw() -> None:
    clinic_id = uuid4()
    now = datetime.now(timezone.utc)
    fetch_raw = AsyncMock(return_value=[object()])

    rows, src, mx, stale = await resolve_erp_aggregate_rows(
        use_aggregate=True,
        fetch_agg=AsyncMock(return_value=[]),
        max_updated_for_range=AsyncMock(return_value=now),
        fetch_raw=fetch_raw,
        report_type="revenue-by-period",
        aggregate_kind="visit_revenue",
        stale_limit_seconds=7200,
        now=now,
        clinic_id=clinic_id,
        stale_log_event="stale",
        empty_log_event="empty",
        trust_empty_if=AsyncMock(return_value=False),
    )
    assert rows
    assert src == "raw"
    fetch_raw.assert_awaited_once()
