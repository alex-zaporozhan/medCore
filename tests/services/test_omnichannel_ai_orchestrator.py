"""Tests for OmnichannelAIOrchestrator basic modes.

We stub LLMClient to avoid real external calls.
"""


import pytest
from sqlalchemy import select

from src.application.services.omnichannel_ai_orchestrator import (
    LLMClient,
    LLMReply,
    OmnichannelAIOrchestrator,
)
from src.application.services.omnichannel_ai_settings_service import (
    OmnichannelAISettingsService,
)
from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.infrastructure.database import base as db_base


class StubLLMClient(LLMClient):
    def __init__(self, reply: LLMReply | None):
        self._reply = reply

    def is_configured(self) -> bool:  # type: ignore[override]
        return self._reply is not None

    async def generate_reply(self, context):  # type: ignore[override]
        return self._reply


@pytest.mark.asyncio
async def test_ai_orchestrator_disabled_mode_noop(init_db, seed_data):
    """When ai_mode=DISABLED, orchestrator should not create outbound messages."""

    business_account_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        # Prepare chat + inbound message
        chat_service = OmnichannelChatService(session)
        contact = await chat_service.create_contact(
            business_account_id=business_account_id,
            full_name="AI Disabled Test",
            primary_phone="+79990009999",
        )
        chat = await chat_service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
        )
        inbound = await chat_service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Сообщение без AI ответа",
        )

        # No AISettings created => defaults to DISABLED
        orchestrator = OmnichannelAIOrchestrator(session, llm_client=StubLLMClient(None))
        await orchestrator.handle_incoming_for_ai(
            message=inbound,
            chat=chat,
            contact=contact,
        )

        # Ensure only one message exists
        result = await session.execute(
            select(OmniMessage).where(OmniMessage.chat_id == chat.id)
        )
        msgs = list(result.scalars().all())
        assert len(msgs) == 1
        assert msgs[0].direction == "INBOUND"


@pytest.mark.asyncio
async def test_ai_orchestrator_auto_reply_creates_outbound(init_db, seed_data):
    """AUTO_REPLY with confident LLM reply should create outbound AI message."""

    business_account_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        chat_service = OmnichannelChatService(session)
        contact = await chat_service.create_contact(
            business_account_id=business_account_id,
            full_name="AI Auto Test",
            primary_phone="+79990008888",
        )
        chat = await chat_service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
        )
        inbound = await chat_service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Когда вы работаете?",
        )

        # Force deterministic BUSINESS settings even if seed already created a row.
        settings_svc = OmnichannelAISettingsService(session)
        await settings_svc.upsert_settings(
            scope="BUSINESS",
            scope_id=business_account_id,
            data={
                "ai_mode": "AUTO_REPLY",
                "confidence_thresholds": {"auto_reply": 0.3},
            },
        )

        stub_reply = LLMReply(text="Мы работаем ежедневно с 9 до 21.", confidence=0.9, meta={})
        orchestrator = OmnichannelAIOrchestrator(session, llm_client=StubLLMClient(stub_reply))
        await orchestrator.handle_incoming_for_ai(
            message=inbound,
            chat=chat,
            contact=contact,
        )

        result = await session.execute(
            select(OmniMessage).where(OmniMessage.chat_id == chat.id).order_by(OmniMessage.created_at)
        )
        msgs = list(result.scalars().all())
        assert len(msgs) >= 2
        assert msgs[-1].direction == "OUTBOUND"
        assert msgs[-1].actor_type == "AI"
        assert "работаем" in msgs[-1].content


@pytest.mark.asyncio
async def test_ai_orchestrator_suggest_only_creates_template(init_db, seed_data):
    """SUGGEST_ONLY mode should create TEMPLATE draft message."""

    business_account_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        chat_service = OmnichannelChatService(session)
        contact = await chat_service.create_contact(
            business_account_id=business_account_id,
            full_name="AI Suggest Test",
            primary_phone="+79990007777",
        )
        chat = await chat_service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
        )
        inbound = await chat_service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Подскажите стоимость консультации.",
        )

        # Force deterministic mode: business disabled + chat suggest-only override.
        settings_svc = OmnichannelAISettingsService(session)
        await settings_svc.upsert_settings(
            scope="BUSINESS",
            scope_id=business_account_id,
            data={
                "ai_mode": "DISABLED",
                "confidence_thresholds": {"auto_reply": 0.9},
            },
        )
        await settings_svc.upsert_settings(
            scope="CHAT",
            scope_id=chat.id,
            data={
                "ai_mode": "SUGGEST_ONLY",
                "confidence_thresholds": {"auto_reply": 0.8},
            },
        )

        stub_reply = LLMReply(
            text="Предложите клиенту уточнить услугу и сообщите базовую стоимость консультации.",
            confidence=0.6,
            meta={},
        )
        orchestrator = OmnichannelAIOrchestrator(session, llm_client=StubLLMClient(stub_reply))
        await orchestrator.handle_incoming_for_ai(
            message=inbound,
            chat=chat,
            contact=contact,
        )

        result = await session.execute(
            select(OmniMessage).where(OmniMessage.chat_id == chat.id)
        )
        msgs = list(result.scalars().all())
        templates = [m for m in msgs if m.content_type == "TEMPLATE" and m.actor_type == "AI"]
        assert templates, "Expected at least one TEMPLATE AI draft message"


