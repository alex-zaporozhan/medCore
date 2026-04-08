"""HTTP-level checks for Phase 1c entitlement gates (QA_ARCH)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from src.domain.entities.admin_user import AdminUser
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement


@pytest.fixture(autouse=True)
async def _restore_seed_admin_after_entitlement_case(db_session, seed_data):
    """Не оставлять seed-админа привязанным к org из SaaS-тестов (иначе ломаются session/tasks)."""
    yield
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one_or_none()
    if admin is None:
        return
    oid = admin.organization_id
    admin.organization_id = None
    if oid is not None:
        await db_session.execute(
            delete(OrganizationEntitlement).where(OrganizationEntitlement.organization_id == oid)
        )
        await db_session.execute(delete(Organization).where(Organization.id == oid))
    await db_session.commit()


def _http_error_code(payload: dict) -> str | None:
    """FastAPI: либо верхний уровень, либо `detail` — dict."""
    d = payload.get("detail")
    if isinstance(d, dict):
        c = d.get("code")
        if c is not None:
            return str(c).lower()
    c = payload.get("code")
    return str(c).lower() if c is not None else None


@pytest.mark.asyncio
async def test_admin_tasks_403_when_org_enforced_without_kanban(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Entitlement QA Org"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_id,
            entitlement_key="core.base",
            source="tariff_snapshot",
        )
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/admin/tasks", headers=headers)
    assert r.status_code == 403, r.text
    assert _http_error_code(r.json()) == "entitlement_required"


@pytest.mark.asyncio
async def test_admin_tasks_200_when_org_has_kanban_entitlement(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Entitlement QA Org 2"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    for key in ("core.base", "tasks.kanban"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="tariff_snapshot",
            )
        )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/admin/tasks", headers=headers)
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_admin_session_shows_enforcement_when_org_has_entitlements(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Entitlement QA Org 3"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_id,
            entitlement_key="core.base",
            source="tariff_snapshot",
        )
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/admin/auth/session", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("entitlement_enforced") is True
    assert "core.base" in (data.get("entitlement_keys") or [])


@pytest.mark.asyncio
async def test_lead_logs_not_gated_by_crm_entitlement(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    """Операционный лог лидов omni не должен требовать SKU CRM (риск блокировки без воронки)."""
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Entitlement QA Org 4"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_id,
            entitlement_key="core.base",
            source="tariff_snapshot",
        )
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        "/api/v1/admin/lead-logs",
        headers=headers,
        params={"day": "2024-06-01"},
    )
    assert r.status_code == 200, r.text
