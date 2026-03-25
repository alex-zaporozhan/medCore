"""Integration-style tests for OmnichannelAIOrchestrator.run_ai_agent (function-calling agent)."""

import json
from datetime import datetime

import pytest
from sqlalchemy import select

from src.application.dto.chat_ai_agent_dto import AgentResult, ToolCall
from src.application.services.omnichannel_ai_orchestrator import (
    OmnichannelAIOrchestrator,
)
from src.core.context import RequestContext
from src.domain.entities.ai_tool_event import AiToolEvent
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.infrastructure.database import base as db_base


class StubAiClient:
    """Stub AiClient for testing run_ai_agent with predefined tool_calls behaviour."""

    def __init__(self, scenarios):
        """
        scenarios: list of tuples (with_tools: bool, response: dict, tool_calls: list[dict])
        Each call to chat_with_tools pops next scenario.
        """
        self._scenarios = list(scenarios)

    def is_configured(self) -> bool:
        return True

    async def complete(self, payload: dict) -> dict:
        # Not used directly in tests, but real AiClient exposes it; implement minimal stub.
        return {}

    async def chat_with_tools(self, messages, tools_schema=None, tool_choice=None):
        if not self._scenarios:
            return {"choices": [{"message": {"content": "stub fallback"}}]}, []
        _, response, tool_calls = self._scenarios.pop(0)
        normalized: list[ToolCall] = []
        for tc in tool_calls:
            if isinstance(tc, ToolCall):
                normalized.append(tc)
                continue
            if isinstance(tc, dict):
                fn = tc.get("function") or {}
                normalized.append(
                    ToolCall(
                        id=str(tc.get("id") or ""),
                        name=str(fn.get("name") or ""),
                        arguments_json=str(fn.get("arguments") or "{}"),
                    )
                )
        return response, normalized


async def _make_chat_and_message(session, business_account_id):
    """Helper to create minimal omnichannel chat/contact/message set."""
    contact = OmniContact(
        business_account_id=business_account_id,
        full_name="Agent Test Contact",
        primary_phone="+79999999999",
    )
    session.add(contact)
    await session.flush()

    chat = OmniChat(
        business_account_id=business_account_id,
        contact_id=contact.id,
        channel_id=None,
        status="OPEN",
        ai_mode="AUTO_REPLY",
    )
    session.add(chat)
    await session.flush()

    inbound = OmniMessage(
        chat_id=chat.id,
        contact_id=contact.id,
        channel_id=None,
        direction="INBOUND",
        actor_type="CLIENT",
        content_type="TEXT",
        content="Запишите меня к врачу завтра.",
        created_at=datetime.utcnow(),
    )
    session.add(inbound)
    await session.flush()

    return chat, contact, inbound


@pytest.mark.asyncio
async def test_run_ai_agent_text_only_reply(init_db, seed_data, redis_client, monkeypatch):
    """Agent should handle case when LLM returns only text without tool_calls."""
    clinic_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        chat, contact, inbound = await _make_chat_and_message(session, business_account_id=clinic_id)

        # Stub AiClient: first call returns plain text, no tool_calls; final call also plain text.
        first_response = {
            "choices": [
                {
                    "message": {
                        "content": "Мы можем предложить вам несколько вариантов записи.",
                        "tool_calls": [],
                    },
                }
            ]
        }
        final_response = {
            "choices": [
                {
                    "message": {
                        "content": "Запишем вас на ближайшее удобное время.",
                        "tool_calls": [],
                    },
                }
            ]
        }
        stub_client = StubAiClient(
            scenarios=[
                (True, first_response, []),
                (False, final_response, []),
            ]
        )

        # Patch AiClient used by build_safe_ai_client (factory holds its own import ref).
        from src.application.services import ai_client_factory as ai_client_factory_module

        monkeypatch.setattr(ai_client_factory_module, "AiClient", lambda config=None, timeout=None: stub_client)

        orchestrator = OmnichannelAIOrchestrator(session)
        ctx = RequestContext(
            clinic_id=clinic_id,
            user_id=None,
            user_type="system",
            roles=set(),
            permissions={"booking.ai_tools.use"},
        )

        result = await orchestrator.run_ai_agent(
            chat=chat,
            incoming_message=inbound,
            request_context=ctx,
        )

        assert isinstance(result, AgentResult)
        assert result.error is None
        assert "Запишем вас" in result.reply_message.content

        # Ensure outbound AI message was written
        res_msgs = await session.execute(
            select(OmniMessage).where(OmniMessage.chat_id == chat.id).order_by(OmniMessage.created_at)
        )
        msgs = list(res_msgs.scalars().all())
        assert any(m.direction == "OUTBOUND" and m.actor_type == "AI" for m in msgs)


