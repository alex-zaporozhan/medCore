import json

import pytest
from uuid import uuid4


from src.application.services.conversation_analysis_service import ConversationAnalysisService
from src.application.services.ai_client_factory import SafeAiClientContext
from src.core.context import RequestContext
from src.domain.entities.conversation import Conversation
from src.domain.entities.chat_message import ChatMessage
from src.infrastructure.database import base as db_base


class RecordingSafeAiClient:
    """Test double for SafeAiClient that records payloads passed to complete()."""

    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def is_configured(self) -> bool:
        return True

    async def complete(self, payload: dict) -> dict:
        self.payloads.append(payload)
        # Minimal JSON matching expected analysis schema
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "items": [
                                    {
                                        "conversation_id": str(uuid4()),
                                        "sentiment": "neutral",
                                        "issue_category": "other",
                                        "is_conflict": False,
                                        "is_resolved": True,
                                        "admin_mistakes": [],
                                        "business_root_causes": [],
                                        "suggested_playbook": [],
                                    }
                                ],
                                "summary": {
                                    "total": 1,
                                    "unresolved_conflicts": 0,
                                    "top_issue_categories": [],
                                },
                            }
                        )
                    }
                }
            ]
        }


async def _prepare_conversation_with_pd(session, clinic_id):
    convo = Conversation(
        clinic_id=clinic_id,
    )
    session.add(convo)
    await session.flush()

    msg = ChatMessage(
        clinic_id=clinic_id,
        conversation_id=convo.id,
        sender_type="patient",
        body="Мой телефон +7 900 123-45-67 и почта test@example.com",
    )
    session.add(msg)
    await session.flush()
    return convo


@pytest.mark.asyncio
async def test_conversation_analysis_masks_pd_when_not_allowed(init_db, seed_data):
    """When allow_personal_data=False in factory context, PD must be masked in transcript."""

    clinic_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        convo = await _prepare_conversation_with_pd(session, clinic_id)

        ai_client = RecordingSafeAiClient()
        ctx = RequestContext(
            clinic_id=clinic_id,
            user_id=None,
            user_type="system",
            roles=set(),
            permissions=set(),
        )

        service = ConversationAnalysisService(session=session, ctx=ctx, ai_client=ai_client)
        # Emulate factory context with strict PD rules
        service.ai_client_ctx = SafeAiClientContext(
            clinic_id=clinic_id,
            provider_type="external",
            allow_personal_data=False,
        )

        await service._analyze_single(clinic_id=clinic_id, conversation_id=convo.id)

        assert ai_client.payloads, "Expected at least one AI payload"
        serialized = json.dumps(ai_client.payloads, ensure_ascii=False)
        # Original PD must not be present
        assert "+7 900 123-45-67" not in serialized
        assert "test@example.com" not in serialized
        # Masked tokens should be present
        assert "[PHONE]" in serialized or "[EMAIL]" in serialized


@pytest.mark.asyncio
async def test_conversation_analysis_passes_pd_when_allowed(init_db, seed_data):
    """When allow_personal_data=True in factory context, transcript should be pass-through."""

    clinic_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        convo = await _prepare_conversation_with_pd(session, clinic_id)

        ai_client = RecordingSafeAiClient()
        ctx = RequestContext(
            clinic_id=clinic_id,
            user_id=None,
            user_type="system",
            roles=set(),
            permissions=set(),
        )

        service = ConversationAnalysisService(session=session, ctx=ctx, ai_client=ai_client)
        # Emulate factory context with allowed personal data
        service.ai_client_ctx = SafeAiClientContext(
            clinic_id=clinic_id,
            provider_type="ru_compliant",
            allow_personal_data=True,
        )

        await service._analyze_single(clinic_id=clinic_id, conversation_id=convo.id)

        assert ai_client.payloads, "Expected at least one AI payload"
        serialized = json.dumps(ai_client.payloads, ensure_ascii=False)
        # In pass-through mode original PD should remain in payload
        assert "+7 900 123-45-67" in serialized
        assert "test@example.com" in serialized

