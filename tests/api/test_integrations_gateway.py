"""Tests for omnichannel Integration Gateway (Phase 2)."""

import json

import pytest
from httpx import AsyncClient

from src.core.config import settings
from src.infrastructure.database import base as db_base
from src.domain.entities.omnichannel_message import Message as OmniMessage


@pytest.mark.asyncio
async def test_telegram_webhook_persists_inbound_message(init_db, seed_data, client: AsyncClient, monkeypatch):
    """Send Telegram-style webhook and ensure omni_messages row is created."""

    # Ensure TELEGRAM_BOT_TOKEN is set for validation
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-telegram-token")

    payload = {
        "update_id": 123456,
        "message": {
            "message_id": 111,
            "from": {
                "id": 555,
                "is_bot": False,
                "first_name": "Test",
            },
            "chat": {
                "id": 555,
                "type": "private",
            },
            "date": 1700000000,
            "text": "Hello from Telegram",
        },
    }

    r = await client.post(
        "/api/v1/integrations/webhooks/telegram",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") in ("ok", "ignored")

    # Verify omni_messages contains at least one row for this text
    async with db_base.AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(OmniMessage).where(OmniMessage.content == "Hello from Telegram")
        )
        msg = result.scalar_one_or_none()
        assert msg is not None
        assert msg.direction == "INBOUND"
        assert msg.actor_type == "CLIENT"


@pytest.mark.asyncio
async def test_webchat_inbound_persists_message(init_db, seed_data, client: AsyncClient):
    """Send webchat message and ensure omni_messages row is created."""

    payload = {
        "anonymous_id": "anon-123",
        "text": "Hello from Webchat",
    }

    r = await client.post(
        "/api/v1/webchat/messages",
        json=payload,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "ok"

    async with db_base.AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(OmniMessage).where(OmniMessage.content == "Hello from Webchat")
        )
        msg = result.scalar_one_or_none()
        assert msg is not None
        assert msg.direction == "INBOUND"
        assert msg.actor_type == "CLIENT"


@pytest.mark.asyncio
async def test_duplicate_webhook_same_external_message_id_no_duplicate(init_db, seed_data, client: AsyncClient, monkeypatch):
    """Two identical webhooks (same external_message_id for same chat) must not create duplicate message."""
    monkeypatch.setattr(settings, "telegram_bot_token", "test-telegram-token")

    payload = {
        "update_id": 999,
        "message": {
            "message_id": 777,
            "from": {"id": 888, "is_bot": False, "first_name": "Dup"},
            "chat": {"id": 888, "type": "private"},
            "date": 1700000000,
            "text": "Idempotent message",
        },
    }

    r1 = await client.post(
        "/api/v1/integrations/webhooks/telegram",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert r1.status_code == 200, r1.text

    r2 = await client.post(
        "/api/v1/integrations/webhooks/telegram",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert r2.status_code == 200, r2.text

    async with db_base.AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(OmniMessage).where(
                OmniMessage.content == "Idempotent message",
                OmniMessage.direction == "INBOUND",
            )
        )
        messages = list(result.scalars().all())
        assert len(messages) == 1, "duplicate inbound message must not be created"
        assert messages[0].source_metadata is not None
        assert messages[0].source_metadata.get("external_message_id") == "777"

