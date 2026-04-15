"""ERP L2: sample parity helper (raw vs vitrine sample)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.application.services.erp_parity_sample_service import (
    compare_visit_revenue_totals,
    pick_clinic_for_day,
)
from src.infrastructure.database import base as db_base


def test_pick_clinic_for_day_empty() -> None:
    assert pick_clinic_for_day([], date(2026, 1, 1)) is None


def test_pick_clinic_for_day_stable() -> None:
    ids = sorted([uuid4() for _ in range(5)], key=str)
    d = date(2026, 3, 21)
    assert pick_clinic_for_day(ids, d) == pick_clinic_for_day(ids, d)
    assert pick_clinic_for_day(ids, d) in ids


@pytest.mark.asyncio
async def test_compare_visit_revenue_totals_zero_without_transactions(init_db, seed_data) -> None:
    empty_day = seed_data["date"] + timedelta(days=(uuid4().int % 365) + 365)
    async with db_base.AsyncSessionLocal() as session:
        s_raw, s_agg = await compare_visit_revenue_totals(
            session,
            clinic_id=seed_data["clinic_id"],
            date_from=empty_day,
            date_to=empty_day,
        )
    assert s_raw == Decimal("0")
    assert s_agg == Decimal("0")
