"""Admin AI conflicts report: SQL-bounded items + full-range summary (QA_ARCH-019)."""

from __future__ import annotations

from datetime import date

import pytest


@pytest.mark.asyncio
async def test_admin_ai_conflicts_skip_limit_and_max(client, admin_auth) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    today = date.today().isoformat()
    base = "/api/v1/admin/ai-reports/conflicts"

    ok = await client.get(
        base,
        headers=headers,
        params={"clinic_id": str(clinic_id), "date_from": today, "date_to": today, "skip": 0, "limit": 10},
    )
    assert ok.status_code == 200, ok.text
    data = ok.json()
    assert "summary" in data
    assert "items" in data
    assert data.get("items_skip") == 0
    assert data.get("items_limit") == 10
    assert len(data["items"]) <= 10

    bad = await client.get(
        base,
        headers=headers,
        params={"clinic_id": str(clinic_id), "date_from": today, "date_to": today, "limit": 6000},
    )
    assert bad.status_code == 422, bad.text
