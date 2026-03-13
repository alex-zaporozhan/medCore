"""AI Orchestrator for omnichannel assistant (Phase 4).

MVP behaviour:
- reads effective settings (BUSINESS → CHANNEL → CHAT);
- for DISABLED: no-op;
- for AUTO_REPLY: tries to generate reply and send as outbound AI message;
- for SUGGEST_ONLY: generates draft reply as TEMPLATE message visible только админам.

All external AI calls go through SafeAiClient; on any error we fall back to no-op.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.omnichannel_ai_settings_service import (
    EffectiveOmniAISettings,
    OmnichannelAISettingsService,
)
from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.application.services.omnichannel_outbound_dispatcher import (
    OmnichannelOutboundDispatcher,
)
from src.core.config import settings
from src.core.metrics import (
    omni_ai_auto_replies_total,
    omni_ai_escalations_total,
    omni_ai_provider_errors_total,
    omni_ai_suggestions_total,
)
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.infrastructure.external_apis.ai_client import AiClient, AiClientError
from src.infrastructure.external_apis.safe_ai_client import SafeAiClient

logger = logging.getLogger(__name__)


@dataclass
class AIContext:
    business_account_id: UUID
    chat: OmniChat
    contact: OmniContact | None
    last_messages: list[OmniMessage]
    effective_settings: EffectiveOmniAISettings
    clinic_name: str | None = None  # Domain context for prompt (Phase 4)


@dataclass
class LLMReply:
    text: str
    confidence: float
    meta: dict[str, Any]


class LLMClient:
    """Thin wrapper around SafeAiClient for omnichannel orchestrator."""

    def __init__(self, safe_client: SafeAiClient | None = None) -> None:
        base_client = AiClient()
        self._client = safe_client or SafeAiClient(base_client)

    def is_configured(self) -> bool:
        return self._client.is_configured()

    async def generate_reply(self, context: AIContext) -> LLMReply | None:
        """Call LLM provider and return structured reply; on failure returns None."""
        # Build simple prompt using last messages only; domain data can be added later.
        lines: list[str] = []
        for m in context.last_messages[-10:]:
            role = "КЛИЕНТ" if m.direction == "INBOUND" and m.actor_type == "CLIENT" else "ОПЕРАТОР"
            body = (m.content or "").strip()
            if not body:
                continue
            lines.append(f"{role}: {body}")
        transcript = "\n".join(lines)

        system_prompt = (
            "Ты помощник контакт-центра клиники. "
            "Отвечай вежливо, кратко, без медицинских рекомендаций и без обещаний скидок. "
            "Верни строго JSON вида {\"text\": \"...\", \"confidence\": 0.0}."
        )
        if context.clinic_name:
            system_prompt = f"Клиника: {context.clinic_name}.\n{system_prompt}"
        user_content = f"История диалога:\n{transcript}\n\nСформулируй ответ клиенту на последнюю реплику."

        payload = {
            "model": settings.ai_provider_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 256,
        }

        try:
            data = await self._client.complete(payload)
        except AiClientError as exc:
            omni_ai_provider_errors_total.labels(
                source="omni_orchestrator",
                error_type="ai_client_error",
            ).inc()
            logger.warning("LLMClient.generate_reply AiClientError", extra={"error": str(exc)})
            return None
        except Exception:  # noqa: BLE001
            omni_ai_provider_errors_total.labels(
                source="omni_orchestrator",
                error_type="unexpected_error",
            ).inc()
            logger.exception("LLMClient.generate_reply unexpected error")
            return None

        content = _extract_message_content(data) or ""
        try:
            import json

            parsed = json.loads(content)
            text = str(parsed.get("text") or "").strip()
            if not text:
                return None
            confidence = float(parsed.get("confidence") or 0.5)
            return LLMReply(text=text, confidence=confidence, meta=parsed)
        except Exception:
            # If provider did not return structured JSON, treat content as plain text.
            text = content.strip()
            if not text:
                return None
            return LLMReply(text=text, confidence=0.5, meta={})


OPERATOR_REQUEST_PHRASES = [
    "оператор",
    "живой человек",
    "менеджер",
    "позовите",
    "хочу поговорить с человеком",
    "соедините с оператором",
]


def _client_asks_for_operator(text: str) -> bool:
    """Return True if client text indicates request for a live operator."""
    if not (text and isinstance(text, str)):
        return False
    normalized = " ".join((text or "").lower().split())
    return any(phrase in normalized for phrase in OPERATOR_REQUEST_PHRASES)


def _extract_message_content(data: dict) -> str:
    """Extract `choices[0].message.content` from generic chat-completions response."""
    try:
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        return str(content)
    except Exception:  # noqa: BLE001
        return ""


class OmnichannelAIOrchestrator:
    """Core AI orchestrator for omnichannel inbound messages."""

    def __init__(
        self,
        session: AsyncSession,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.session = session
        self.chat_service = OmnichannelChatService(session)
        self.settings_service = OmnichannelAISettingsService(session)
        self.llm_client = llm_client or LLMClient()
        self.dispatcher = OmnichannelOutboundDispatcher(session)

    async def _get_telegram_admin_chat_id(self, chat: OmniChat) -> str | None:
        """Admin chat ID for Telegram notifications: TELEGRAM_BOT credentials or settings (delegates to shared helper)."""
        from src.application.services.omnichannel_integrations_config_service import (
            OmnichannelIntegrationsConfigService,
        )
        config_svc = OmnichannelIntegrationsConfigService(self.session)
        return await config_svc.get_telegram_admin_chat_id_for_clinic(chat.business_account_id)

    async def handle_incoming_for_ai(
        self,
        message: OmniMessage,
        chat: OmniChat,
        contact: OmniContact | None,
    ) -> None:
        """Entry point after createInboundMessage(...)."""
        # Resolve effective settings
        effective = await self.settings_service.get_effective_settings(
            business_account_id=chat.business_account_id,
            channel_id=message.channel_id,
            chat_id=chat.id,
        )

        ai_mode = (effective.ai_mode or "DISABLED").upper()

        if ai_mode == "DISABLED":
            logger.info(
                "OmnichannelAIOrchestrator.skip_disabled",
                extra={
                    "component": "omni_ai_orchestrator",
                    "event": "ai_disabled",
                    "chat_id": str(chat.id),
                    "message_id": str(message.id),
                    "ai_mode": ai_mode,
                    "correlation_chat_id": str(chat.id),
                    "correlation_message_id": str(message.id),
                },
            )
            return

        if not self.llm_client.is_configured():
            logger.info(
                "OmnichannelAIOrchestrator: AI disabled because provider not configured",
                extra={
                    "component": "omni_ai_orchestrator",
                    "event": "provider_not_configured",
                    "chat_id": str(chat.id),
                    "message_id": str(message.id),
                    "correlation_chat_id": str(chat.id),
                    "correlation_message_id": str(message.id),
                },
            )
            return

        # Escalation: client asked for live operator — set status and notify, do not call LLM
        if _client_asks_for_operator(message.content or ""):
            chat.status = "WAITING_FOR_OPERATOR"
            chat.ai_mode = "SUGGEST_ONLY"
            await self.session.flush()
            logger.info(
                "omni_escalation_client_asked_operator",
                extra={
                    "chat_id": str(chat.id),
                    "message_id": str(message.id),
                    "business_account_id": str(chat.business_account_id),
                },
            )
            try:
                from src.application.services.notification_service import send_with_fallback
                from src.core.config import settings

                message_text = f"Клиент запросил живого оператора в чате {chat.id}."
                admin_chat_id = await self._get_telegram_admin_chat_id(chat)
                await send_with_fallback(
                    message=message_text,
                    template="omni_ai_suggestion",
                    chat_id=admin_chat_id,
                    preferred_channel="telegram",
                )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "OmnichannelAIOrchestrator: failed to notify admins about operator request",
                    extra={"chat_id": str(chat.id)},
                    exc_info=True,
                )
            return

        # Collect context messages and optional domain context (clinic name for prompt)
        last_messages = await self.chat_service.list_messages(chat_id=chat.id, limit=20)
        clinic_name: str | None = None
        from sqlalchemy import select
        from src.domain.entities.clinic import Clinic
        result = await self.session.execute(
            select(Clinic.name).where(Clinic.id == chat.business_account_id).limit(1)
        )
        name_val = result.scalar_one_or_none()
        if name_val and isinstance(name_val, str):
            clinic_name = name_val
        ctx = AIContext(
            business_account_id=chat.business_account_id,
            chat=chat,
            contact=contact,
            last_messages=last_messages,
            effective_settings=effective,
            clinic_name=clinic_name,
        )

        llm_reply = await self.llm_client.generate_reply(ctx)
        if llm_reply is None or not llm_reply.text.strip():
            logger.info(
                "OmnichannelAIOrchestrator.no_reply",
                extra={
                    "component": "omni_ai_orchestrator",
                    "event": "no_reply",
                    "chat_id": str(chat.id),
                    "message_id": str(message.id),
                    "ai_mode": ai_mode,
                    "correlation_chat_id": str(chat.id),
                    "correlation_message_id": str(message.id),
                },
            )
            return

        thresholds = effective.confidence_thresholds or {}
        auto_threshold = float(thresholds.get("auto_reply", 0.7))

        if ai_mode == "AUTO_REPLY":
            if llm_reply.confidence >= auto_threshold:
                await self._auto_reply(chat, llm_reply)
            else:
                # Low confidence: mark for operator attention only (no message to client).
                omni_ai_escalations_total.labels(reason="low_confidence").inc()
                logger.info(
                    "OmnichannelAIOrchestrator: AUTO_REPLY below threshold, skipping reply",
                    extra={
                        "component": "omni_ai_orchestrator",
                        "event": "auto_reply_below_threshold",
                        "chat_id": str(chat.id),
                        "message_id": str(message.id),
                        "confidence": llm_reply.confidence,
                        "threshold": auto_threshold,
                        "correlation_chat_id": str(chat.id),
                        "correlation_message_id": str(message.id),
                    },
                )
        elif ai_mode == "SUGGEST_ONLY":
            await self._suggest_only(chat, llm_reply)

    async def _auto_reply(self, chat: OmniChat, reply: LLMReply) -> None:
        """Create outbound AI message and dispatch to channel."""
        msg = await self.chat_service.append_outbound_message(
            chat=chat,
            actor_type="AI",
            content=reply.text,
            channel_id=chat.channel_id,
        )
        omni_ai_auto_replies_total.labels(
            business_account_id=str(chat.business_account_id),
        ).inc()
        await self.dispatcher.dispatch_to_channel(msg)

    async def _suggest_only(self, chat: OmniChat, reply: LLMReply) -> None:
        """Create TEMPLATE message as AI draft suggestion for admins."""
        draft = OmniMessage(
            chat_id=chat.id,
            contact_id=None,
            channel_id=None,
            direction="OUTBOUND",
            actor_type="AI",
            content_type="TEMPLATE",
            content=reply.text,
            source_metadata={
                "kind": "ai_suggestion",
                "confidence": reply.confidence,
            },
        )
        self.session.add(draft)
        await self.session.flush()
        omni_ai_suggestions_total.labels(
            business_account_id=str(chat.business_account_id),
        ).inc()
        logger.info(
            "omni_ai_suggestion_created",
            extra={
                "chat_id": str(chat.id),
                "message_id": str(draft.id),
                "business_account_id": str(chat.business_account_id),
            },
        )
        # Notify admins (log + optional Telegram to admin chat)
        try:
            from src.application.services.notification_service import send_with_fallback
            from src.core.config import settings

            message_text = (
                f"Новый черновик ответа AI в омниканальном чате. Chat ID: {chat.id}. "
                "Откройте раздел «Единый чат» в админке."
            )
            admin_chat_id = await self._get_telegram_admin_chat_id(chat)
            await send_with_fallback(
                message=message_text,
                template="omni_ai_suggestion",
                chat_id=admin_chat_id,
                preferred_channel="telegram",
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "OmnichannelAIOrchestrator: failed to notify admins about suggestion",
                extra={"chat_id": str(chat.id), "message_id": str(draft.id)},
                exc_info=True,
            )

