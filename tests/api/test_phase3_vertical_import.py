"""Phase 3+: industry_profile, medical vertical gate, CRM import entitlement (ADR-010 stub)."""

from __future__ import annotations

import uuid
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic
from src.domain.entities.crm_import_staging_job import CrmImportStagingJob
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement


@pytest.mark.asyncio
async def test_admin_session_includes_industry_profile(
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/admin/auth/session", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json().get("industry_profile") == "industry_dental"


@pytest.mark.asyncio
async def test_medical_visits_blocked_for_generic_industry(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    _cid = seed_data["clinic_id"]
    cid_uuid = _cid if isinstance(_cid, UUID) else UUID(str(_cid))
    try:
        db_session.add(
            Organization(id=org_id, name="Generic vertical org", industry_profile="industry_generic")
        )
        await db_session.flush()
        clinic = await db_session.get(Clinic, cid_uuid)
        assert clinic is not None
        clinic.organization_id = org_id
        await db_session.commit()

        headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
        patient_id = str(seed_data["patient_id"])
        clinic_id = str(seed_data["clinic_id"])
        r = await client.get(
            f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/visits",
            headers=headers,
        )
        assert r.status_code == 403, r.text
        assert r.json().get("code") == "medical_module_industry_not_dental"
    finally:
        clinic = await db_session.get(Clinic, cid_uuid)
        if clinic is not None:
            clinic.organization_id = None
        await db_session.flush()
        await db_session.execute(delete(Organization).where(Organization.id == org_id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_crm_import_dry_run_requires_entitlement_when_enforced(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    _cid = seed_data["clinic_id"]
    cid_uuid = _cid if isinstance(_cid, UUID) else UUID(str(_cid))
    try:
        db_session.add(Organization(id=org_id, name="Import gate org"))
        await db_session.flush()
        res = await db_session.execute(
            select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
        )
        admin = res.scalar_one()
        admin.organization_id = org_id
        clinic = await db_session.get(Clinic, cid_uuid)
        assert clinic is not None
        clinic.organization_id = org_id
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key="core.base",
                source="test",
            )
        )
        await db_session.commit()

        headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
        r = await client.post(
            "/api/v1/admin/organization/crm-import/dry-run",
            headers=headers,
            json={"source_profile": "csv_contacts_v1", "idempotency_key": "t1"},
        )
        assert r.status_code == 403, r.text
        assert r.json().get("code") == "entitlement_required"

        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key="import.crm_v1",
                source="test",
            )
        )
        await db_session.commit()

        r2 = await client.post(
            "/api/v1/admin/organization/crm-import/dry-run",
            headers=headers,
            json={"source_profile": "csv_contacts_v1", "idempotency_key": "t2"},
        )
        assert r2.status_code == 201, r2.text
        data = r2.json()
        assert data.get("status") == "ingested"
        assert data.get("job_id")

        r3 = await client.post(
            "/api/v1/admin/organization/crm-import/dry-run",
            headers=headers,
            json={"source_profile": "csv_contacts_v1", "idempotency_key": "t2"},
        )
        assert r3.status_code == 200, r3.text
        assert r3.json().get("job_id") == data.get("job_id")
    finally:
        clinic = await db_session.get(Clinic, cid_uuid)
        if clinic is not None:
            clinic.organization_id = None
        res = await db_session.execute(
            select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
        )
        adm = res.scalar_one_or_none()
        if adm is not None:
            adm.organization_id = None
        await db_session.flush()
        await db_session.execute(
            delete(CrmImportStagingJob).where(CrmImportStagingJob.organization_id == org_id)
        )
        await db_session.execute(
            delete(OrganizationEntitlement).where(OrganizationEntitlement.organization_id == org_id)
        )
        await db_session.execute(delete(Organization).where(Organization.id == org_id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_crm_import_rejects_unknown_source_profile(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    _cid = seed_data["clinic_id"]
    cid_uuid = _cid if isinstance(_cid, UUID) else UUID(str(_cid))
    try:
        db_session.add(Organization(id=org_id, name="Import profile org"))
        await db_session.flush()
        res = await db_session.execute(
            select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
        )
        admin = res.scalar_one()
        admin.organization_id = org_id
        clinic = await db_session.get(Clinic, cid_uuid)
        assert clinic is not None
        clinic.organization_id = org_id
        for key in ("core.base", "import.crm_v1"):
            db_session.add(
                OrganizationEntitlement(
                    id=uuid.uuid4(),
                    organization_id=org_id,
                    entitlement_key=key,
                    source="test",
                )
            )
        await db_session.commit()

        headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
        r = await client.post(
            "/api/v1/admin/organization/crm-import/dry-run",
            headers=headers,
            json={"source_profile": "unknown_connector_v9", "idempotency_key": "pf1"},
        )
        assert r.status_code == 400, r.text
        assert r.json().get("code") == "invalid_source_profile"
    finally:
        clinic = await db_session.get(Clinic, cid_uuid)
        if clinic is not None:
            clinic.organization_id = None
        res = await db_session.execute(
            select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
        )
        adm = res.scalar_one_or_none()
        if adm is not None:
            adm.organization_id = None
        await db_session.flush()
        await db_session.execute(
            delete(CrmImportStagingJob).where(CrmImportStagingJob.organization_id == org_id)
        )
        await db_session.execute(
            delete(OrganizationEntitlement).where(OrganizationEntitlement.organization_id == org_id)
        )
        await db_session.execute(delete(Organization).where(Organization.id == org_id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_crm_import_entitlement_enforced_when_org_only_on_clinic(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    """SaaS gate must use clinic.organization_id when admin.organization_id is unset (QA_ARCH)."""
    org_id = uuid.uuid4()
    _cid = seed_data["clinic_id"]
    cid_uuid = _cid if isinstance(_cid, UUID) else UUID(str(_cid))
    try:
        db_session.add(Organization(id=org_id, name="Clinic-only org import"))
        await db_session.flush()
        res = await db_session.execute(
            select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
        )
        admin = res.scalar_one()
        admin.organization_id = None
        clinic = await db_session.get(Clinic, cid_uuid)
        assert clinic is not None
        clinic.organization_id = org_id
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key="core.base",
                source="test",
            )
        )
        await db_session.commit()

        headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
        r = await client.post(
            "/api/v1/admin/organization/crm-import/dry-run",
            headers=headers,
            json={"source_profile": "csv_contacts_v1", "idempotency_key": "clinic_only_1"},
        )
        assert r.status_code == 403, r.text
        assert r.json().get("code") == "entitlement_required"

        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key="import.crm_v1",
                source="test",
            )
        )
        await db_session.commit()

        r2 = await client.post(
            "/api/v1/admin/organization/crm-import/dry-run",
            headers=headers,
            json={"source_profile": "csv_contacts_v1", "idempotency_key": "clinic_only_2"},
        )
        assert r2.status_code == 201, r2.text
    finally:
        clinic = await db_session.get(Clinic, cid_uuid)
        if clinic is not None:
            clinic.organization_id = None
        await db_session.flush()
        await db_session.execute(
            delete(CrmImportStagingJob).where(CrmImportStagingJob.organization_id == org_id)
        )
        await db_session.execute(
            delete(OrganizationEntitlement).where(OrganizationEntitlement.organization_id == org_id)
        )
        await db_session.execute(delete(Organization).where(Organization.id == org_id))
        await db_session.commit()
