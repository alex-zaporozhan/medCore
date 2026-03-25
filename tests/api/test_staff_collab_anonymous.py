"""P1: staff collab API без JWT — 403 (граница контура)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_staff_feed_posts_requires_admin_session(client: AsyncClient) -> None:
    r = await client.get("/api/v1/admin/staff/feed/posts")
    assert r.status_code == 403
