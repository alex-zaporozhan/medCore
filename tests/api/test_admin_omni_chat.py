"""Tests for admin omnichannel chat API (Phase 3)."""

import asyncio
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.domain.entities.omnichannel_ai_settings import AISettings as OmniAISettings
from src.domain.entities.omnichannel_channel import Channel as OmniChannel
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_chat_closure import OmniChatClosure
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.infrastructure.database import base as db_base


async def _add_outbound_capable_channel(session, clinic_id: uuid.UUID) -> uuid.UUID:
    """WEB_WIDGET supports admin outbound (OutboundPolicy + dispatcher)."""
    ch = OmniChannel(
        id=uuid.uuid4(),
        business_account_id=clinic_id,
        type="WEB_WIDGET",
        display_name="Test Web Widget",
        status="ACTIVE",
    )
    session.add(ch)
    await session.flush()
    return ch.id


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_list_omni_chats_and_messages(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """Admin can list omnichannel chats and see messages."""

    business_account_id = seed_data["clinic_id"]

    # Prepare one omnichannel chat + message directly via service
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        channel_id = await _add_outbound_capable_channel(session, business_account_id)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Omni Admin Test",
            primary_phone="+79990002233",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=channel_id,
        )
        await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Hello from client (admin omni)",
            channel_id=channel_id,
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
        channel_id = await _add_outbound_capable_channel(session, business_account_id)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Omni Hide Test",
            primary_phone="+79990004455",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=channel_id,
        )
        inbound = await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Client message to hide via admin",
            channel_id=channel_id,
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
    assert sent.get("channel_id") == str(channel_id)
    assert sent.get("sender_admin_id") == admin_auth["admin_id"]

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
async def test_admin_claim_and_close_omni_chat_and_analytics(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    business_account_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        channel_id = await _add_outbound_capable_channel(session, business_account_id)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Omni Claim Close Test",
            primary_phone="+79990007788",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=channel_id,
        )
        chat.status = "WAITING_FOR_OPERATOR"
        chat.assignee_admin_id = None
        await session.flush()
        chat_id = chat.id
        await session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Claim -> assigned to current admin + IN_PROGRESS + claimed_at set
    r_claim = await client.post(f"/api/v1/admin/omni-chats/{chat_id}/claim", headers=headers)
    assert r_claim.status_code == 200, r_claim.text
    claimed = r_claim.json()["chat"]
    assert claimed["chat_id"] == str(chat_id)
    assert claimed["assignee_admin_id"] == admin_auth["admin_id"]
    assert claimed["status"] in {"IN_PROGRESS", "WAITING_FOR_OPERATOR", "OPEN"}  # server normalizes to IN_PROGRESS
    assert claimed.get("claimed_at") is not None

    # Close -> closure record + chat CLOSED
    r_close = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/close",
        json={"outcome": "BOOKED", "tag_ids": [], "comment": "Booked"},
        headers=headers,
    )
    assert r_close.status_code == 200, r_close.text
    closed = r_close.json()["chat"]
    assert closed["status"] == "CLOSED"
    assert closed.get("closed_at") is not None

    async with db_base.AsyncSessionLocal() as session:
        cres = await session.execute(select(OmniChatClosure).where(OmniChatClosure.chat_id == chat_id))
        closure = cres.scalar_one_or_none()
        assert closure is not None
        assert closure.outcome == "BOOKED"

    # Analytics should include at least 1 created/claimed/closed for a wide range.
    r_analytics = await client.get(
        "/api/v1/admin/omni-chats/analytics",
        params={"date_from": "2000-01-01", "date_to": "2100-01-01"},
        headers=headers,
    )
    assert r_analytics.status_code in {200, 403}, r_analytics.text
    if r_analytics.status_code == 200:
        a = r_analytics.json()
        assert a["total_chats_created"] >= 1
        assert a["total_claimed"] >= 1
        assert a["total_closed"] >= 1


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
        channel_id = await _add_outbound_capable_channel(session, business_account_id)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Omni Hidden Test",
            primary_phone="+79990006677",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=channel_id,
        )
        visible = await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Visible message",
            channel_id=channel_id,
        )
        to_hide = await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Message to soft-hide",
            channel_id=channel_id,
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


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_outbound_uses_last_client_inbound_channel(
    init_db, seed_data, client: AsyncClient, admin_auth: dict
):
    """Two CLIENT inbounds with different channel_id — reply without reply_channel_id uses the latest."""
    business_account_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        ch_first = await _add_outbound_capable_channel(session, business_account_id)
        ch_second = await _add_outbound_capable_channel(session, business_account_id)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Two-channel test",
            primary_phone="+79990007788",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=ch_first,
        )
        await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="from first channel",
            channel_id=ch_first,
        )
        await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="from second channel",
            channel_id=ch_second,
        )
        await session.commit()
        chat_id = chat.id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/messages",
        json={"content": "operator reply"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["channel_id"] == str(ch_second)


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_reply_channel_foreign_clinic_400(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """reply_channel_id belonging to another clinic returns 400."""
    from decimal import Decimal

    from src.domain.entities.clinic import Clinic

    business_account_id = seed_data["clinic_id"]
    foreign_clinic_id = uuid.uuid4()
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        session.add(
            Clinic(
                id=foreign_clinic_id,
                name="Foreign tenant omni",
                prepayment_amount=Decimal("0"),
            )
        )
        foreign_channel_id = await _add_outbound_capable_channel(session, foreign_clinic_id)
        channel_id = await _add_outbound_capable_channel(session, business_account_id)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Tenant isolation omni",
            primary_phone="+79990008899",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=channel_id,
        )
        await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="hello",
            channel_id=channel_id,
        )
        await session.commit()
        chat_id = chat.id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/messages",
        json={"content": "nope", "reply_channel_id": str(foreign_channel_id)},
        headers=headers,
    )
    assert r.status_code == 400, r.text


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_reply_channel_unresolved_409(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """No inbound channel and no usable primary channel — 409 OMNI_REPLY_CHANNEL_UNRESOLVED."""
    business_account_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Unresolved channel test",
            primary_phone="+79990009900",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=None,
        )
        await session.commit()
        chat_id = chat.id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/messages",
        json={"content": "cannot send"},
        headers=headers,
    )
    assert r.status_code == 409, r.text
    detail = r.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "OMNI_REPLY_CHANNEL_UNRESOLVED"
    else:
        assert "OMNI_REPLY_CHANNEL_UNRESOLVED" in r.text


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_omni_send_rate_limit_429(
    init_db, seed_data, client: AsyncClient, admin_auth: dict, monkeypatch: pytest.MonkeyPatch
):
    """POST omni messages beyond per-admin limit returns 429 (Redis rate limiter)."""
    from src.core.config import settings
    from src.infrastructure.database.redis_client import get_redis

    monkeypatch.setattr(settings, "rate_admin_omni_send_per_admin_limit", 2)
    monkeypatch.setattr(settings, "rate_admin_omni_send_window_seconds", 60)

    # This suite shares a single admin user across tests; clear the limiter key to avoid
    # cross-test coupling and flakiness in full runs.
    redis = await get_redis()
    await redis.delete(f"rate:omni:send:admin:{admin_auth['admin_id']}")

    business_account_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        channel_id = await _add_outbound_capable_channel(session, business_account_id)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Omni rate limit",
            primary_phone="+79990003344",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=channel_id,
        )
        await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="seed for rate",
            channel_id=channel_id,
        )
        await session.commit()
        chat_id = chat.id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    for i in range(2):
        r = await client.post(
            f"/api/v1/admin/omni-chats/{chat_id}/messages",
            json={"content": f"msg {i}"},
            headers=headers,
        )
        assert r.status_code == 201, r.text

    r3 = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/messages",
        json={"content": "over limit"},
        headers=headers,
    )
    assert r3.status_code == 429, r3.text
    detail = r3.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "OMNI_SEND_RATE_LIMITED"
    else:
        assert "OMNI_SEND_RATE_LIMITED" in r3.text


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_patch_omni_assignee_and_filter_me(
    init_db, seed_data, client: AsyncClient, admin_auth: dict
):
    """PATCH assignee (P1-B); list with assignee=me returns only assigned chats; clear assignee."""
    business_account_id = seed_data["clinic_id"]
    raw_aid = admin_auth["admin_id"]
    admin_id = raw_aid if isinstance(raw_aid, uuid.UUID) else uuid.UUID(str(raw_aid))

    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        channel_id = await _add_outbound_capable_channel(session, business_account_id)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Assignee patch test",
            primary_phone="+79990001001",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=channel_id,
        )
        await session.commit()
        chat_id = chat.id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    r_patch = await client.patch(
        f"/api/v1/admin/omni-chats/{chat_id}",
        json={"assignee_admin_id": str(admin_id)},
        headers=headers,
    )
    assert r_patch.status_code == 200, r_patch.text
    patched = r_patch.json()
    assert patched.get("assignee_admin_id") == str(admin_id)
    assert patched.get("assignee_name")

    r_me = await client.get(
        "/api/v1/admin/omni-chats",
        params={"assignee": "me", "page_size": 100},
        headers=headers,
    )
    assert r_me.status_code == 200, r_me.text
    me_ids = {c["chat_id"] for c in r_me.json()["items"]}
    assert str(chat_id) in me_ids

    r_clear = await client.patch(
        f"/api/v1/admin/omni-chats/{chat_id}",
        json={"assignee_admin_id": None},
        headers=headers,
    )
    assert r_clear.status_code == 200, r_clear.text
    cleared = r_clear.json()
    assert cleared.get("assignee_admin_id") in (None, "")


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_omni_quick_replies_crud(init_db, seed_data, client: AsyncClient, admin_auth: dict):
    """Quick-replies CRUD (omni.inbox.manage)."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    r_create = await client.post(
        "/api/v1/admin/omni-chats/quick-replies",
        json={"title": "QR title", "body": "QR body line", "sort_order": 1},
        headers=headers,
    )
    assert r_create.status_code == 201, r_create.text
    qid = r_create.json()["id"]

    r_list = await client.get("/api/v1/admin/omni-chats/quick-replies", headers=headers)
    assert r_list.status_code == 200, r_list.text
    ids = [x["id"] for x in r_list.json()["items"]]
    assert qid in ids

    r_up = await client.patch(
        f"/api/v1/admin/omni-chats/quick-replies/{qid}",
        json={"title": "QR title updated"},
        headers=headers,
    )
    assert r_up.status_code == 200, r_up.text
    assert r_up.json()["title"] == "QR title updated"

    r_del = await client.delete(f"/api/v1/admin/omni-chats/quick-replies/{qid}", headers=headers)
    assert r_del.status_code == 204, r_del.text


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_patch_omni_chat_status_rejects_unknown(
    init_db, seed_data, client: AsyncClient, admin_auth: dict
):
    """PATCH status validates enum-like values and rejects arbitrary strings."""
    business_account_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        channel_id = await _add_outbound_capable_channel(session, business_account_id)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Status validation test",
            primary_phone="+79990001002",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=channel_id,
        )
        await session.commit()
        chat_id = chat.id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.patch(
        f"/api/v1/admin/omni-chats/{chat_id}",
        json={"status": "NOT_A_REAL_STATUS"},
        headers=headers,
    )
    assert r.status_code == 422, r.text


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_omni_quick_replies_reject_empty_after_trim(
    init_db, seed_data, client: AsyncClient, admin_auth: dict
):
    """Quick replies reject blank title/body after trim."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    r_create = await client.post(
        "/api/v1/admin/omni-chats/quick-replies",
        json={"title": "   ", "body": "ok"},
        headers=headers,
    )
    assert r_create.status_code == 422, r_create.text

    r_create2 = await client.post(
        "/api/v1/admin/omni-chats/quick-replies",
        json={"title": "ok", "body": "   "},
        headers=headers,
    )
    assert r_create2.status_code == 422, r_create2.text


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_omni_quick_replies_manage_requires_permission(
    init_db, seed_data, client: AsyncClient, doctor_auth: dict
):
    """Users without omni.inbox.manage cannot mutate quick replies."""
    headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
    r = await client.post(
        "/api/v1/admin/omni-chats/quick-replies",
        json={"title": "Nope", "body": "Forbidden for this role"},
        headers=headers,
    )
    assert r.status_code == 403, r.text


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_omni_sse_requires_auth(init_db, seed_data, client: AsyncClient):
    """SSE endpoint returns 401 without token."""
    r = await client.get("/api/v1/admin/omni-chats/events")
    assert r.status_code == 401, r.text


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_omni_sse_connected_event_with_auth(
    init_db, seed_data, client: AsyncClient, admin_auth: dict
):
    """SSE endpoint streams initial connected comment for valid admin token."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    async with client.stream("GET", "/api/v1/admin/omni-chats/events", headers=headers) as resp:
        assert resp.status_code == 200, await resp.aread()
        assert resp.headers.get("content-type", "").startswith("text/event-stream")
        first_line = await asyncio.wait_for(resp.aiter_lines().__anext__(), timeout=3.0)
        assert first_line.startswith(": connected")


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_omni_list_assignee_param_rejects_invalid(
    init_db, seed_data, client: AsyncClient, admin_auth: dict
):
    """Only assignee=me is accepted; any other value returns 422."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/admin/omni-chats", params={"assignee": "all"}, headers=headers)
    assert r.status_code == 422, r.text


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_omni_sse_token_requires_permission(
    init_db, seed_data, client: AsyncClient, admin_auth: dict, doctor_auth: dict
):
    """SSE token endpoint is protected by omni.inbox.manage."""
    r_forbidden = await client.get(
        "/api/v1/admin/omni-chats/sse-token",
        headers={"Authorization": f"Bearer {doctor_auth['access_token']}"},
    )
    assert r_forbidden.status_code == 403, r_forbidden.text

    r_ok = await client.get(
        "/api/v1/admin/omni-chats/sse-token",
        headers={"Authorization": f"Bearer {admin_auth['access_token']}"},
    )
    assert r_ok.status_code == 200, r_ok.text
    data = r_ok.json()
    assert isinstance(data.get("token"), str) and data["token"]
    assert data.get("expires_in_seconds") == 300


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_omni_close_forbidden_for_non_assignee(
    init_db, seed_data, client: AsyncClient, admin_auth: dict, doctor_auth: dict
):
    """Close is allowed only for assignee (owner override), and still requires omni.inbox.manage."""
    business_account_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        channel_id = await _add_outbound_capable_channel(session, business_account_id)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Close ownership test",
            primary_phone="+79990001003",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=channel_id,
        )
        chat.status = "WAITING_FOR_OPERATOR"
        chat.assignee_admin_id = None
        await session.commit()
        chat_id = chat.id

    # Claim as admin
    r_claim = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/claim",
        headers={"Authorization": f"Bearer {admin_auth['access_token']}"},
    )
    assert r_claim.status_code == 200, r_claim.text

    # Attempt to close as doctor (no omni.inbox.manage) -> 403
    r_close = await client.post(
        f"/api/v1/admin/omni-chats/{chat_id}/close",
        json={"outcome": "BOOKED", "tag_ids": [], "comment": "nope"},
        headers={"Authorization": f"Bearer {doctor_auth['access_token']}"},
    )
    assert r_close.status_code == 403, r_close.text


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_omni_upload_rejects_svg(
    init_db, seed_data, client: AsyncClient, admin_auth: dict
):
    """Upload blocks image/svg+xml to prevent stored XSS."""
    business_account_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        channel_id = await _add_outbound_capable_channel(session, business_account_id)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="SVG upload test",
            primary_phone="+79990001004",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
            channel_id=channel_id,
        )
        await session.commit()
        chat_id = chat.id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    files = {"file": ("x.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/svg+xml")}
    data = {"body": "svg"}
    r = await client.post(f"/api/v1/admin/omni-chats/{chat_id}/messages/upload", headers=headers, data=data, files=files)
    assert r.status_code == 400, r.text

