"""Security tests specific to AI agent (run_ai_agent) behaviour."""

import json
from datetime import datetime

import pytest
from sqlalchemy import select

from src.application.services.omnichannel_ai_orchestrator import OmnichannelAIOrchestrator
from src.core.context import RequestContext
from src.domain.entities.clinic_ai_settings import ClinicAiSettings
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.infrastructure.database import base as db_base


class RecordingStubAiClient:
    """Stub AiClient that records messages payloads to verify sanitization."""

    def __init__(self, response):
        self._response = response
        self.seen_payloads: list[dict] = []

    def is_configured(self) -> bool:
        return True

    async def complete(self, payload: dict) -> dict:
        self.seen_payloads.append(payload)
        return self._response

    async def chat_with_tools(self, messages, tools_schema=None, tool_choice=None):
        # For security tests we care mostly about payload of first call.
        payload = {
            "model": "test-model",
            "messages": [m.model_dump() for m in messages],
        }
        self.seen_payloads.append(payload)
        return self._response, []


async def _make_chat_with_pd(session, business_account_id):
    """Create chat where inbound message contains phone/email to test masking."""
    contact = OmniContact(
        business_account_id=business_account_id,
        full_name="PD Test",
        primary_phone="+79001234567",
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
        content="Мой телефон +7 900 123-45-67 и почта test@example.com",
        created_at=datetime.utcnow(),
    )
    session.add(inbound)
    await session.flush()

    return chat, contact, inbound


@pytest.mark.asyncio
async def test_run_ai_agent_sanitizes_personal_data_when_not_allowed(
    init_db, seed_data, redis_client, monkeypatch
):
    """When allow_personal_data=False, outbound payload to AI must be sanitized."""
    clinic_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        # Ensure ClinicAiSettings exist with ai_enabled=False and external provider
        existing = await session.execute(
            select(ClinicAiSettings).where(ClinicAiSettings.clinic_id == clinic_id)
        )
        row = existing.scalar_one_or_none()
        if row is None:
            row = ClinicAiSettings(
                clinic_id=clinic_id,
                ai_enabled=False,
                ai_provider_type="external",
            )
            session.add(row)
            await session.flush()
        else:
            row.ai_enabled = False
            row.ai_provider_type = "external"
            await session.flush()

        chat, contact, inbound = await _make_chat_with_pd(session, business_account_id=clinic_id)

        ai_response = {
            "choices": [
                {
                    "message": {
                        "content": "Ответ без использования PD.",
                        "tool_calls": [],
                    },
                }
            ]
        }
        stub_client = RecordingStubAiClient(ai_response)

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

        await orchestrator.run_ai_agent(
            chat=chat,
            incoming_message=inbound,
            request_context=ctx,
        )

        assert stub_client.seen_payloads, "Expected at least one payload recorded"
        serialized = json.dumps(stub_client.seen_payloads, ensure_ascii=False)
        # Original phone/email must not appear in payloads
        assert "+7 900 123-45-67" not in serialized
        assert "test@example.com" not in serialized
        # Instead we expect masked placeholders
        assert "[PHONE]" in serialized or "[EMAIL]" in serialized


@pytest.mark.asyncio
async def test_run_ai_agent_respects_clinic_boundary_in_tools(
    init_db, seed_data, redis_client, monkeypatch
):
    """Tools invoked by agent must not operate on foreign clinic data."""
    clinic_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        chat, contact, inbound = await _make_chat_with_pd(session, business_account_id=clinic_id)

        # Tool call with wrong clinic_id in arguments – tools should return clinic_mismatch.
        from uuid import uuid4

        foreign_clinic_id = uuid4()

        tool_call = {
            "id": "call_foreign",
            "function": {
                "name": "get_available_slots",
                "arguments": json.dumps(
                    {
                        "clinic_id": str(foreign_clinic_id),
                        "doctor_id": str(seed_data["doctor_id"]),
                        "service_id": str(seed_data["service_id"]),
                        "date_from": seed_data["date"].isoformat(),
                        "date_to": seed_data["date"].isoformat(),
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
                        "content": "Техническая ошибка, администратор свяжется с вами.",
                        "tool_calls": [],
                    },
                }
            ]
        }
        from src.application.dto.chat_ai_agent_dto import ToolCall

        # Use simple stub that reuses run_ai_agent expectations
        class SimpleStubAiClient:
            def __init__(self):
                self.calls = 0

            def is_configured(self) -> bool:
                return True

            async def complete(self, payload: dict) -> dict:
                return first_response if self.calls == 0 else final_response

            async def chat_with_tools(self, messages, tools_schema=None, tool_choice=None):
                self.calls += 1
                if self.calls == 1:
                    # First call returns tool_call
                    return first_response, [
                        ToolCall(
                            id=tool_call["id"],
                            name=tool_call["function"]["name"],
                            arguments_json=tool_call["function"]["arguments"],
                        )
                    ]
                return final_response, []

        stub_client = SimpleStubAiClient()

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

        # Expect at least one tool_event with clinic_mismatch
        assert any(
            e.get("tool") == "get_available_slots"
            and e.get("status") == "error"
            and e.get("code") == "clinic_mismatch"
            for e in result.tool_events
        )

