"""Forms list/export bounds (QA_ARCH QA-AUDIT-006)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_forms_templates_skip_limit_max(client, admin_auth) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    ok = await client.get(
        "/api/v1/admin/forms/templates",
        headers=headers,
        params={"skip": 0, "limit": 10},
    )
    assert ok.status_code == 200, ok.text
    bad = await client.get(
        "/api/v1/admin/forms/templates",
        headers=headers,
        params={"limit": 6000},
    )
    assert bad.status_code == 422, bad.text


@pytest.mark.asyncio
async def test_admin_forms_submissions_skip_limit_max(client, admin_auth) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    ok = await client.get(
        "/api/v1/admin/forms/submissions",
        headers=headers,
        params={"skip": 0, "limit": 5},
    )
    assert ok.status_code == 200, ok.text
    bad = await client.get(
        "/api/v1/admin/forms/submissions",
        headers=headers,
        params={"limit": 6000},
    )
    assert bad.status_code == 422, bad.text


@pytest.mark.asyncio
async def test_admin_forms_export_submission_limit_max(client, admin_auth, seed_data) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    pid = seed_data["patient_id"]
    ok = await client.get(
        "/api/v1/admin/forms/export",
        headers=headers,
        params={"patient_id": str(pid), "submission_limit": 100},
    )
    assert ok.status_code == 200, ok.text
    bad = await client.get(
        "/api/v1/admin/forms/export",
        headers=headers,
        params={"patient_id": str(pid), "submission_limit": 20000},
    )
    assert bad.status_code == 422, bad.text
