"""Smoke test: POST /api/v1/patient/bookings."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_patient_booking(client: AsyncClient, seed_data: dict):
    """POST /api/v1/patient/bookings with patient_id, body returns 201 with id, status."""
    patient_id = seed_data["patient_id"]
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]
    # Use a slot time from working hours (e.g. 10:00)
    response = await client.post(
        f"/api/v1/patient/bookings?patient_id={patient_id}",
        json={
            "clinic_id": str(clinic_id),
            "doctor_id": str(doctor_id),
            "service_id": str(service_id),
            "appointment_date": day.isoformat(),
            "appointment_time": "10:00:00",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "status" in data
    assert data.get("status") == "pending"
