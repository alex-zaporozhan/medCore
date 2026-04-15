"""Manual ERP vitrine POST refresh persists audit row (QA_ARCH A13)."""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from src.domain.entities.erp_manual_refresh_audit import ErpAggregateManualRefreshAudit
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_post_refresh_erp_aggregates_creates_audit_row(
    client: AsyncClient,
    init_db,
    seed_data,
) -> None:
    clinic_id = seed_data["clinic_id"]
    admin_id = seed_data["admin_id"]
    r = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": seed_data["admin_email"], "password": "password123"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    today = date.today()
    resp = await client.post(
        f"/api/v1/admin/clinics/{clinic_id}/reports/erp-aggregates/refresh",
        headers={"Authorization": f"Bearer {token}"},
        json={"kind": "visit_revenue", "date_from": today.isoformat(), "date_to": today.isoformat()},
    )
    assert resp.status_code == 200, resp.text

    async with db_base.AsyncSessionLocal() as session:
        stmt = select(func.count()).select_from(ErpAggregateManualRefreshAudit).where(
            ErpAggregateManualRefreshAudit.clinic_id == clinic_id,
            ErpAggregateManualRefreshAudit.admin_user_id == admin_id,
            ErpAggregateManualRefreshAudit.scope_kind == "visit_revenue",
        )
        n = (await session.execute(stmt)).scalar_one()
        assert n == 1
