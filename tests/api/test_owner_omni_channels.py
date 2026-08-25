"""Tests for Owner omnichannel channels API (Phase 5)."""

import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.domain.entities.clinic import Clinic
from src.domain.entities.omnichannel_channel import Channel as OmniChannel
from src.domain.entities.omnichannel_integration_config import (
    OmnichannelIntegrationConfig,
)
from src.infrastructure.database import base as db_base


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_owner_create_and_list_channels(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """Owner can create channels of different types and then see them in the owner/channels list."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Create one channel of each key type from ARCH
    type_matrix = [
        ("telegram_bot", "Telegram Bot #1", "TELEGRAM_BOT"),
        ("whatsapp_business", "WhatsApp Business #1", "WHATSAPP_BUSINESS"),
        ("viber_bot", "Viber Bot #1", "VIBER_BOT"),
        ("max_chat", "Max Chat #1", "MAX_CHAT"),
        ("sms_gateway", "SMS Gateway #1", "SMS_GATEWAY"),
        ("email_inbox", "Email Inbox #1", "EMAIL_INBOX"),
        ("other", "Other Provider #1", "OTHER"),
    ]
    created_ids: list[str] = []
    for raw_type, display_name, expected_type in type_matrix:
        payload = {"type": raw_type, "display_name": display_name}
        r = await client.post("/api/v1/owner/channels", json=payload, headers=headers)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["type"] == expected_type
        assert data["display_name"] == display_name
        assert data["status"] == "PENDING_SETUP"
        assert data["has_credentials"] is False
        created_ids.append(data["id"])

    # List channels and ensure created channels are present
    r2 = await client.get("/api/v1/owner/channels", headers=headers)
    assert r2.status_code == 200, r2.text
    list_data = r2.json()
    assert "items" in list_data
    assert isinstance(list_data["items"], list)
    ids_in_list = {item["id"] for item in list_data["items"]}
    for cid in created_ids:
        assert cid in ids_in_list


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_owner_create_vk_bot_rejected(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """SC4: VK_BOT is hidden from create UI and rejected on owner API (legacy rows remain readable)."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.post(
        "/api/v1/owner/channels",
        json={"type": "VK_BOT", "display_name": "VK Bot blocked"},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    body = r.json()
    assert body["code"] == "omni_channel_type_not_creatable"
    assert isinstance(body["detail"], str) and body["detail"]


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_owner_set_credentials_and_visibility(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """Owner can store credentials; API never returns raw secret, only has_credentials flag (for multiple providers)."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    business_account_id = seed_data["clinic_id"]

    # Create two channels directly in DB for clarity (Telegram and Max)
    async with db_base.AsyncSessionLocal() as session:
        telegram_channel = OmniChannel(
            business_account_id=business_account_id,
            type="TELEGRAM_BOT",
            display_name="Telegram Bot Secrets",
            status="PENDING_SETUP",
        )
        max_channel = OmniChannel(
            business_account_id=business_account_id,
            type="MAX_CHAT",
            display_name="Max Chat Secrets",
            status="PENDING_SETUP",
        )
        session.add_all([telegram_channel, max_channel])
        await session.commit()
        await session.refresh(telegram_channel)
        await session.refresh(max_channel)
        telegram_channel_id = telegram_channel.id
        max_channel_id = max_channel.id

    # Store credentials for Telegram via API
    cred_payload_telegram = {
        "provider_type": "TELEGRAM",
        "scopes": "messages:read",
        "payload": json.dumps({"token": "telegram-test-token"}),
    }
    r = await client.post(
        f"/api/v1/owner/channels/{telegram_channel_id}/credentials",
        json=cred_payload_telegram,
        headers=headers,
    )
    assert r.status_code == 204, r.text

    # Store credentials for Max via API
    cred_payload_max = {
        "provider_type": "MAX",
        "scopes": None,
        "payload": json.dumps({"api_key": "max-secret-key"}),
    }
    r_max = await client.post(
        f"/api/v1/owner/channels/{max_channel_id}/credentials",
        json=cred_payload_max,
        headers=headers,
    )
    assert r_max.status_code == 204, r_max.text

    # List channels and verify has_credentials is True for both, but secrets are not present in payload
    r2 = await client.get("/api/v1/owner/channels", headers=headers)
    assert r2.status_code == 200, r2.text
    list_data = r2.json()
    items = list_data.get("items", [])
    telegram_target = next((item for item in items if item["id"] == str(telegram_channel_id)), None)
    max_target = next((item for item in items if item["id"] == str(max_channel_id)), None)
    assert telegram_target is not None
    assert max_target is not None
    assert telegram_target["has_credentials"] is True
    assert max_target["has_credentials"] is True
    # Response should not contain any secret fields
    assert "credentials_encrypted" not in telegram_target
    assert "credentials_encrypted" not in max_target

    # Verify encrypted credentials exist in DB and do not store plaintext
    async with db_base.AsyncSessionLocal() as session:
        result = await session.execute(
            select(OmnichannelIntegrationConfig).where(
                OmnichannelIntegrationConfig.business_account_id == business_account_id,
                OmnichannelIntegrationConfig.channel_id == telegram_channel_id,
            )
        )
        cfg = result.scalar_one_or_none()
        assert cfg is not None
        assert cfg.credentials_encrypted is not None
        assert "telegram-test-token" not in (cfg.credentials_encrypted or "")

        result_max = await session.execute(
            select(OmnichannelIntegrationConfig).where(
                OmnichannelIntegrationConfig.business_account_id == business_account_id,
                OmnichannelIntegrationConfig.channel_id == max_channel_id,
            )
        )
        cfg_max = result_max.scalar_one_or_none()
        assert cfg_max is not None
        assert cfg_max.credentials_encrypted is not None
        assert "max-secret-key" not in (cfg_max.credentials_encrypted or "")


@pytest.mark.regression_chats
@pytest.mark.security
@pytest.mark.asyncio
async def test_owner_cannot_access_foreign_channel(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """Owner cannot modify channel that belongs to another clinic."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Create channel for another clinic directly
    other_clinic_id = uuid.uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(Clinic(id=other_clinic_id, name="Foreign Clinic", prepayment_amount=0))
        await session.flush()
        channel = OmniChannel(
            business_account_id=other_clinic_id,
            type="TELEGRAM_BOT",
            display_name="Foreign Channel",
            status="PENDING_SETUP",
        )
        session.add(channel)
        await session.commit()
        await session.refresh(channel)
        foreign_channel_id = channel.id

    # Try to update foreign channel
    r = await client.put(
        f"/api/v1/owner/channels/{foreign_channel_id}",
        json={"display_name": "Should Not Work"},
        headers=headers,
    )
    assert r.status_code == 404

    # Try to set credentials for foreign channel
    r2 = await client.post(
        f"/api/v1/owner/channels/{foreign_channel_id}/credentials",
        json={"provider_type": "TELEGRAM", "scopes": None, "payload": "x"},
        headers=headers,
    )
    assert r2.status_code == 404

