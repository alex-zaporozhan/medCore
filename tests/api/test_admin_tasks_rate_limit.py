import pytest


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_task_comment_rate_limit_returns_structured_429(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    create_resp = await client.post(
        "/api/v1/admin/tasks",
        headers=headers,
        json={"title": "Rate-limit comments", "priority": "medium"},
    )
    assert create_resp.status_code == 201, create_resp.text
    task_id = create_resp.json()["id"]

    for i in range(12):
        resp = await client.post(
            f"/api/v1/admin/tasks/{task_id}/comments",
            headers=headers,
            json={"text": f"Comment {i}"},
        )
        assert resp.status_code == 201, resp.text

    overflow_resp = await client.post(
        f"/api/v1/admin/tasks/{task_id}/comments",
        headers=headers,
        json={"text": "Overflow"},
    )
    assert overflow_resp.status_code == 429, overflow_resp.text
    body = overflow_resp.json()
    assert body.get("code") == "rate_limit_exceeded"
