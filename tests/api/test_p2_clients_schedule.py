"""P2 Clients & Schedule: комментарий к записи, фильтр пациентов по датам визита."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_patch_booking_notes(client: AsyncClient, admin_auth: dict, seed_data: dict):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    day = seed_data["date"]
    r = await client.post(
        "/api/v1/admin/bookings",
        headers=headers,
        json={
            "clinic_id": str(seed_data["clinic_id"]),
            "patient_id": str(seed_data["patient_id"]),
            "doctor_id": str(seed_data["doctor_id"]),
            "service_id": str(seed_data["service_id"]),
            "appointment_date": day.isoformat(),
            "appointment_time": "09:00:00",
            "notes": "старый",
        },
    )
    assert r.status_code == 201, r.text
    bid = r.json()["id"]
    r2 = await client.patch(
        f"/api/v1/admin/bookings/{bid}",
        headers=headers,
        json={"notes": "Комментарий администратора"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["notes"] == "Комментарий администратора"
    r3 = await client.patch(
        f"/api/v1/admin/bookings/{bid}",
        headers=headers,
        json={"notes": None},
    )
    assert r3.status_code == 200, r3.text
    assert r3.json()["notes"] is None


@pytest.mark.asyncio
async def test_admin_patch_booking_status(client: AsyncClient, admin_auth: dict, seed_data: dict):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    day = seed_data["date"]
    r = await client.post(
        "/api/v1/admin/bookings",
        headers=headers,
        json={
            "clinic_id": str(seed_data["clinic_id"]),
            "patient_id": str(seed_data["patient_id"]),
            "doctor_id": str(seed_data["doctor_id"]),
            "service_id": str(seed_data["service_id"]),
            "appointment_date": day.isoformat(),
            "appointment_time": "10:00:00",
            "status": "pending",
        },
    )
    assert r.status_code == 201, r.text
    bid = r.json()["id"]
    assert r.json()["status"] == "pending"
    r2 = await client.patch(
        f"/api/v1/admin/bookings/{bid}",
        headers=headers,
        json={"status": "confirmed"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_patients_list_requires_auth(client: AsyncClient):
    """Без JWT RBAC возвращает 403 (как и для не-админа)."""
    r = await client.get(
        "/api/v1/patients",
        params={"visited_from": "2020-01-01"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_patients_list_forbidden_for_doctor_role(client: AsyncClient, doctor_auth: dict):
    """Врач без права patients.pii.read не видит списки/ПД (QA_ARCH)."""
    headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
    r = await client.get("/api/v1/patients", headers=headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_patients_visit_dates_invalid_order(client: AsyncClient, admin_auth: dict):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        "/api/v1/patients",
        params={"visited_from": "2020-01-02", "visited_to": "2020-01-01"},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patients_visit_filter_by_date(client: AsyncClient, admin_auth: dict, seed_data: dict):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    day = seed_data["date"]
    r = await client.post(
        "/api/v1/admin/bookings",
        headers=headers,
        json={
            "clinic_id": str(seed_data["clinic_id"]),
            "patient_id": str(seed_data["patient_id"]),
            "doctor_id": str(seed_data["doctor_id"]),
            "service_id": str(seed_data["service_id"]),
            "appointment_date": day.isoformat(),
            "appointment_time": "10:00:00",
        },
    )
    assert r.status_code == 201, r.text

    pid = str(seed_data["patient_id"])
    r2 = await client.get(
        "/api/v1/patients",
        params={
            "visited_from": day.isoformat(),
            "visited_to": day.isoformat(),
        },
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    ids = {p["id"] for p in r2.json()}
    assert pid in ids
