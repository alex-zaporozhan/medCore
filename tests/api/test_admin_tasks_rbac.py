
import pytest
from httpx import AsyncClient

from src.main import app


@pytest.fixture(scope="module", autouse=True)
def ensure_test_db_engine():
    """Ensure DB engine is initialized when running only this module (TESTING=1 defers init)."""
    from src.infrastructure.database import base as db_base
    if getattr(db_base, "init_engine_for_testing", None):
        db_base.init_engine_for_testing()


@pytest.mark.asyncio
async def test_admin_tasks_requires_auth():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/tasks")
        assert resp.status_code in (401, 403), "protected endpoint must return 401 or 403 without auth"


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

