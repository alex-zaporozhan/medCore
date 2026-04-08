"""SaaS entitlement gate helpers (Phase 1c)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.organization_entitlement_access import (
    ensure_org_entitlement_keys_for_public_client,
    ensure_org_has_any_entitlement,
    ensure_org_has_any_entitlement_for_organization,
    list_legacy_organizations_without_entitlements,
    org_entitlement_enforcement_state,
    session_entitlement_view,
)
from src.core.config import settings
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement


@pytest.mark.asyncio
async def test_enforcement_off_when_no_org(db_session: AsyncSession):
    enforced, keys = await org_entitlement_enforcement_state(db_session, None)
    assert enforced is False
    assert keys == frozenset()


@pytest.mark.asyncio
async def test_enforcement_off_when_org_has_no_rows(db_session: AsyncSession, seed_data):
    from src.api.v1.routers.admin_auth import hash_password

    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Org SaaS"))
    await db_session.flush()
    clinic_id = seed_data["clinic_id"]
    admin = AdminUser(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        organization_id=org_id,
        email="ent-norows@test.local",
        password_hash=hash_password("x"),
    )
    db_session.add(admin)
    await db_session.commit()

    enforced, keys = await org_entitlement_enforcement_state(db_session, org_id)
    assert enforced is False
    assert keys == frozenset()

    await ensure_org_has_any_entitlement(db_session, admin, "tasks.kanban")


@pytest.mark.asyncio
async def test_enforcement_on_requires_key(db_session: AsyncSession, seed_data):
    from src.api.v1.routers.admin_auth import hash_password

    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Org Paid"))
    await db_session.flush()
    clinic_id = seed_data["clinic_id"]
    admin = AdminUser(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        organization_id=org_id,
        email="ent-paid@test.local",
        password_hash=hash_password("x"),
    )
    db_session.add(admin)
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_id,
            entitlement_key="core.base",
            source="tariff_snapshot",
        )
    )
    await db_session.commit()

    enforced, keys = await org_entitlement_enforcement_state(db_session, org_id)
    assert enforced is True
    assert "core.base" in keys

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        await ensure_org_has_any_entitlement(db_session, admin, "tasks.kanban")
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "entitlement_required"

    await ensure_org_has_any_entitlement(db_session, admin, "core.base")


@pytest.mark.asyncio
async def test_session_entitlement_view_sorted(db_session: AsyncSession, seed_data):
    from src.api.v1.routers.admin_auth import hash_password

    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Org Keys"))
    await db_session.flush()
    clinic_id = seed_data["clinic_id"]
    admin = AdminUser(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        organization_id=org_id,
        email="ent-view@test.local",
        password_hash=hash_password("x"),
    )
    db_session.add(admin)
    for k in ("zebra", "alpha"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=k,
                source="tariff_snapshot",
            )
        )
    await db_session.commit()

    enforced, keys = await session_entitlement_view(db_session, admin)
    assert enforced is True
    assert keys == ["alpha", "zebra"]


@pytest.mark.asyncio
async def test_enforcement_mode_strict_blocks_legacy_org_without_rows(
    db_session: AsyncSession,
    seed_data: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    from src.api.v1.routers.admin_auth import hash_password
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "entitlement_enforcement_mode", "strict")
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Strict org"))
    await db_session.flush()
    admin = AdminUser(
        id=uuid.uuid4(),
        clinic_id=seed_data["clinic_id"],
        organization_id=org_id,
        email="strict@test.local",
        password_hash=hash_password("x"),
    )
    db_session.add(admin)
    await db_session.commit()

    enforced, keys = await org_entitlement_enforcement_state(db_session, org_id)
    assert enforced is True
    assert keys == frozenset()

    with pytest.raises(HTTPException) as ei:
        await ensure_org_has_any_entitlement(db_session, admin, "tasks.kanban")
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "entitlement_required"


@pytest.mark.asyncio
async def test_auto_mode_strict_cohort_enforces_specific_org_only(
    db_session: AsyncSession,
    seed_data: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    from src.api.v1.routers.admin_auth import hash_password
    from fastapi import HTTPException

    strict_org = uuid.uuid4()
    legacy_org = uuid.uuid4()
    db_session.add(Organization(id=strict_org, name="Strict cohort"))
    db_session.add(Organization(id=legacy_org, name="Legacy cohort"))
    await db_session.flush()
    strict_admin = AdminUser(
        id=uuid.uuid4(),
        clinic_id=seed_data["clinic_id"],
        organization_id=strict_org,
        email="strict-cohort@test.local",
        password_hash=hash_password("x"),
    )
    legacy_admin = AdminUser(
        id=uuid.uuid4(),
        clinic_id=seed_data["clinic_id"],
        organization_id=legacy_org,
        email="legacy-cohort@test.local",
        password_hash=hash_password("x"),
    )
    db_session.add(strict_admin)
    db_session.add(legacy_admin)
    await db_session.commit()

    monkeypatch.setattr(settings, "entitlement_enforcement_mode", "auto")
    monkeypatch.setattr(settings, "entitlement_enforcement_strict_org_ids", f"{strict_org}")

    with pytest.raises(HTTPException):
        await ensure_org_has_any_entitlement(db_session, strict_admin, "tasks.kanban")
    await ensure_org_has_any_entitlement(db_session, legacy_admin, "tasks.kanban")


@pytest.mark.asyncio
async def test_list_legacy_organizations_without_entitlements(db_session: AsyncSession):
    org_without = uuid.uuid4()
    org_with = uuid.uuid4()
    db_session.add(Organization(id=org_without, name="No entitlements"))
    db_session.add(Organization(id=org_with, name="Has entitlements"))
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_with,
            entitlement_key="core.base",
            source="tariff_snapshot",
        )
    )
    await db_session.commit()

    ids = await list_legacy_organizations_without_entitlements(db_session, limit=100)
    assert org_without in ids
    assert org_with not in ids


@pytest.mark.asyncio
async def test_legacy_mode_skips_entitlement_gate_even_with_db_rows(
    db_session: AsyncSession,
    seed_data: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    """WP3.2: explicit legacy cohort must not be blocked by SaaS keys when mode=legacy."""
    from src.api.v1.routers.admin_auth import hash_password

    monkeypatch.setattr(settings, "entitlement_enforcement_mode", "legacy")
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Legacy SaaS rows"))
    await db_session.flush()
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_id,
            entitlement_key="core.base",
            source="tariff_snapshot",
        )
    )
    admin = AdminUser(
        id=uuid.uuid4(),
        clinic_id=seed_data["clinic_id"],
        organization_id=org_id,
        email="legacy-mode@test.local",
        password_hash=hash_password("x"),
    )
    db_session.add(admin)
    await db_session.commit()

    enforced, _ = await org_entitlement_enforcement_state(db_session, org_id)
    assert enforced is False
    await ensure_org_has_any_entitlement(db_session, admin, "tasks.kanban")


@pytest.mark.asyncio
async def test_public_client_enforcement_denies_without_required_key(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """WP3.2 / WP3.3: embed/public gate must 403 when SaaS enforcement is on but key missing."""
    from fastapi import HTTPException

    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Public gate org"))
    await db_session.flush()
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_id,
            entitlement_key="core.base",
            source="tariff_snapshot",
        )
    )
    await db_session.commit()

    monkeypatch.setattr(settings, "entitlement_enforcement_mode", "strict")

    with pytest.raises(HTTPException) as ei:
        await ensure_org_entitlement_keys_for_public_client(
            db_session,
            org_id,
            "omni.embed.bundle",
        )
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "entitlement_required"


@pytest.mark.asyncio
async def test_ensure_org_has_any_entitlement_for_organization_respects_explicit_org(
    db_session: AsyncSession,
    seed_data: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    """Bypass attempt: admin linked to clinic A must not unlock org B without keys."""
    from src.api.v1.routers.admin_auth import hash_password
    from fastapi import HTTPException

    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    db_session.add(Organization(id=org_a, name="Org A"))
    db_session.add(Organization(id=org_b, name="Org B paid"))
    await db_session.flush()
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_b,
            entitlement_key="core.base",
            source="tariff_snapshot",
        )
    )
    admin = AdminUser(
        id=uuid.uuid4(),
        clinic_id=seed_data["clinic_id"],
        organization_id=org_a,
        email="explicit-org@test.local",
        password_hash=hash_password("x"),
    )
    db_session.add(admin)
    await db_session.commit()

    monkeypatch.setattr(settings, "entitlement_enforcement_mode", "auto")

    with pytest.raises(HTTPException) as ei:
        await ensure_org_has_any_entitlement_for_organization(
            db_session,
            org_b,
            "tasks.kanban",
        )
    assert ei.value.status_code == 403

    await ensure_org_has_any_entitlement_for_organization(db_session, org_b, "core.base")
