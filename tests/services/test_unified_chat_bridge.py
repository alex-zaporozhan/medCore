"""Tests for Unified Chat bridge: PWA -> omni (WEB_APP), admin reply -> PWA."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.chat_service import ChatService
from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.domain.entities.omnichannel_channel import Channel
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_web_app_channel_get_or_create(init_db, seed_data):
    """Block 1: get_or_create_channel_for_provider(WEB_APP) returns channel id, second call returns same."""
    business_account_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        ch1 = await service.get_or_create_channel_for_provider(business_account_id, "WEB_APP")
        assert ch1 is not None
        ch2 = await service.get_or_create_channel_for_provider(business_account_id, "WEB_APP")
        assert ch2 == ch1
        result = await session.execute(
            select(Channel).where(
                Channel.business_account_id == business_account_id,
                Channel.type == "WEB_APP",
            )
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.id == ch1


@pytest.mark.asyncio
async def test_get_or_create_contact_for_patient(init_db, seed_data):
    """Block 2: get_or_create_contact_for_patient creates on first call, returns same on second."""
    business_account_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        c1 = await service.get_or_create_contact_for_patient(
            business_account_id=business_account_id,
            patient_id=patient_id,
            full_name="Test Patient",
            primary_phone="+79001234567",
        )
        assert c1.id is not None
        assert c1.external_ids is not None
        assert c1.external_ids.get("patient_id") == str(patient_id)
        c2 = await service.get_or_create_contact_for_patient(
            business_account_id=business_account_id,
            patient_id=patient_id,
            full_name="Other Name",
            primary_phone="+79999999999",
        )
        assert c2.id == c1.id


@pytest.mark.asyncio
async def test_bridge_pwa_to_omni_integration(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """Bridge: patient sends message via ChatService -> omni_contacts, omni_chats (WEB_APP), omni_messages; admin list shows chat."""
    patient_id = seed_data["patient_id"]
    clinic_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        chat_svc = ChatService(session)
        dto = await chat_svc.send_message_from_patient(
            clinic_id=clinic_id,
            patient_id=patient_id,
            body="Hello from PWA bridge test",
        )
        assert dto is not None
        assert dto.body == "Hello from PWA bridge test"
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        # Contact with patient_id in external_ids
        result = await session.execute(
            select(OmniContact).where(
                OmniContact.business_account_id == clinic_id,
                OmniContact.external_ids["patient_id"].as_string() == str(patient_id),
            )
        )
        contact = result.scalar_one_or_none()
        assert contact is not None

        # Chat with WEB_APP channel
        result_chat = await session.execute(
            select(OmniChat)
            .where(OmniChat.business_account_id == clinic_id, OmniChat.contact_id == contact.id)
            .limit(1)
        )
        chat = result_chat.scalar_one_or_none()
        assert chat is not None
        assert chat.channel_id is not None
        ch_result = await session.execute(select(Channel).where(Channel.id == chat.channel_id))
        channel = ch_result.scalar_one_or_none()
        assert channel is not None
        assert channel.type == "WEB_APP"

        # Inbound message in omni_messages
        result_msg = await session.execute(
            select(OmniMessage).where(
                OmniMessage.chat_id == chat.id,
                OmniMessage.direction == "INBOUND",
            )
        )
        messages = list(result_msg.scalars().all())
        assert len(messages) >= 1
        assert any("Hello from PWA bridge test" in (m.content or "") for m in messages)

    # Admin list omni-chats shows this dialog
    headers_admin = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r_list = await client.get("/api/v1/admin/omni-chats", headers=headers_admin)
    assert r_list.status_code == 200, r_list.text
    list_data = r_list.json()
    assert list_data.get("total", 0) >= 1
    items = list_data.get("items", [])
    chat_ids = [str(it["chat_id"]) for it in items]
    assert str(chat.id) in chat_ids


@pytest.mark.asyncio
async def test_web_app_dispatcher_admin_reply_to_pwa(
    init_db, seed_data, client: AsyncClient, admin_auth: dict
):
    """Dispatcher WEB_APP: omni chat with WEB_APP + contact(patient_id) + Conversation; admin sends message -> chat_messages and Conversation updated."""
    from src.domain.entities.conversation import Conversation
    from src.domain.entities.chat_message import ChatMessage as PwaChatMessage
    from src.infrastructure.database.conversation_repo_impl import ConversationRepositoryImpl
    from src.infrastructure.database.chat_message_repo_impl import ChatMessageRepositoryImpl

    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]

    async with db_base.AsyncSessionLocal() as session:
        omni_svc = OmnichannelChatService(session)
        channel_id = await omni_svc.get_or_create_channel_for_provider(clinic_id, "WEB_APP")
        assert channel_id is not None
        contact = await omni_svc.get_or_create_contact_for_patient(
            business_account_id=clinic_id,
            patient_id=patient_id,
            full_name="Test Patient",
            primary_phone="+79001234567",
        )
        chat = await omni_svc.get_or_create_chat(clinic_id, contact, channel_id=channel_id)
        conv_repo = ConversationRepositoryImpl(session)
        conv = await conv_repo.get_by_clinic_patient(clinic_id, patient_id)
        if conv is None:
            conv = Conversation(
                clinic_id=clinic_id,
                patient_id=patient_id,
                assigned_admin_id=None,
                last_message_at=None,
                last_message_sender_type=None,
                unread_by_admin_count=0,
                unread_by_patient_count=0,
            )
            conv = await conv_repo.create(conv)
        await session.commit()
        chat_id = chat.id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/messages",
        json={"content": "Admin reply to PWA"},
        headers=headers,
    )
    assert r.status_code == 201, r.text

    async with db_base.AsyncSessionLocal() as session:
        conv_repo = ConversationRepositoryImpl(session)
        msg_repo = ChatMessageRepositoryImpl(session)
        conv = await conv_repo.get_by_clinic_patient(clinic_id, patient_id)
        assert conv is not None
        assert conv.last_message_sender_type == "admin"
        result = await session.execute(
            select(PwaChatMessage).where(
                PwaChatMessage.conversation_id == conv.id,
                PwaChatMessage.sender_type == "admin",
                PwaChatMessage.body == "Admin reply to PWA",
            )
        )
        admin_msg = result.scalar_one_or_none()
        assert admin_msg is not None
        assert conv.unread_by_patient_count >= 1


@pytest.mark.asyncio
async def test_bridge_idempotent_no_duplicate_omni_message(init_db, seed_data):
    """Calling bridge twice for same conversation+message does not create duplicate in omni_messages."""
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]

    async with db_base.AsyncSessionLocal() as session:
        chat_svc = ChatService(session)
        conv = await chat_svc.conv_repo.get_by_clinic_patient(clinic_id, patient_id)
        if conv is None:
            from src.domain.entities.conversation import Conversation
            conv = Conversation(
                clinic_id=clinic_id,
                patient_id=patient_id,
                assigned_admin_id=None,
                last_message_at=None,
                last_message_sender_type=None,
                unread_by_admin_count=0,
                unread_by_patient_count=0,
            )
            conv = await chat_svc.conv_repo.create(conv)
        dto = await chat_svc.send_message_from_patient(
            clinic_id=clinic_id,
            patient_id=patient_id,
            body="Idempotency test message",
        )
        assert dto is not None
        msg_entity = await chat_svc.msg_repo.get_by_id(dto.id)
        assert msg_entity is not None

        omni_svc = OmnichannelChatService(session)
        contact = await omni_svc.contacts.find_by_external_id(
            business_account_id=clinic_id,
            external_key="patient_id",
            external_value=str(patient_id),
        )
        assert contact is not None
        chat = await omni_svc.chats.find_open_by_contact(
            business_account_id=clinic_id,
            contact_id=contact.id,
        )
        assert chat is not None

        result = await session.execute(
            select(OmniMessage).where(
                OmniMessage.chat_id == chat.id,
                OmniMessage.direction == "INBOUND",
            )
        )
        count_after_first = len(list(result.scalars().all()))

        await chat_svc._bridge_patient_message_to_omni(clinic_id, patient_id, conv.id, msg_entity)
        result2 = await session.execute(
            select(OmniMessage).where(
                OmniMessage.chat_id == chat.id,
                OmniMessage.direction == "INBOUND",
            )
        )
        count_after_second = len(list(result2.scalars().all()))
        assert count_after_second == count_after_first, "Bridge should be idempotent: no duplicate message"
