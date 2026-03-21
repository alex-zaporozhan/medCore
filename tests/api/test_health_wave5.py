"""Health endpoints for Wave 5 (replica probe)."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.config import settings
from src.main import app


@pytest.mark.asyncio
async def test_health_replica_shape():
    """GET /health/replica returns replica status; body shape depends on DATABASE_REPLICA_URL."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health/replica")
    assert r.status_code == 200
    data = r.json()
    assert "replica_configured" in data
    if not settings.database_replica_url:
        assert data["replica_configured"] is False
