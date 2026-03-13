"""Smoke test: GET /api/v1/doctors."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_doctors(client: AsyncClient, seed_data: dict):
    """GET /api/v1/doctors returns 200 and list with id, full_name, is_active."""
    response = await client.get("/api/v1/doctors")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    item = data[0]
    assert "id" in item
    assert "full_name" in item
    assert "is_active" in item
    assert "display_role" in item
    assert item["display_role"]  # e.g. "Врач", "Мастер", "Специалист"
    if "specialist_role" in item:
        assert item["specialist_role"] in ("doctor", "nurse", "master", "therapist", "other")