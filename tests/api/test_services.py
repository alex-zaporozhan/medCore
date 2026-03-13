"""Smoke test: GET /api/v1/services."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_services(client: AsyncClient, seed_data: dict):
    """GET /api/v1/services returns 200 and list with id, name, price."""
    response = await client.get("/api/v1/services")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    item = data[0]
    assert "id" in item
    assert "name" in item
    assert "price" in item
