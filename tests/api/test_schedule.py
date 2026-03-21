"""Smoke test: GET /api/v1/doctors/{doctor_id}/schedule."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_doctor_schedule(client: AsyncClient, seed_data: dict):
    """GET /api/v1/doctors/{id}/schedule?date= returns 200 and slots structure."""
    doctor_id = seed_data["doctor_id"]
    day = seed_data["date"]
    response = await client.get(
        f"/api/v1/doctors/{doctor_id}/schedule",
        params={"date": day.isoformat(), "clinic_id": str(seed_data["clinic_id"])},
    )
    assert response.status_code == 200
    data = response.json()
    assert "doctor_id" in data
    assert "date" in data
    assert "slots" in data
    assert isinstance(data["slots"], list)


@pytest.mark.asyncio
async def test_get_doctor_schedule_wrong_clinic_returns_404(client: AsyncClient, seed_data: dict):
    """Doctor must belong to clinic_id in query (multi-tenant guard)."""
    doctor_id = seed_data["doctor_id"]
    day = seed_data["date"]
    wrong_clinic = uuid.uuid4()
    response = await client.get(
        f"/api/v1/doctors/{doctor_id}/schedule",
        params={"date": day.isoformat(), "clinic_id": str(wrong_clinic)},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_doctor_schedule_admin_unknown_doctor_returns_403(
    client: AsyncClient, seed_data: dict, admin_auth: dict
):
    """Admin schedule: doctor not in admin's clinic (or unknown) → 403 clinic_forbidden."""
    unknown_doctor = uuid.uuid4()
    day = seed_data["date"]
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    response = await client.get(
        f"/api/v1/doctors/admin/{unknown_doctor}/schedule",
        params={"date": day.isoformat()},
        headers=headers,
    )
    assert response.status_code == 403
    detail = response.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "clinic_forbidden"


@pytest.mark.asyncio
async def test_get_admin_clinic_schedule_foreign_clinic_in_path_returns_403(
    client: AsyncClient, seed_data: dict, admin_auth: dict
):
    """Path clinic_id must match JWT admin clinic."""
    other_clinic = uuid.uuid4()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    response = await client.get(
        f"/api/v1/admin/clinics/{other_clinic}/schedule",
        params={
            "date": seed_data["date"].isoformat(),
            "doctor_ids": str(seed_data["doctor_id"]),
        },
        headers=headers,
    )
    assert response.status_code == 403
    detail = response.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "clinic_forbidden"