@pytest.mark.asyncio
async def test_legacy_orchestrator_uses_factory_for_safe_client(init_db, seed_data, monkeypatch):
    """Legacy handle_incoming_for_ai path must obtain SafeAiClient via build_safe_ai_client factory."""

    business_account_id = seed_data["clinic_id"]

    # Arrange chat, settings and inbound message similar to SUGGEST_ONLY scenario to hit legacy path.
    async with db_base.AsyncSessionLocal() as session:
        chat_service = OmnichannelChatService(session)
        contact = await chat_service.create_contact(
            business_account_id=business_account_id,
            full_name="AI Legacy Factory Test",
            primary_phone="+79990006666",
        )
        chat = await chat_service.get_or_create_chat(
            business_account_id=business_account_id,
            contact=contact,
        )
        inbound = await chat_service.create_inbound_message(
            chat=chat,
            contact=contact,
            content="Подскажите расписание работы.",
        )

        settings_svc = OmnichannelAISettingsService(session)
        await settings_svc.upsert_settings(
            scope="BUSINESS",
            scope_id=business_account_id,
            data={"ai_mode": "DISABLED"},
        )
        await settings_svc.upsert_settings(
            scope="CHAT",
            scope_id=chat.id,
            data={
                "ai_mode": "SUGGEST_ONLY",
                "confidence_thresholds": {"auto_reply": 0.5},
            },
        )

        # Force use_agent=False so that legacy branch is used.
        from src.application.services import ai_config_service as ai_config_module

        original_get_clinic_ai_config = ai_config_module.AiConfigService.get_clinic_ai_config

        async def fake_get_clinic_ai_config(self, clinic_id):  # type: ignore[unused-argument]
            # Delegate to original implementation; keep monkeypatch deterministic and recursion-safe.
            return await original_get_clinic_ai_config(self, clinic_id)

        monkeypatch.setattr(
            ai_config_module.AiConfigService,
            "get_clinic_ai_config",
            fake_get_clinic_ai_config,
        )

        # Capture calls to build_safe_ai_client from legacy path.
        from src.application.services import omnichannel_ai_orchestrator as orch_module
        from src.application.services.ai_client_factory import SafeAiClientContext

        captured_calls = []

        class StubSafeAiClient:
            def is_configured(self) -> bool:
                return True

            async def complete(self, payload: dict) -> dict:
                # Minimal JSON reply understood by LLMClient.generate_reply
                return {
                    "choices": [
                        {
                            "message": {
                                "content": '{"text": "Работаем ежедневно.", "confidence": 0.95}',
                            }
                        }
                    ]
                }

        async def fake_build_safe_ai_client(*, clinic_id, session):
            captured_calls.append((clinic_id, session))
            return StubSafeAiClient(), SafeAiClientContext(
                clinic_id=clinic_id,
                provider_type="ru_compliant",
                allow_personal_data=True,
            )

        monkeypatch.setattr(orch_module, "build_safe_ai_client", fake_build_safe_ai_client)

        orchestrator = OmnichannelAIOrchestrator(session)

        await orchestrator.handle_incoming_for_ai(
            message=inbound,
            chat=chat,
            contact=contact,
        )

        # Factory must be invoked with correct clinic_id and session.
        assert captured_calls, "Expected factory to be called from legacy path"
        called_clinic_id, called_session = captured_calls[0]
        assert called_clinic_id == business_account_id
        assert called_session is session

        # And legacy LLM path should still create AI suggestion/template.
        result = await session.execute(
            select(OmniMessage).where(OmniMessage.chat_id == chat.id)
        )
        msgs = list(result.scalars().all())
        templates = [m for m in msgs if m.content_type == "TEMPLATE" and m.actor_type == "AI"]
        assert templates, "Expected TEMPLATE AI draft message from legacy path using factory"

