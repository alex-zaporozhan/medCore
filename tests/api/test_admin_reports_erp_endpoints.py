from datetime import date, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_erp_revenue_by_period_requires_auth(client: AsyncClient) -> None:
    clinic_id = uuid4()
    resp = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/reports/revenue-by-period",
        params={"date_from": date.today().isoformat(), "date_to": date.today().isoformat()},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_erp_revenue_by_period_invalid_period_returns_400(
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    clinic_id = admin_auth["clinic_id"]
    today = date.today()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    resp = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/reports/revenue-by-period",
        headers=headers,
        params={"date_from": (today + timedelta(days=1)).isoformat(), "date_to": today.isoformat()},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_erp_revenue_by_period_rejects_too_long_range(
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    clinic_id = admin_auth["clinic_id"]
    today = date.today()
    start = today - timedelta(days=400)
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    resp = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/reports/revenue-by-period",
        headers=headers,
        params={"date_from": start.isoformat(), "date_to": today.isoformat()},
    )
    assert resp.status_code == 400
    assert "366" in resp.json().get("detail", "")
