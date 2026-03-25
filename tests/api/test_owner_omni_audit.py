"""Tests for Owner omnichannel audit log API (Phase 3 Review)."""

import pytest
from httpx import AsyncClient

from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_owner_audit_log_list_and_filters(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    """GET /owner/audit-log returns entries for current business; filters by type, actor, dates work."""
    business_account_id = seed_data["clinic_id"]
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Create chat + message and soft-hide it to produce an audit log entry
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelChatService(session)
        contact = await service.create_contact(
            business_account_id=business_account_id,
            full_name="Audit Test",
            primary_phone="+79990007777",
        )
        chat = await service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
        )
        msg = await service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Message for audit test",
        )
        await service.soft_hide_message(
            business_account_id=business_account_id,
            message=msg,
            reason="test audit log",
            actor_id=None,
            actor_type="SYSTEM",
        )
        await session.commit()

    # List audit log
    r = await client.get("/api/v1/owner/audit-log", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    items = data["items"]
    assert len(items) >= 1
    entry = next((e for e in items if e.get("action_type") == "MESSAGE_SOFT_HIDE"), None)
    assert entry is not None
    assert entry["business_account_id"] == str(business_account_id)
    assert entry["actor_type"] == "SYSTEM"
    assert entry["target_type"] == "MESSAGE"
    assert "meta" in entry
    assert entry.get("meta", {}).get("reason") == "test audit log"

    # Filter by type
    r_type = await client.get(
        "/api/v1/owner/audit-log",
        params={"type": "MESSAGE_SOFT_HIDE"},
        headers=headers,
    )
    assert r_type.status_code == 200, r_type.text
    type_data = r_type.json()
    assert all(e["action_type"] == "MESSAGE_SOFT_HIDE" for e in type_data["items"])

    # Filter by actor
    r_actor = await client.get(
        "/api/v1/owner/audit-log",
        params={"actor": "SYSTEM"},
        headers=headers,
    )
    assert r_actor.status_code == 200, r_actor.text
    actor_data = r_actor.json()
    assert all(e["actor_type"] == "SYSTEM" for e in actor_data["items"])
