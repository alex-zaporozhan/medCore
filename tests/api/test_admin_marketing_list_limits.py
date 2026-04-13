"""Admin marketing posts/stories: bounded pagination (QA_ARCH-019)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_marketing_posts_pagination_and_max(client, admin_auth) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    base = f"/api/v1/admin/clinics/{clinic_id}/marketing/posts"

    ok = await client.get(base, headers=headers, params={"limit": 10, "skip": 0})
    assert ok.status_code == 200, ok.text
    assert isinstance(ok.json(), list)

    bad = await client.get(base, headers=headers, params={"limit": 6000})
    assert bad.status_code == 422, bad.text


@pytest.mark.asyncio
async def test_admin_marketing_stories_pagination_and_max(client, admin_auth) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    base = f"/api/v1/admin/clinics/{clinic_id}/marketing/stories"

    ok = await client.get(base, headers=headers, params={"limit": 5, "skip": 0})
    assert ok.status_code == 200, ok.text
    assert isinstance(ok.json(), list)

    bad = await client.get(base, headers=headers, params={"limit": 6000})
    assert bad.status_code == 422, bad.text
