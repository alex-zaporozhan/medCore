
import pytest


@pytest.fixture(scope="module", autouse=True)
def ensure_test_db_engine():
    """Ensure DB engine is initialized when running only this module (TESTING=1 defers init)."""
    from src.infrastructure.database import base as db_base
    if getattr(db_base, "init_engine_for_testing", None):
        db_base.init_engine_for_testing()


@pytest.mark.asyncio
async def test_admin_tasks_requires_auth(client):
    resp = await client.get("/api/v1/admin/tasks")
    assert resp.status_code in (401, 403), "protected endpoint must return 401 or 403 without auth"


@pytest.mark.asyncio
async def test_admin_tasks_forbidden_without_permission(client):
    # Fake token with admin type but no permissions wired in fixtures;
    # here we just assert that backend returns 401/403 for invalid token.
    resp = await client.get(
        "/api/v1/admin/tasks",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert resp.status_code in (401, 403)


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_doctor_cannot_bulk_status_or_reorder_or_unblock(client, admin_auth, doctor_auth):
    admin_headers = _auth_headers(admin_auth["access_token"])
    doctor_headers = _auth_headers(doctor_auth["access_token"])

    create_resp = await client.post(
        "/api/v1/admin/tasks",
        headers=admin_headers,
        json={
            "title": "RBAC granular operations",
            "priority": "medium",
            "assignee_ids": [doctor_auth["admin_id"]],
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    task_id = create_resp.json()["id"]

    block_resp = await client.patch(
        f"/api/v1/admin/tasks/{task_id}",
        headers=admin_headers,
        json={"blocked": True, "blocked_reason": "Waiting approval"},
    )
    assert block_resp.status_code == 200, block_resp.text

    bulk_resp = await client.post(
        "/api/v1/admin/tasks/bulk/status",
        headers=doctor_headers,
        json={"task_ids": [task_id], "to_status": "in_progress"},
    )
    assert bulk_resp.status_code == 403, bulk_resp.text

    reorder_resp = await client.post(
        "/api/v1/admin/tasks/reorder",
        headers=doctor_headers,
        json={"status": "open", "ordered_task_ids": [task_id]},
    )
    assert reorder_resp.status_code == 403, reorder_resp.text

    unblock_resp = await client.patch(
        f"/api/v1/admin/tasks/{task_id}",
        headers=doctor_headers,
        json={"blocked": False},
    )
    assert unblock_resp.status_code == 403, unblock_resp.text

