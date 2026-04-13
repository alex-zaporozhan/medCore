"""Integration tests for WhatsApp webhook in Integration Gateway (Phase 6)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_whatsapp_webhook_creates_contact_chat_message_with_channel(  # noqa: D103
    init_db,
    seed_data,
    client: AsyncClient,
) -> None:
    # Call WhatsApp webhook with minimal valid payload
    payload = {
        "from": "+1234567890",
        "chat_id": "whatsapp-chat-1",
        "text": "Hello from WhatsApp",
        "message_id": "wa-msg-1",
    }
    r = await client.post("/api/v1/integrations/webhooks/whatsapp", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"

    # Verify that Contact, Chat, and Message were created with correct provider/channel
    async with db_base.AsyncSessionLocal() as session:
        # There should be exactly one message with provider WHATSAPP in source_metadata
        result_msg = await session.execute(select(OmniMessage))
        msgs = list(result_msg.scalars().all())
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg.content == "Hello from WhatsApp"
        assert msg.direction == "INBOUND"
        assert msg.actor_type == "CLIENT"
        assert msg.channel_id is not None
        assert msg.source_metadata.get("provider") == "WHATSAPP"

        # Chat should exist and be linked to channel
        result_chat = await session.execute(
            select(OmniChat).where(OmniChat.id == msg.chat_id)
        )
        chat = result_chat.scalar_one_or_none()
        assert chat is not None
        assert chat.channel_id == msg.channel_id

        # Contact should exist and be linked to business account
        result_contact = await session.execute(
            select(OmniContact).where(OmniContact.id == msg.contact_id)
        )
        contact = result_contact.scalar_one_or_none()
        assert contact is not None
        assert contact.business_account_id == chat.business_account_id

