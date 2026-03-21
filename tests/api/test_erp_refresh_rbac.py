"""RBAC for unified ERP aggregate refresh (QA: attribution contour)."""

import pytest
from httpx import AsyncClient

from src.api.v1.dependencies import get_request_context
from src.core.context import RequestContext
from src.main import app


@pytest.mark.asyncio
async def test_post_refresh_attribution_requires_attribution_permission(
    client: AsyncClient,
    init_db,
    seed_data,
) -> None:
    clinic_id = seed_data["clinic_id"]
    admin_id = seed_data["admin_id"]

    async def fake_ctx_erp_only() -> RequestContext:
        return RequestContext(
            clinic_id=clinic_id,
            user_id=admin_id,
            user_type="admin",
            permissions={"erp.owner_reports.read"},
            roles=set(),
        )

    app.dependency_overrides[get_request_context] = fake_ctx_erp_only
    try:
        r = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": "admin@test-clinic.local", "password": "password123"},
        )
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            f"/api/v1/admin/clinics/{clinic_id}/reports/erp-aggregates/refresh",
            headers=headers,
            json={"kind": "attribution"},
        )
        assert resp.status_code == 403
        assert "attribution.reports.read" in resp.json().get("detail", "")
    finally:
        app.dependency_overrides.pop(get_request_context, None)


@pytest.mark.asyncio
async def test_post_refresh_all_requires_attribution_permission(
    client: AsyncClient,
    init_db,
    seed_data,
) -> None:
    clinic_id = seed_data["clinic_id"]
    admin_id = seed_data["admin_id"]

    async def fake_ctx_erp_only() -> RequestContext:
        return RequestContext(
            clinic_id=clinic_id,
            user_id=admin_id,
            user_type="admin",
            permissions={"erp.owner_reports.read"},
            roles=set(),
        )

    app.dependency_overrides[get_request_context] = fake_ctx_erp_only
    try:
        r = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": "admin@test-clinic.local", "password": "password123"},
        )
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            f"/api/v1/admin/clinics/{clinic_id}/reports/erp-aggregates/refresh",
            headers=headers,
            json={"kind": "all"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_request_context, None)
