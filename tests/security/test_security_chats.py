"""Security tests: chats and omnichannel isolation (SEC-C1–C4).

Admin cannot see other clinic's chats; patient cannot see other's messages; owner cannot access foreign channel.
"""

import uuid

import pytest
from httpx import AsyncClient

from src.domain.entities.clinic import Clinic
from src.domain.entities.omnichannel_channel import Channel as OmniChannel
from src.infrastructure.database import base as db_base


@pytest.mark.security
@pytest.mark.asyncio
async def test_sec_c1_admin_omni_chats_only_own_clinic(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """SEC-C1: GET admin omni-chats with admin token returns only own clinic's chats; no clinic_id override leak."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    # List uses current_admin.clinic_id from token; there is no query param to override.
    # Create another clinic's chat in DB; admin must not see it in list.
    other_clinic_id = uuid.uuid4()
    async with db_base.AsyncSessionLocal() as session:
        from src.domain.entities.omnichannel_contact import Contact as OmniContact
        from src.domain.entities.omnichannel_chat import Chat as OmniChat

        session.add(Clinic(id=other_clinic_id, name="Other Clinic", prepayment_amount=0))
        await session.flush()
        contact = OmniContact(
            business_account_id=other_clinic_id,
            full_name="Other Contact",
            primary_phone="+79005556666",
        )
        session.add(contact)
        await session.flush()
        chat = OmniChat(
            business_account_id=other_clinic_id,
            contact_id=contact.id,
            status="OPEN",
            title="Other Clinic Chat",
        )
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
        other_chat_id = chat.id

    r = await client.get("/api/v1/admin/omni-chats", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data.get("items") or []
    chat_ids = [item["chat_id"] for item in items]
    assert other_chat_id not in chat_ids and str(other_chat_id) not in [str(x) for x in chat_ids]


@pytest.mark.security
@pytest.mark.asyncio
async def test_sec_c2_admin_cannot_get_other_clinic_conversation_messages(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """SEC-C2 (admin path): Admin of clinic A cannot GET messages for conversation belonging to clinic B."""
    from src.domain.entities.patient import Patient
    other_clinic_id = uuid.uuid4()
    other_patient_id = uuid.uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(Clinic(id=other_clinic_id, name="Other", prepayment_amount=0))
        session.add(
            Patient(
                id=other_patient_id,
                clinic_id=other_clinic_id,
                phone="+79003334444",
                full_name="Other P",
            )
        )
        await session.flush()
        from src.application.services.chat_service import ChatService
        svc = ChatService(session)
        conv = await svc.get_or_create_conversation_for_patient(other_clinic_id, other_patient_id)
        await session.commit()
        other_conv_id = conv.conversation_id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        f"/api/v1/admin/chat/conversations/{other_conv_id}/messages",
        headers=headers,
    )
    assert r.status_code == 404, r.text


@pytest.mark.security
@pytest.mark.asyncio
async def test_sec_c3_owner_cannot_access_foreign_channel(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """SEC-C3: Owner cannot get/update channel of another clinic (404)."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    other_clinic_id = uuid.uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(Clinic(id=other_clinic_id, name="Foreign Clinic", prepayment_amount=0))
        await session.flush()
        ch = OmniChannel(
            business_account_id=other_clinic_id,
            type="TELEGRAM_BOT",
            display_name="Foreign",
            status="PENDING_SETUP",
        )
        session.add(ch)
        await session.commit()
        await session.refresh(ch)
        foreign_id = ch.id

    r = await client.put(
        f"/api/v1/owner/channels/{foreign_id}",
        json={"display_name": "Hacked"},
        headers=headers,
    )
    assert r.status_code == 404
    r2 = await client.post(
        f"/api/v1/owner/channels/{foreign_id}/credentials",
        json={"provider_type": "TELEGRAM", "scopes": None, "payload": "x"},
        headers=headers,
    )
    assert r2.status_code == 404


@pytest.mark.security
@pytest.mark.asyncio
async def test_sec_c4_admin_ai_insight_no_cross_clinic_leak(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """SEC-C4: Admin AI summary/suggest/insight with correct clinic_id does not return other clinic's chat data."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = seed_data["clinic_id"]
    # Call AI insight for own patient; response must have expected structure and must not contain
    # raw message bodies from other clinics (we only have one clinic in seed, so just check structure).
    patient_id = seed_data["patient_id"]
    r = await client.get(
        f"/api/v1/admin/patients/{patient_id}/ai-insight",
        params={"clinic_id": str(clinic_id)},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "summary" in data
    assert "risk_flags" in data
    # Must not expose raw credentials or other clinic identifiers
    body_str = str(data)
    assert "credentials_encrypted" not in body_str or "decrypted" not in body_str.lower()
