"""Recall marketing lists: bounded pagination (QA_ARCH scale)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_recall_logs_list_limit_and_max(client, admin_auth) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    base = f"/api/v1/admin/clinics/{clinic_id}/recall/logs"

    ok = await client.get(base, headers=headers, params={"limit": 10, "skip": 0})
    assert ok.status_code == 200, ok.text
    assert isinstance(ok.json(), list)

    bad = await client.get(base, headers=headers, params={"limit": 6000})
    assert bad.status_code == 422, bad.text


@pytest.mark.parametrize(
    "path",
    [
        "segments",
        "templates",
        "campaigns",
        "automations",
    ],
)
@pytest.mark.asyncio
async def test_admin_recall_marketing_lists_limit_max(client, admin_auth, path: str) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    url = f"/api/v1/admin/clinics/{clinic_id}/recall/{path}"
    ok = await client.get(url, headers=headers, params={"limit": 5})
    assert ok.status_code == 200, ok.text
    bad = await client.get(url, headers=headers, params={"limit": 6000})
    assert bad.status_code == 422, bad.text
