"""Service for batch AI analysis of conversations (conflict coaching)."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Iterable
from uuid import UUID

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.datetime_utils import utc_now
from src.core.ai_sanitizer import AiSanitizer
from src.domain.entities.conversation import Conversation
from src.domain.entities.chat_message import ChatMessage
from src.domain.entities.conversation_ai_analysis import ConversationAiAnalysis
from src.infrastructure.external_apis.safe_ai_client import SafeAiClient
from src.infrastructure.external_apis.ai_client import AiClient, AiClientError

logger = logging.getLogger(__name__)


class ConversationAnalysisService:
    def __init__(self, session: AsyncSession, ai_client: SafeAiClient | None = None) -> None:
        self.session = session
        base_client = AiClient()
        self.ai_client = ai_client or SafeAiClient(base_client, AiSanitizer())

    async def analyze_range(self, clinic_id: UUID, date_from: date, date_to: date) -> None:
        """Analyze conversations in date range and store AI insights."""
        if not self.ai_client.is_configured():
            logger.info("AI provider not configured, skipping conversation analysis", extra={"clinic_id": str(clinic_id)})
            return

        convo_ids = await self._get_conversations_in_range(clinic_id, date_from, date_to)
        if not convo_ids:
            return

        for conv_id in convo_ids:
            try:
                await self._analyze_single(clinic_id, conv_id)
            except Exception:
                logger.exception(
                    "Failed to analyze conversation",
                    extra={"clinic_id": str(clinic_id), "conversation_id": str(conv_id)},
                )

    async def _get_conversations_in_range(
        self,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[UUID]:
        stmt: Select[tuple[UUID]] = (
            select(Conversation.id)
            .where(
                Conversation.clinic_id == clinic_id,
                Conversation.created_at >= date_from,
                Conversation.created_at < date_to,
            )
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def _analyze_single(self, clinic_id: UUID, conversation_id: UUID) -> None:
        # fetch last N messages
        stmt: Select[tuple[ChatMessage]] = (
            select(ChatMessage)
            .where(
                ChatMessage.clinic_id == clinic_id,
                ChatMessage.conversation_id == conversation_id,
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(50)
        )
        result = await self.session.execute(stmt)
        messages: list[ChatMessage] = list(reversed(list(result.scalars().all())))
        if not messages:
            return

        lines: list[str] = []
        sanitizer = AiSanitizer()
        for m in messages:
            role = "КЛИЕНТ" if m.sender_type == "patient" else "АДМИН"
            body = (m.body or "").strip()
            if not body:
                continue
            safe_body = sanitizer.sanitize(body).sanitized
            lines.append(f"{role}: {safe_body}")
        transcript = "\n".join(lines)

        system_prompt = (
            "Ты помогаешь владельцу клиники понять конфликты с клиентами. "
            "На вход даётся один диалог. Верни строго JSON вида: "
            '{"items":[{"conversation_id":"uuid","sentiment":"negative|neutral|positive",'
            '"issue_category":"price|schedule|service|doctor|payment|other","is_conflict":true|false,'
            '"is_resolved":true|false,"admin_mistakes":["..."],"business_root_causes":["..."],'
            '"suggested_playbook":["..."]}],'
            '"summary":{"total":1,"unresolved_conflicts":0,"top_issue_categories":["..."]}} '
            "Ответь только JSON без пояснений."
        )
        user_content = f"Диалог:\n{transcript}"

        payload = {
            "model": settings.ai_provider_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 512,
        }

        try:
            data = await self.ai_client.complete(payload)
        except (AiClientError, Exception):
            logger.exception(
                "AI provider failed while analyzing conversation",
                extra={"clinic_id": str(clinic_id), "conversation_id": str(conversation_id)},
            )
            return

        content = _extract_message_content(data) or ""
        try:
            parsed = json.loads(content)
        except Exception:
            logger.warning(
                "Failed to parse AI analysis JSON",
                extra={"clinic_id": str(clinic_id), "conversation_id": str(conversation_id)},
            )
            return

        items = parsed.get("items") or []
        analysis_date = utc_now().date()
        for item in items:
            try:
                record = ConversationAiAnalysis(
                    clinic_id=clinic_id,
                    conversation_id=conversation_id,
                    analysis_date=analysis_date,
                    sentiment=item.get("sentiment") or "neutral",
                    issue_category=item.get("issue_category") or "other",
                    is_conflict=bool(item.get("is_conflict", False)),
                    is_resolved=bool(item.get("is_resolved", False)),
                    admin_mistakes=item.get("admin_mistakes") or [],
                    business_root_causes=item.get("business_root_causes") or [],
                    suggested_playbook=item.get("suggested_playbook") or [],
                    raw_ai_payload=item,
                )
                self.session.add(record)
            except Exception:
                logger.exception(
                    "Failed to persist AI analysis item",
                    extra={"clinic_id": str(clinic_id), "conversation_id": str(conversation_id)},
                )
        await self.session.flush()


def _extract_message_content(data: dict) -> str:
    """Reuse chat_ai_service helper shape: choices[0].message.content."""
    try:
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        return str(content)
    except Exception:
        return ""

