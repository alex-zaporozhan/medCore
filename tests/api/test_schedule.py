"""Smoke test: GET /api/v1/doctors/{doctor_id}/schedule."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_doctor_schedule(client: AsyncClient, seed_data: dict):
    """GET /api/v1/doctors/{id}/schedule?date= returns 200 and slots structure."""
    doctor_id = seed_data["doctor_id"]
    day = seed_data["date"]
    response = await client.get(
        f"/api/v1/doctors/{doctor_id}/schedule",
        params={"date": day.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert "doctor_id" in data
    assert "date" in data
    assert "slots" in data
    assert isinstance(data["slots"], list)
