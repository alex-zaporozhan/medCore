"""
Smoke test: every API endpoint used by admin and app frontend.

Run with: poetry run pytest tests/api/test_frontend_integration.py -v

Does not require frontend to be running; validates backend stubs for all pages.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """Landing / any page may call health."""
    r = await client.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_auth_send_code(client: AsyncClient):
    """Login page: send code."""
    r = await client.post("/api/v1/auth/send-code", json={"phone": "+79001234567"})
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_doctors_list(client: AsyncClient):
    """Admin doctors, app booking: GET doctors."""
    r = await client.get("/api/v1/doctors")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_services_list(client: AsyncClient):
    """App booking: GET services."""
    r = await client.get("/api/v1/services")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_doctor_schedule(client: AsyncClient, seed_data):
    """App booking, admin schedule: GET doctor schedule."""
    doctors = (await client.get("/api/v1/doctors")).json()
    if not doctors:
        pytest.skip("No doctors in seed")
    doctor_id = doctors[0]["id"]
    day = seed_data["date"]
    r = await client.get(
        f"/api/v1/doctors/{doctor_id}/schedule",
        params={"date": day.isoformat()},
    )
    assert r.status_code == 200
    assert "slots" in r.json()


@pytest.mark.asyncio
async def test_admin_bookings_list(client: AsyncClient, admin_auth: dict):
    """Admin bookings page: GET admin bookings."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/admin/bookings", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_reports_dashboard(client: AsyncClient):
    """Admin reports: GET dashboard (day)."""
    from datetime import date
    r = await client.get(
        "/api/v1/reports/dashboard",
        params={"date": date.today().isoformat(), "period": "day"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "date" in data
    assert "revenue" in data


@pytest.mark.asyncio
async def test_reports_no_show(client: AsyncClient):
    """Admin reports: GET no-show."""
    from datetime import date, timedelta
    today = date.today()
    r = await client.get(
        "/api/v1/reports/no-show",
        params={"date_from": today.isoformat(), "date_to": (today + timedelta(days=7)).isoformat()},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_reports_revenue(client: AsyncClient):
    """Admin reports: GET revenue."""
    from datetime import date, timedelta
    today = date.today()
    r = await client.get(
        "/api/v1/reports/revenue",
        params={"date_from": today.isoformat(), "date_to": (today + timedelta(days=7)).isoformat()},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_patients_list(client: AsyncClient):
    """Admin patients: GET patients (no filters = all)."""
    r = await client.get("/api/v1/patients")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_admin_doctor_schedule(client: AsyncClient, seed_data):
    """Admin schedule: GET admin doctor schedule."""
    doctors = (await client.get("/api/v1/doctors")).json()
    if not doctors:
        pytest.skip("No doctors in seed")
    doctor_id = doctors[0]["id"]
    day = seed_data["date"]
    r = await client.get(
        f"/api/v1/doctors/admin/{doctor_id}/schedule",
        params={"date": day.isoformat()},
    )
    assert r.status_code == 200
