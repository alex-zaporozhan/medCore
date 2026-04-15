"""Patient delete endpoint: soft-delete within current clinic."""

import pytest
from httpx import AsyncClient

from src.domain.entities.patient import Patient
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_delete_patient_sets_deleted_at(
    client: AsyncClient,
    seed_data: dict,
    admin_auth: dict,
):
    pid = seed_data["patient_id"]
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.delete(f"/api/v1/patients/{pid}", headers=headers)
    assert r.status_code == 204, r.text

    async with db_base.AsyncSessionLocal() as session:
        row = await session.get(Patient, pid)
        assert row is not None
        assert row.deleted_at is not None
        # Current implementation is soft-delete only (PII fields remain unchanged).
        assert row.full_name is not None
        assert row.phone is not None


@pytest.mark.asyncio
async def test_delete_patient_404_other_clinic(
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
    r = await client.delete(f"/api/v1/patients/{other_patient}", headers=headers)
    assert r.status_code in (403, 404)

    async with db_base.AsyncSessionLocal() as session:
        foreign = await session.get(Patient, other_patient)
        assert foreign is not None
        assert foreign.full_name == "Foreign"
