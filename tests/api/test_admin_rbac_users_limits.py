"""RBAC users list: pagination caps (QA_ARCH / §IV.2)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_rbac_users_skip_limit_and_max(client, admin_auth) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    ok = await client.get("/api/v1/admin/rbac/users", headers=headers, params={"skip": 0, "limit": 50})
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert "items" in body
    assert isinstance(body["items"], list)

    bad = await client.get("/api/v1/admin/rbac/users", headers=headers, params={"limit": 9999})
    assert bad.status_code == 422, bad.text
