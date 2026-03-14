"""Basic tests for admin marketing attribution API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_marketing_attribution_summary_empty_ok(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    """Summary endpoint should work even when there is no attribution data."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    r = await client.get(
        "/api/v1/admin/attribution/summary",
        params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["items"] == []