@pytest.mark.asyncio
async def test_run_ai_agent_with_get_available_slots_tool(init_db, seed_data, redis_client, monkeypatch):
    """Agent should execute get_available_slots tool and record AiToolEvent."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        chat, contact, inbound = await _make_chat_and_message(session, business_account_id=clinic_id)

        tool_call = {
            "id": "call_1",
            "function": {
                "name": "get_available_slots",
                "arguments": json.dumps(
                    {
                        "clinic_id": str(clinic_id),
                        "doctor_id": str(doctor_id),
                        "service_id": str(service_id),
                        "date_from": day.isoformat(),
                        "date_to": day.isoformat(),
                    }
                ),
            },
        }
        first_response = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [tool_call],
                    },
                }
            ]
        }
        final_response = {
            "choices": [
                {
                    "message": {
                        "content": "Вот доступные слоты для записи.",
                        "tool_calls": [],
                    },
                }
            ]
        }
        stub_client = StubAiClient(
            scenarios=[
                (True, first_response, [tool_call]),
                (False, final_response, []),
            ]
        )

        from src.application.services import ai_client_factory as ai_client_factory_module

        monkeypatch.setattr(ai_client_factory_module, "AiClient", lambda config=None, timeout=None: stub_client)

        orchestrator = OmnichannelAIOrchestrator(session)
        ctx = RequestContext(
            clinic_id=clinic_id,
            user_id=None,
            user_type="system",
            roles=set(),
            permissions={"booking.ai_tools.use"},
        )

        result = await orchestrator.run_ai_agent(
            chat=chat,
            incoming_message=inbound,
            request_context=ctx,
        )

        assert isinstance(result, AgentResult)
        assert result.error is None

        # Tool events should include success for get_available_slots
        assert any(e.get("tool") == "get_available_slots" and e.get("status") == "success" for e in result.tool_events)

        # AiToolEvent persisted
        db_events = await session.execute(select(AiToolEvent).where(AiToolEvent.chat_id == chat.id))
        events = list(db_events.scalars().all())
        assert any(e.tool_name == "get_available_slots" for e in events)


@pytest.mark.asyncio
async def test_run_ai_agent_create_booking_success_and_conflict(init_db, seed_data, redis_client, monkeypatch):
    """Agent should create booking via create_booking tool and handle slot_conflict on second attempt."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        chat, contact, inbound = await _make_chat_and_message(session, business_account_id=clinic_id)

        # First, we need a concrete appointment_start from schedule_service inside orchestrator tools.
        # For stub we pass approximate datetime; actual slot mapping is handled by tool logic.
        appointment_start = datetime.combine(day, datetime.min.time())

        create_args = {
            "clinic_id": str(clinic_id),
            "patient_id": str(patient_id),
            "doctor_id": str(doctor_id),
            "service_id": str(service_id),
            "appointment_start": appointment_start.isoformat(),
            "source": "ai_agent",
        }

        tool_call_success = {
            "id": "call_create_1",
            "function": {
                "name": "create_booking",
                "arguments": json.dumps(create_args),
            },
        }
        tool_call_conflict = {
            "id": "call_create_2",
            "function": {
                "name": "create_booking",
                "arguments": json.dumps(create_args),
            },
        }

        first_response = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [tool_call_success],
                    },
                }
            ]
        }
        # Second LLM call after tools: ask for no more tools, text only
        final_response = {
            "choices": [
                {
                    "message": {
                        "content": "Запись успешно создана.",
                        "tool_calls": [],
                    },
                }
            ]
        }

        stub_client = StubAiClient(
            scenarios=[
                (True, first_response, [tool_call_success]),
                (False, final_response, []),
            ]
        )

        from src.application.services import ai_client_factory as ai_client_factory_module

        monkeypatch.setattr(ai_client_factory_module, "AiClient", lambda config=None, timeout=None: stub_client)

        orchestrator = OmnichannelAIOrchestrator(session)
        ctx = RequestContext(
            clinic_id=clinic_id,
            user_id=None,
            user_type="system",
            roles={"admin"},
            permissions={"booking.ai_tools.use"},
        )

        result = await orchestrator.run_ai_agent(
            chat=chat,
            incoming_message=inbound,
            request_context=ctx,
        )

        assert isinstance(result, AgentResult)
        assert result.error is None
        assert any(e.get("tool") == "create_booking" and e.get("status") == "success" for e in result.tool_events)

        # Now simulate second agent run that hits same slot to trigger slot_conflict
        # Reuse same stub, but its first call will again attempt create_booking on same args.
        stub_client_conflict = StubAiClient(
            scenarios=[
                (True, first_response, [tool_call_conflict]),
                (False, final_response, []),
            ]
        )
        monkeypatch.setattr(ai_client_factory_module, "AiClient", lambda config=None, timeout=None: stub_client_conflict)

        result2 = await orchestrator.run_ai_agent(
            chat=chat,
            incoming_message=inbound,
            request_context=ctx,
        )

        assert isinstance(result2, AgentResult)
        # Expect at least one ToolError event with slot_conflict
        assert any(
            e.get("tool") == "create_booking" and e.get("status") == "error" for e in result2.tool_events
        )

