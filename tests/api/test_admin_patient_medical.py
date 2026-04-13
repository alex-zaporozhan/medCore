from __future__ import annotations

from datetime import date

import pytest
import uuid
from sqlalchemy import select

from src.domain.entities.patient_medical_file import PatientMedicalFile
from src.domain.entities.patient import Patient
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_admin_medical_visits_crud_minimal(client, admin_auth, seed_data):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    patient_id = str(seed_data["patient_id"])

    # list empty
    r0 = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/visits",
        headers=headers,
    )
    assert r0.status_code == 200, (
        f"Expected 200 for medical visits list (seed owner has patients.medical.*); got {r0.status_code}: {r0.text}"
    )

    c = await client.post(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/visits",
        headers=headers,
        json={"visit_date": date.today().isoformat(), "notes_md": "Test visit"},
    )
    assert c.status_code == 201, c.text
    v = c.json()
    assert v["patient_id"] == patient_id
    assert v["clinic_id"] == clinic_id

    r1 = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/visits",
        headers=headers,
    )
    assert r1.status_code == 200, r1.text
    assert any(x["id"] == v["id"] for x in r1.json())

    r_limit = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/visits",
        headers=headers,
        params={"limit": 1},
    )
    assert r_limit.status_code == 200, r_limit.text
    assert len(r_limit.json()) <= 1

    bad = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/visits",
        headers=headers,
        params={"limit": 99999},
    )
    assert bad.status_code == 422, bad.text


@pytest.mark.asyncio
async def test_admin_medical_diagnoses_create_and_list(client, admin_auth, seed_data):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    patient_id = str(seed_data["patient_id"])

    r0 = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/diagnoses",
        headers=headers,
    )
    assert r0.status_code == 200, (
        f"Expected 200 for diagnoses list (seed owner); got {r0.status_code}: {r0.text}"
    )

    c = await client.post(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/diagnoses",
        headers=headers,
        json={
            "diagnosis_date": date.today().isoformat(),
            "title": "Caries",
            "description": "MVP",
        },
    )
    assert c.status_code == 201, c.text

    r1 = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/diagnoses",
        headers=headers,
    )
    assert r1.status_code == 200, r1.text
    assert any(x["title"] == "Caries" for x in r1.json())

    bad = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/diagnoses",
        headers=headers,
        params={"limit": 6000},
    )
    assert bad.status_code == 422, bad.text


@pytest.mark.asyncio
async def test_admin_medical_files_list_limit_validation(client, admin_auth, seed_data):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    patient_id = str(seed_data["patient_id"])
    bad = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/files",
        headers=headers,
        params={"limit": 6000},
    )
    assert bad.status_code == 422, bad.text


@pytest.mark.asyncio
async def test_admin_medical_file_download_token_and_stream_contract(client, admin_auth, seed_data):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    patient_id = str(seed_data["patient_id"])

    # Ensure patient exists in clinic (seed should, but keep test self-contained)
    async with db_base.AsyncSessionLocal() as session:
        p = await session.execute(select(Patient).where(Patient.id == uuid.UUID(patient_id)))
        assert p.scalar_one_or_none() is not None

        file_id = uuid.uuid4()
        session.add(
            PatientMedicalFile(
                id=file_id,
                clinic_id=uuid.UUID(clinic_id),
                patient_id=uuid.UUID(patient_id),
                visit_id=None,
                s3_key=f"medical/test/{file_id}.pdf",
                file_name="test.pdf",
                content_type="application/pdf",
                size_bytes=123,
                sha256=None,
                uploaded_by_admin_id=uuid.UUID(admin_auth["admin_id"]),
            )
        )
        await session.commit()

    # Old presign endpoint is gone (no direct links allowed)
    old = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/files/{file_id}:download",
        headers=headers,
    )
    assert old.status_code == 410, old.text

    tok = await client.post(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/files/{file_id}:download-token",
        headers=headers,
        json={},
    )
    assert tok.status_code == 200, (
        f"Expected 200 for download-token (seed owner); got {tok.status_code}: {tok.text}"
    )
    token = tok.json()["token"]

    # Stream may fail if S3 not configured in test env; that's acceptable. Contract should be non-2xx only for storage.
    stream = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/files/{file_id}:stream?token={token}",
        headers=headers,
    )
    assert stream.status_code in (200, 206, 503), stream.text

    # Reusing token must fail (one-time).
    stream2 = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/medical/files/{file_id}:stream?token={token}",
        headers=headers,
    )
    assert stream2.status_code in (410, 503), stream2.text

