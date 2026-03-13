"""Tests for admin omnichannel chat API (Phase 3)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.domain.entities.omnichannel_ai_settings import AISettings as OmniAISettings
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.infrastructure.database import base as db_base


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_list_omni_chats_and_messages(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """Admin can list omnichannel chats and see messages."""

    business_account_id = seed_data["clinic_id"]

    # Prepare one omnichannel chat + message directly via service
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Omni Admin Test",
            primary_phone="+79990002233",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
        )
        await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Hello from client (admin omni)",
        )
        await session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # List chats
    r = await client.get("/api/v1/admin/omni-chats", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 1

    chat_id = data["items"][0]["chat_id"]

    # Get single chat by id
    r_detail = await client.get(f"/api/v1/admin/omni-chats/{chat_id}", headers=headers)
    assert r_detail.status_code == 200, r_detail.text
    detail = r_detail.json()
    assert detail["chat_id"] == chat_id
    assert detail["contact_id"] is not None
    assert "status" in detail
    assert "ai_mode" in detail

    # Get messages for chat
    r2 = await client.get(f"/api/v1/admin/omni-chats/{chat_id}/messages", headers=headers)
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    assert "items" in data2
    assert isinstance(data2["items"], list)
    assert len(data2["items"]) >= 1

    # Cursor: messages after first message
    first_msg_id = data2["items"][0]["id"]
    r_after = await client.get(
        f"/api/v1/admin/omni-chats/{chat_id}/messages",
        params={"after": first_msg_id, "limit": 10},
        headers=headers,
    )
    assert r_after.status_code == 200, r_after.text
    after_data = r_after.json()
    assert "items" in after_data


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_send_and_hide_omni_message(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """Admin can send outbound message and soft-hide a message via API."""

    business_account_id = seed_data["clinic_id"]

    # Prepare chat + inbound msg
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Omni Hide Test",
            primary_phone="+79990004455",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
        )
        inbound = await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Client message to hide via admin",
        )
        await session.commit()
        chat_id = chat.id
        inbound_id = inbound.id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Send outbound message from admin
    r = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/messages",
        json={"content": "Admin reply in omni chat"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    sent = r.json()
    assert sent.get("direction") == "OUTBOUND"
    assert sent.get("actor_type") == "HUMAN_ADMIN"

    # Hide inbound message
    r2 = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/messages/{inbound_id}/hide",
        json={"reason": "moderation via admin API"},
        headers=headers,
    )
    assert r2.status_code == 204, r2.text

    # Verify message is hidden in DB
    async with db_base.AsyncSessionLocal() as session:
        result = await session.execute(
            select(OmniMessage).where(OmniMessage.id == inbound_id)
        )
        msg = result.scalar_one_or_none()
        assert msg is not None
        assert msg.ui_hidden is True
        assert msg.hidden_reason == "moderation via admin API"


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_update_omni_chat_ai_mode(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """Admin can update ai_mode for specific omnichannel chat and it is persisted in omni_ai_settings."""

    business_account_id = seed_data["clinic_id"]

    # Prepare chat
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Omni AI Mode Test",
            primary_phone="+79990005566",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
        )
        chat_id = chat.id
        await session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Update ai_mode to AUTO_REPLY
    r = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/ai-mode",
        json={"ai_mode": "AUTO_REPLY"},
        headers=headers,
    )
    assert r.status_code == 204, r.text

    # Verify chat.ai_mode and omni_ai_settings row
    async with db_base.AsyncSessionLocal() as session:
        result_chat = await session.execute(
            select(OmniChat).where(OmniChat.id == chat_id)
        )
        chat_db = result_chat.scalar_one_or_none()
        assert chat_db is not None
        assert chat_db.ai_mode == "AUTO_REPLY"

        result_settings = await session.execute(
            select(OmniAISettings).where(
                OmniAISettings.scope == "CHAT",
                OmniAISettings.scope_id == chat_id,
            )
        )
        settings_row = result_settings.scalar_one_or_none()
        assert settings_row is not None
        assert settings_row.ai_mode == "AUTO_REPLY"

    # Invalid ai_mode should return 400
    r_bad = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/ai-mode",
        json={"ai_mode": "UNKNOWN"},
        headers=headers,
    )
    assert r_bad.status_code == 400
    assert "Invalid ai_mode" in r_bad.text


@pytest.mark.asyncio
async def test_admin_omni_messages_exclude_hidden_by_default_include_hidden_param(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """GET messages without include_hidden returns only non-hidden; with include_hidden=true returns all including ui_hidden."""
    business_account_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Omni Hidden Test",
            primary_phone="+79990006677",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
        )
        visible = await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Visible message",
        )
        to_hide = await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Message to soft-hide",
        )
        await session.commit()
        chat_id = chat.id
        to_hide_id = to_hide.id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Soft-hide one message
    r_hide = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/messages/{to_hide_id}/hide",
        json={"reason": "test filter"},
        headers=headers,
    )
    assert r_hide.status_code == 204, r_hide.text

    # Without include_hidden: hidden message must not be in response
    r_default = await client.get(f"/api/v1/admin/omni-chats/{chat_id}/messages", headers=headers)
    assert r_default.status_code == 200, r_default.text
    items_default = r_default.json()["items"]
    ids_default = [m["id"] for m in items_default]
    assert str(to_hide_id) not in ids_default
    assert str(visible.id) in ids_default
    for m in items_default:
        assert m.get("ui_hidden") is False or "ui_hidden" not in m or m["ui_hidden"] is False

    # With include_hidden=true: hidden message must be in response with ui_hidden: true
    r_include = await client.get(
        f"/api/v1/admin/omni-chats/{chat_id}/messages",
        params={"include_hidden": "true"},
        headers=headers,
    )
    assert r_include.status_code == 200, r_include.text
    items_include = r_include.json()["items"]
    ids_include = [m["id"] for m in items_include]
    assert str(to_hide_id) in ids_include
    hidden_msg = next(m for m in items_include if m["id"] == str(to_hide_id))
    assert hidden_msg["ui_hidden"] is True
    assert hidden_msg.get("hidden_reason") == "test filter"

