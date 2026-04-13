import uuid
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from src.api.v1.routers.admin_lead_logs import lead_logs_stats
from src.api.v1.routers.admin_omni_chat import _resolve_chat_to_lead_log_task
from src.core.context import RequestContext
from src.infrastructure.database import base as db_base
from src.domain.entities.omni_chat_lease import OmniChatLease
from src.domain.entities.omni_lead_log import OmniLeadLog
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_contact import Contact as OmniContact


@pytest.mark.asyncio
async def test_admin_lead_logs_stats_returns_counts(init_db, seed_data):
    clinic_id = seed_data["clinic_id"]
    admin_id = seed_data["admin_id"]

    async with db_base.AsyncSessionLocal() as session:
        c1 = OmniContact(business_account_id=clinic_id, full_name="Stats A", primary_phone="+70000000001")
        c2 = OmniContact(business_account_id=clinic_id, full_name="Stats B", primary_phone="+70000000002")
        session.add_all([c1, c2])
        await session.flush()
        chat1 = OmniChat(business_account_id=clinic_id, contact_id=c1.id)
        chat2 = OmniChat(business_account_id=clinic_id, contact_id=c2.id)
        session.add_all([chat1, chat2])
        await session.flush()
        now = datetime.utcnow()
        session.add_all(
            [
                OmniLeadLog(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    omni_chat_id=chat1.id,
                    contact_id=c1.id,
                    opened_by_admin_id=admin_id,
                    opened_at=now - timedelta(minutes=30),
                    closed_at=now - timedelta(minutes=5),
                    title="A",
                    outcome="BOOKED",
                    transcript_text="",
                    transcript_json={},
                ),
                OmniLeadLog(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    omni_chat_id=chat2.id,
                    contact_id=c2.id,
                    opened_by_admin_id=admin_id,
                    opened_at=now - timedelta(minutes=20),
                    closed_at=now - timedelta(minutes=2),
                    title="B",
                    outcome="NOT_BOOKED",
                    transcript_text="",
                    transcript_json={},
                ),
            ]
        )
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        ctx = RequestContext(
            clinic_id=clinic_id,
            user_id=admin_id,
            user_type="admin",
            roles={"owner"},
            permissions={"leads.log.view"},
        )
        stats = await lead_logs_stats(
            date_from="2000-01-01",
            date_to="2100-01-01",
            session=session,
            admin_ctx=ctx,  # type: ignore[arg-type]
        )

    assert stats.total >= 2
    outcomes = {row.outcome: row.count for row in stats.by_outcome}
    assert outcomes.get("BOOKED", 0) >= 1
    assert outcomes.get("NOT_BOOKED", 0) >= 1


@pytest.mark.asyncio
async def test_admin_resolve_conflicts_on_active_lease_unless_force(init_db, seed_data):
    clinic_id = seed_data["clinic_id"]
    admin_id = seed_data["admin_id"]

    async with db_base.AsyncSessionLocal() as session:
        contact = OmniContact(business_account_id=clinic_id, full_name="Lease Guard", primary_phone="+70000000003")
        session.add(contact)
        await session.flush()
        chat = OmniChat(business_account_id=clinic_id, contact_id=contact.id)
        session.add(chat)
        await session.flush()
        chat.assignee_admin_id = admin_id
        chat.status = "IN_PROGRESS"
        await session.flush()

        now = datetime.utcnow()
        session.add(
            OmniChatLease(
                clinic_id=clinic_id,
                chat_id=chat.id,
                admin_id=admin_id,
                tab_id="tab_test",
                expires_at=now + timedelta(seconds=90),
                last_heartbeat_at=now,
            )
        )
        await session.commit()
        chat_id = chat.id

    ctx = RequestContext(
        clinic_id=clinic_id,
        user_id=admin_id,
        user_type="admin",
        roles={"owner"},
        permissions={"omni.inbox.manage", "omni.chat.resolve.override"},
    )

    async with db_base.AsyncSessionLocal() as session:
        with pytest.raises(HTTPException) as e:
            await _resolve_chat_to_lead_log_task(
                chat_id=chat_id,
                session=session,
                admin_ctx=ctx,  # type: ignore[arg-type]
                force=False,
            )
        assert e.value.status_code == 409
        assert isinstance(e.value.detail, dict)
        assert e.value.detail.get("code") == "omni_chat_active_lease"

    async with db_base.AsyncSessionLocal() as session:
        dto = await _resolve_chat_to_lead_log_task(
            chat_id=chat_id,
            session=session,
            admin_ctx=ctx,  # type: ignore[arg-type]
            force=True,
        )
        assert dto.lead_log_id
        # Route uses get_session → commit at end; raw session must commit or the row never persists.
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        res = await session.execute(
            select(OmniLeadLog).where(OmniLeadLog.omni_chat_id == chat_id, OmniLeadLog.clinic_id == clinic_id)
        )
        assert res.scalar_one_or_none() is not None

