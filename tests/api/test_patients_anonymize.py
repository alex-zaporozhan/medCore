"""LEAD B2: POST /patients/{id}/anonymize scrubs PII and soft-deletes."""

import pytest
from httpx import AsyncClient

from sqlalchemy import select

from src.domain.entities.patient import Patient
from src.domain.entities.rbac_audit_log import RbacAuditLog
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_anonymize_patient_scrubs_pii_and_sets_deleted(
    client: AsyncClient,
    seed_data: dict,
    admin_auth: dict,
):
    pid = seed_data["patient_id"]
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.post(f"/api/v1/patients/{pid}/anonymize", headers=headers)
    assert r.status_code == 204, r.text

    async with db_base.AsyncSessionLocal() as session:
        row = await session.get(Patient, pid)
        assert row is not None
        assert row.deleted_at is not None
        assert row.full_name is None
        assert row.email is None
        assert row.phone == f"a{pid.hex[:19]}"
        ar = await session.execute(
            select(RbacAuditLog).where(
                RbacAuditLog.entity_type == "patient",
                RbacAuditLog.entity_id == str(pid),
                RbacAuditLog.action == "patient_pii_anonymized",
            )
        )
        audit = ar.scalar_one_or_none()
        assert audit is not None
        assert audit.after_payload.get("anonymized") is True


@pytest.mark.asyncio
async def test_anonymize_patient_404_other_clinic(
    client: AsyncClient,
    seed_data: dict,
    admin_auth: dict,
    init_db,
):
    """Patient in another clinic must not be anonymized from this admin JWT."""
    from src.domain.entities.clinic import Clinic
    from uuid import uuid4

    other_clinic = uuid4()
    other_patient = uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(
            Clinic(
                id=other_clinic,
                name="Other Clinic",
                clinic_slug=f"other-{other_clinic.hex[:12]}",
            )
        )
        session.add(
            Patient(
                id=other_patient,
                clinic_id=other_clinic,
                phone="+79990000001",
                full_name="Foreign",
            )
        )
        await session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.post(f"/api/v1/patients/{other_patient}/anonymize", headers=headers)
    assert r.status_code in (403, 404)

    async with db_base.AsyncSessionLocal() as session:
        foreign = await session.get(Patient, other_patient)
        assert foreign is not None
        assert foreign.full_name == "Foreign"
