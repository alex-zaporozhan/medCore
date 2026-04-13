"""Public PWA marketing feed/stories: bounded lists (QA_ARCH scale)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_public_feed_and_stories_limits(client, seed_data) -> None:
    cid = seed_data["clinic_id"]
    feed_ok = await client.get(
        f"/api/v1/public/clinics/{cid}/feed",
        params={"skip": 0, "limit": 10},
    )
    assert feed_ok.status_code == 200, feed_ok.text
    assert isinstance(feed_ok.json(), list)

    feed_bad = await client.get(f"/api/v1/public/clinics/{cid}/feed", params={"limit": 9999})
    assert feed_bad.status_code == 422, feed_bad.text

    stories_ok = await client.get(
        f"/api/v1/public/clinics/{cid}/stories",
        params={"limit": 5},
    )
    assert stories_ok.status_code == 200, stories_ok.text

    stories_bad = await client.get(f"/api/v1/public/clinics/{cid}/stories", params={"limit": 9999})
    assert stories_bad.status_code == 422, stories_bad.text
