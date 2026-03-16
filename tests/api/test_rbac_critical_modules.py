"""RBAC: 401/403 for critical modules (ERP, CRM, Loyalty, Paperless, Marketing Attribution, Tasks).

Covers that endpoints protected by require_permissions return 401 without auth
and 403 with invalid token. Add new routes here when adding protected endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient

from src.main import app


@pytest.fixture(scope="module", autouse=True)
def ensure_test_db_engine():
    """Ensure DB engine is initialized when running only this module (TESTING=1 defers init)."""
    from src.infrastructure.database import base as db_base
    if getattr(db_base, "init_engine_for_testing", None):
        db_base.init_engine_for_testing()

# Endpoints that use require_permissions; clinic_id placeholder for path params
RBAC_CRITICAL_ENDPOINTS = [
    # Finance (view_finance / manage_finance)
    ("GET", "/api/v1/admin/clinics/{clinic_id}/finance/cashboxes"),
    # Payroll (view_payroll / manage_payroll)
    ("GET", "/api/v1/admin/clinics/{clinic_id}/payroll/policies"),
    # Inventory (view_inventory)
    ("GET", "/api/v1/admin/clinics/{clinic_id}/inventory/transactions"),
    # CRM (view_crm)
    ("GET", "/api/v1/admin/crm/leads"),
    # Loyalty (view_loyalty)
    ("GET", "/api/v1/admin/loyalty/policy"),
    # Paperless / Forms (view_forms)
    ("GET", "/api/v1/admin/forms/templates"),
    # Marketing Attribution (view_marketing_analytics)
    ("GET", "/api/v1/admin/attribution/summary"),
    ("GET", "/api/v1/admin/attribution/drill-down"),
    # Tasks (view_tasks)
    ("GET", "/api/v1/admin/tasks"),
]


def _path_with_placeholder(path: str, clinic_id: str | None = None) -> str:
    if "{clinic_id}" in path and clinic_id:
        return path.format(clinic_id=clinic_id)
    if "{clinic_id}" in path:
        return path.format(clinic_id=uuid.uuid4())
    return path


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", RBAC_CRITICAL_ENDPOINTS)
async def test_rbac_critical_module_401_without_auth(method: str, path: str):
    """Without Authorization header, protected endpoints return 401 or 403."""
    path = _path_with_placeholder(path)
    async with AsyncClient(app=app, base_url="http://test") as client:
        if method == "GET":
            resp = await client.get(path)
        else:
            resp = await client.request(method, path)
        assert resp.status_code in (401, 403), (
            f"{method} {path} expected 401 or 403 without auth, got {resp.status_code}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", RBAC_CRITICAL_ENDPOINTS)
async def test_rbac_critical_module_403_invalid_token(method: str, path: str):
    """With invalid Bearer token, protected endpoints return 401 or 403."""
    path = _path_with_placeholder(path)
    async with AsyncClient(app=app, base_url="http://test") as client:
        headers = {"Authorization": "Bearer invalid-token"}
        if method == "GET":
            resp = await client.get(path, headers=headers)
        else:
            resp = await client.request(method, path, headers=headers)
        assert resp.status_code in (401, 403), (
            f"{method} {path} expected 401 or 403 with invalid token, got {resp.status_code}"
        )
