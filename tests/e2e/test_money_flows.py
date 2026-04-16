"""E2E-style API flows for revenue- and PD-sensitive paths (QA_ARCH).

Uses pytest + AsyncClient (same stack as API tests). Сценарий «пациент → оплата» см.
`test_booking_to_payment.py::test_booking_to_payment_flow`.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_e2e_admin_creates_booking_for_known_patient(
    client: AsyncClient, admin_auth: dict, seed_data: dict
):
    """Админка: запись на существующего пациента (денежный контур расписания)."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    base_day = seed_data["date"]
    candidate_days = [base_day + timedelta(weeks=w) for w in range(0, 12)]
    times = [f"{h:02d}:00:00" for h in range(9, 18)]
    last = None
    for day in candidate_days:
        for appointment_time in times:
            r = await client.post(
                "/api/v1/admin/bookings",
                headers=headers,
                json={
                    "clinic_id": str(seed_data["clinic_id"]),
                    "patient_id": str(seed_data["patient_id"]),
                    "doctor_id": str(seed_data["doctor_id"]),
                    "service_id": str(seed_data["service_id"]),
                    "appointment_date": day.isoformat(),
                    "appointment_time": appointment_time,
                },
            )
            last = r
            if r.status_code == 201:
                assert r.json().get("id")
                return
    assert last is not None
    assert last.status_code == 201, last.text


@pytest.mark.asyncio
async def test_e2e_admin_owner_can_list_patients(client: AsyncClient, admin_auth: dict):
    """Владелец/owner: список пациентов (RBAC ``patients.pii.read``)."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/patients", headers=headers)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_e2e_doctor_cannot_read_patient_pd(client: AsyncClient, doctor_auth: dict, seed_data: dict):
    """Врач: 403 на список и карточку пациента (жёсткая граница ПД)."""
    headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
    r = await client.get("/api/v1/patients", headers=headers)
    assert r.status_code == 403
    r2 = await client.get(f"/api/v1/patients/{seed_data['patient_id']}", headers=headers)
    assert r2.status_code == 403
