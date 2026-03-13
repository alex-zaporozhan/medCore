"""Security tests: personal data isolation (SEC-P1–P4).

Admin cannot access other clinic's patients/reports; error messages do not leak PD.
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.domain.entities.clinic import Clinic
from src.domain.entities.patient import Patient
from src.infrastructure.database import base as db_base


@pytest.mark.security
@pytest.mark.regression_pd
@pytest.mark.asyncio
async def test_sec_p1_admin_cannot_access_foreign_clinic_patient(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """SEC-P1: Admin of clinic A requesting patient/insight for another clinic gets 404 or 403."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id_a = seed_data["clinic_id"]

    # Create second clinic and patient so we have a "foreign" patient_id
    other_clinic_id = uuid.uuid4()
    other_patient_id = uuid.uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(Clinic(id=other_clinic_id, name="Other Clinic", prepayment_amount=0))
        session.add(
            Patient(
                id=other_patient_id,
                clinic_id=other_clinic_id,
                phone="+79001112233",
                full_name="Other Patient",
            )
        )
        await session.commit()

    # Admin of clinic A requests AI insight for patient of clinic B
    r = await client.get(
        f"/api/v1/admin/patients/{other_patient_id}/ai-insight",
        params={"clinic_id": str(clinic_id_a)},
        headers=headers,
    )
    assert r.status_code in (403, 404), r.text


@pytest.mark.security
@pytest.mark.regression_pd
@pytest.mark.asyncio
async def test_sec_p2_error_response_does_not_leak_pd(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """SEC-P2: 404/error response must not contain phone, email, or full name from seed_data."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    non_existent_id = uuid.uuid4()
    clinic_id = seed_data["clinic_id"]

    r = await client.get(
        f"/api/v1/admin/patients/{non_existent_id}/ai-insight",
        params={"clinic_id": str(clinic_id)},
        headers=headers,
    )
    assert r.status_code in (403, 404), r.text
    body = r.json()
    detail = body.get("detail") or ""
    if isinstance(detail, list):
        detail = " ".join(str(x) for x in detail)
    detail_lower = detail.lower()
    # Seed patient/doctor data must not appear in error message
    assert "79001234567" not in detail_lower and "+79001234567" not in detail
    assert "test patient" not in detail_lower
    assert "test doctor" not in detail_lower
    assert "admin@test-clinic" not in detail_lower


@pytest.mark.security
@pytest.mark.regression_pd
@pytest.mark.asyncio
async def test_sec_p3_admin_reports_foreign_clinic_returns_404(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """SEC-P3: Admin of clinic A requesting reports with clinic_id=B gets 404 or empty without B's data."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    other_clinic_id = uuid.uuid4()
    today = date.today().isoformat()

    r = await client.get(
        f"/api/v1/admin/clinics/{other_clinic_id}/reports/dashboard",
        params={"date": today, "period": "day"},
        headers=headers,
    )
    assert r.status_code == 404, r.text


@pytest.mark.security
@pytest.mark.regression_pd
@pytest.mark.asyncio
async def test_sec_p4_admin_cannot_get_another_clinic_patient_ai(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """SEC-P4: Admin cannot get AI insight for patient belonging to another clinic."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    # Create foreign clinic and patient
    other_clinic_id = uuid.uuid4()
    foreign_patient_id = uuid.uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(Clinic(id=other_clinic_id, name="Foreign", prepayment_amount=0))
        session.add(
            Patient(
                id=foreign_patient_id,
                clinic_id=other_clinic_id,
                phone="+79009998877",
                full_name="Foreign Patient",
            )
        )
        await session.commit()

    r = await client.get(
        f"/api/v1/admin/patients/{foreign_patient_id}/ai-insight",
        params={"clinic_id": str(seed_data["clinic_id"])},
        headers=headers,
    )
    assert r.status_code in (403, 404), r.text
