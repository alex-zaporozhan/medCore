"""Tests for omnichannel chat Phase 1 core flows.

Covers:
- creating Contact and Chat;
- adding inbound and outbound messages;
- soft-hiding a message with AuditLog entry.
"""

import uuid

import pytest
from sqlalchemy import select

from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.domain.entities.omnichannel_audit_log import AuditLog
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_create_contact_chat_and_messages(init_db, seed_data):
    business_account_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)

        # Create contact
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Omni Test Contact",
            primary_phone="+79990001122",
        )
        assert contact.id is not None

        # Create chat
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
        )
        assert chat.id is not None
        assert chat.business_account_id == business_account_id
        assert chat.contact_id == contact.id

        # Add inbound message
        inbound = await service.add_inbound_message(
            chat=chat,
            contact=contact,
            content="Hello from client",
        )
        assert inbound.id is not None
        assert inbound.direction == "INBOUND"
        assert inbound.actor_type == "CLIENT"

        # Add outbound message
        outbound = await service.add_outbound_message(
            chat=chat,
            actor_type="HUMAN_ADMIN",
            content="Hello from admin",
        )
        assert outbound.id is not None
        assert outbound.direction == "OUTBOUND"
        assert outbound.actor_type == "HUMAN_ADMIN"

        # Fetch last messages
        last_messages = await service.list_last_messages(chat_id=chat.id, limit=10)
        assert len(last_messages) == 2
        assert last_messages[0].id == inbound.id
        assert last_messages[1].id == outbound.id


@pytest.mark.asyncio
async def test_soft_hide_message_writes_audit_log(init_db, seed_data):
    business_account_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)

        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Hide Test Contact",
            primary_phone="+79990003344",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
        )
        message = await service.add_inbound_message(
            chat=chat,
            contact=contact,
            content="This will be hidden",
        )

        assert message.ui_hidden is False

        actor_id = uuid.uuid4()
        await service.soft_hide_message(
            business_account_id=business_account_id,
            message=message,
            reason="moderation",
            actor_id=actor_id,
            actor_type="ADMIN",
            ip_address="127.0.0.1",
            user_agent="pytest",
        )

        # Message should be marked as hidden
        assert message.ui_hidden is True
        assert message.hidden_reason == "moderation"

        # AuditLog entry should be present
        result = await session.execute(
            select(AuditLog).where(
                AuditLog.target_id == message.id,
                AuditLog.action_type == "MESSAGE_SOFT_HIDE",
            )
        )
        audit_row = result.scalar_one_or_none()
        assert audit_row is not None
        assert audit_row.business_account_id == business_account_id
        assert audit_row.actor_id == actor_id
        assert audit_row.metadata and audit_row.metadata.get("reason") == "moderation"

