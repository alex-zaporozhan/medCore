"""Admin staff list bounds (QA_ARCH QA-AUDIT-006)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_admins_skip_limit_and_max(client, admin_auth) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    ok = await client.get(
        "/api/v1/admin/admins",
        headers=headers,
        params={"skip": 0, "limit": 10},
    )
    assert ok.status_code == 200, ok.text
    assert isinstance(ok.json(), list)
    bad = await client.get(
        "/api/v1/admin/admins",
        headers=headers,
        params={"limit": 3000},
    )
    assert bad.status_code == 422, bad.text
