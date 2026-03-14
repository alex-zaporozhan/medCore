import uuid

import pytest
from httpx import AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_admin_tasks_requires_auth():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/tasks")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_tasks_forbidden_without_permission(monkeypatch):
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Fake token with admin type but no permissions wired in fixtures;
        # here we just assert that backend returns 401/403 for invalid token.
        resp = await client.get(
            "/api/v1/admin/tasks",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code in (401, 403)

