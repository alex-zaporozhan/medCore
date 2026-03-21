"""Smoke test: POST /api/v1/patient/bookings."""

import uuid

import pytest
from httpx import AsyncClient


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
    detail = response.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "clinic_mismatch"
