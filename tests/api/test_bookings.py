"""Smoke test: POST /api/v1/patient/bookings."""

import uuid
from datetime import datetime, time, timedelta

import pytest
from httpx import AsyncClient

from src.core.config import settings
from src.core.security import create_access_token


@pytest.mark.asyncio
async def test_create_patient_booking(client: AsyncClient, seed_data: dict, patient_auth: dict):
    """POST /api/v1/patient/bookings with patient token and body returns 201 with id, status."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]
    headers = {"Authorization": f"Bearer {patient_auth['access_token']}"}
    # Use a slot time from working hours (e.g. 10:00)
    response = await client.post(
        "/api/v1/patient/bookings",
        json={
            "clinic_id": str(clinic_id),
            "doctor_id": str(doctor_id),
            "service_id": str(service_id),
            "appointment_date": day.isoformat(),
            "appointment_time": "10:00:00",
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "status" in data
    assert data.get("status") == "pending"


@pytest.mark.asyncio
async def test_create_patient_booking_clinic_mismatch_returns_400(
    client: AsyncClient, seed_data: dict, patient_auth: dict
):
    """Body clinic_id must match authenticated patient's clinic."""
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]
    headers = {"Authorization": f"Bearer {patient_auth['access_token']}"}
    other_clinic = uuid.uuid4()
    response = await client.post(
        "/api/v1/patient/bookings",
        json={
            "clinic_id": str(other_clinic),
            "doctor_id": str(doctor_id),
            "service_id": str(service_id),
            "appointment_date": day.isoformat(),
            "appointment_time": "10:00:00",
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json().get("code") == "clinic_mismatch"


@pytest.mark.asyncio
async def test_patient_booking_rejects_jwt_wrong_audience_when_strict(
    client: AsyncClient, seed_data: dict, patient_auth: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """1a-E6 / QA_ARCH: patient token with admin audience must not authorize patient routes."""
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", False)
    token = create_access_token(
        {"role": "patient", "sub": str(patient_auth["patient_id"])},
        expires_delta=timedelta(minutes=5),
        audience=settings.jwt_audience_admin,
    )
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]
    response = await client.post(
        "/api/v1/patient/bookings",
        json={
            "clinic_id": str(clinic_id),
            "doctor_id": str(doctor_id),
            "service_id": str(service_id),
            "appointment_date": day.isoformat(),
            "appointment_time": "10:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json().get("code") == "invalid_token_audience"


@pytest.mark.asyncio
async def test_patient_can_rebook_same_slot_after_cancel(
    client: AsyncClient, seed_data: dict, patient_auth: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P0-1: cancelled row must not block partial unique slot; book → cancel → book same slot → 201."""
    slot_day = seed_data["date"]
    slot_time = "11:00:00"

    class _Morning(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.combine(slot_day, time(8, 0))

    import src.application.services.booking_service as booking_service_mod

    monkeypatch.setattr(booking_service_mod, "datetime", _Morning)

    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    headers = {"Authorization": f"Bearer {patient_auth['access_token']}"}
    body = {
        "clinic_id": str(clinic_id),
        "doctor_id": str(doctor_id),
        "service_id": str(service_id),
        "appointment_date": slot_day.isoformat(),
        "appointment_time": slot_time,
    }
    r1 = await client.post("/api/v1/patient/bookings", json=body, headers=headers)
    assert r1.status_code == 201, r1.text
    booking_id = r1.json()["id"]

    r_del = await client.delete(
        f"/api/v1/patient/bookings/{booking_id}",
        headers=headers,
    )
    assert r_del.status_code == 200, r_del.text

    r2 = await client.post("/api/v1/patient/bookings", json=body, headers=headers)
    assert r2.status_code == 201, r2.text
    assert r2.json()["id"] != booking_id
    assert r2.json().get("status") == "pending"
