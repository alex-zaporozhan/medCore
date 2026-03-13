"""Tests for Owner omnichannel AI settings API (Phase 6)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.domain.entities.omnichannel_ai_settings import AISettings as OmniAISettings
from src.domain.entities.omnichannel_channel import Channel as OmniChannel
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_owner_get_and_update_omni_ai_settings_business_and_channel(  # noqa: D103
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    business_account_id = seed_data["clinic_id"]

    # Prepare one channel for this clinic
    async with db_base.AsyncSessionLocal() as session:
        channel = OmniChannel(
            business_account_id=business_account_id,
            type="TELEGRAM_BOT",
            display_name="Omni Telegram",
            status="ACTIVE",
        )
        session.add(channel)
        await session.commit()
        await session.refresh(channel)
        channel_id = channel.id

    # Initial GET should return DISABLED by default and no channel overrides
    r_get = await client.get("/api/v1/owner/omni-ai-settings", headers=headers)
    assert r_get.status_code == 200, r_get.text
    body = r_get.json()
    assert body["business"]["ai_mode"] == "DISABLED"
    assert isinstance(body["channels"], list)
    assert any(item["channel_id"] == str(channel_id) for item in body["channels"])

    # Update BUSINESS ai_mode and CHANNEL override
    payload = {
        "business": {
            "ai_mode": "auto_reply",
            "confidence_thresholds": {"auto_reply": 0.8},
        },
        "channels": [
            {"channel_id": str(channel_id), "ai_mode": "SUGGEST_ONLY"},
        ],
    }
    r_put = await client.put("/api/v1/owner/omni-ai-settings", json=payload, headers=headers)
    assert r_put.status_code == 200, r_put.text
    updated = r_put.json()

    # Business mode should be AUTO_REPLY (uppercased)
    assert updated["business"]["ai_mode"] == "AUTO_REPLY"
    assert updated["business"]["confidence_thresholds"]["auto_reply"] == 0.8

    # Channel override should be SUGGEST_ONLY
    channels = updated["channels"]
    target = next(item for item in channels if item["channel_id"] == str(channel_id))
    assert target["ai_mode"] == "SUGGEST_ONLY"

    # Verify rows exist in omni_ai_settings
    async with db_base.AsyncSessionLocal() as session:
        result = await session.execute(
            select(OmniAISettings).where(
                OmniAISettings.scope == "BUSINESS",
                OmniAISettings.scope_id == business_account_id,
            )
        )
        business_row = result.scalar_one_or_none()
        assert business_row is not None
        assert business_row.ai_mode == "AUTO_REPLY"

        result_ch = await session.execute(
            select(OmniAISettings).where(
                OmniAISettings.scope == "CHANNEL",
                OmniAISettings.scope_id == channel_id,
            )
        )
        channel_row = result_ch.scalar_one_or_none()
        assert channel_row is not None
        assert channel_row.ai_mode == "SUGGEST_ONLY"


@pytest.mark.asyncio
async def test_owner_omni_ai_settings_rejects_invalid_mode(  # noqa: D103
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Invalid business ai_mode
    bad_payload = {
        "business": {
            "ai_mode": "UNKNOWN_MODE",
        }
    }
    r = await client.put("/api/v1/owner/omni-ai-settings", json=bad_payload, headers=headers)
    assert r.status_code == 400
    assert "Invalid ai_mode for business" in r.text

