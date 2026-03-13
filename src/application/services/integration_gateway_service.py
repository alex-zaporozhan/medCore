"""Integration Gateway service for omnichannel assistant (Phase 2).

Responsible for:
- validating and normalizing incoming webhooks/messages from providers
  into NormalizedMessageDTO;
- minimal identity & routing into omnichannel Contact/Chat and inbound Message.
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.omnichannel_dto import NormalizedMessageDTO
from src.application.services.omnichannel_ai_orchestrator import (
    OmnichannelAIOrchestrator,
)
from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.core.metrics import omni_messages_total
from src.domain.entities.omnichannel_contact import Contact

logger = logging.getLogger(__name__)


class IntegrationGatewayService:
    """High-level entrypoint for provider webhooks → omnichannel Chat/Message."""

    def __init__(self, session: AsyncSession, business_account_id: UUID):
        self.session = session
        self.business_account_id = business_account_id
        self.chat_service = OmnichannelChatService(session)
        self.ai_orchestrator = OmnichannelAIOrchestrator(session)

    # ---------- Normalization ----------

    @staticmethod
    def normalize_telegram_update(payload: dict) -> NormalizedMessageDTO | None:
        """Normalize raw Telegram update to NormalizedMessageDTO.

        Expects standard Bot API update with "message" field.
        """
        message = payload.get("message") or {}
        if not message:
            return None
        text = (message.get("text") or "").strip()
        if not text:
            return None
        message_id = str(message.get("message_id"))
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id"))
        from_user = message.get("from") or {}
        from_id = str(from_user.get("id") or chat_id)
        date_ts = message.get("date")
        ts = datetime.utcfromtimestamp(date_ts) if isinstance(date_ts, int) else datetime.utcnow()
        return NormalizedMessageDTO(
            provider="TELEGRAM",
            external_message_id=message_id,
            from_id=from_id,
            chat_external_id=chat_id,
            text=text,
            timestamp=ts,
        )

    @staticmethod
    def normalize_webchat_message(payload: dict) -> NormalizedMessageDTO | None:
        """Normalize web-chat payload to NormalizedMessageDTO.

        Simple MVP format:
        - anonymous_id: str
        - text: str
        - message_id?: str
        - timestamp?: ISO string
        """
        text = (payload.get("text") or "").strip()
        if not text:
            return None
        anonymous_id = str(payload.get("anonymous_id") or "").strip()
        if not anonymous_id:
            return None
        external_message_id = str(payload.get("message_id") or anonymous_id)
        ts_raw = payload.get("timestamp")
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw)
            except ValueError:
                ts = datetime.utcnow()
        else:
            ts = datetime.utcnow()
        return NormalizedMessageDTO(
            provider="WEBCHAT",
            external_message_id=external_message_id,
            from_id=anonymous_id,
            chat_external_id=anonymous_id,
            text=text,
            timestamp=ts,
        )

    @staticmethod
    def normalize_whatsapp_message(payload: dict) -> NormalizedMessageDTO | None:
        """Normalize WhatsApp Business webhook payload to NormalizedMessageDTO (MVP).

        Expected simplified structure (already pre-filtered by upstream gateway, if any):
        {
            "from": "<phone_or_whatsapp_id>",
            "chat_id": "<conversation_id_or_phone>",
            "text": "<message text>",
            "message_id": "<provider_message_id>",
            "timestamp": "<ISO 8601>",
        }
        """
        text = (payload.get("text") or "").strip()
        if not text:
            return None
        from_id = str(payload.get("from") or "").strip()
        chat_external_id = str(payload.get("chat_id") or from_id).strip()
        if not from_id or not chat_external_id:
            return None
        external_message_id = str(payload.get("message_id") or chat_external_id)
        ts_raw = payload.get("timestamp")
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw)
            except ValueError:
                ts = datetime.utcnow()
        else:
            ts = datetime.utcnow()
        return NormalizedMessageDTO(
            provider="WHATSAPP",
            external_message_id=external_message_id,
            from_id=from_id,
            chat_external_id=chat_external_id,
            text=text,
            timestamp=ts,
        )

    @staticmethod
    def normalize_vk_message(payload: dict) -> NormalizedMessageDTO | None:
        """Normalize VK Messages webhook payload to NormalizedMessageDTO (MVP).

        Expected simplified structure:
        {
            "user_id": "<vk_user_id>",
            "peer_id": "<peer_or_chat_id>",
            "text": "<message text>",
            "message_id": "<provider_message_id>",
            "date": <unix_timestamp>,
        }
        """
        text = (payload.get("text") or "").strip()
        if not text:
            return None
        from_id = str(payload.get("user_id") or "").strip()
        chat_external_id = str(payload.get("peer_id") or from_id).strip()
        if not from_id or not chat_external_id:
            return None
        external_message_id = str(payload.get("message_id") or chat_external_id)
        date_ts = payload.get("date")
        ts = datetime.utcfromtimestamp(date_ts) if isinstance(date_ts, int) else datetime.utcnow()
        return NormalizedMessageDTO(
            provider="VK",
            external_message_id=external_message_id,
            from_id=from_id,
            chat_external_id=chat_external_id,
            text=text,
            timestamp=ts,
        )

    @staticmethod
    def normalize_instagram_message(payload: dict) -> NormalizedMessageDTO | None:
        """Normalize Instagram Direct webhook payload to NormalizedMessageDTO (MVP).

        Expected simplified structure:
        {
            "sender_id": "<instagram_user_id>",
            "thread_id": "<thread_or_conversation_id>",
            "text": "<message text>",
            "message_id": "<provider_message_id>",
            "timestamp": "<ISO 8601>",
        }
        """
        text = (payload.get("text") or "").strip()
        if not text:
            return None
        from_id = str(payload.get("sender_id") or "").strip()
        chat_external_id = str(payload.get("thread_id") or from_id).strip()
        if not from_id or not chat_external_id:
            return None
        external_message_id = str(payload.get("message_id") or chat_external_id)
        ts_raw = payload.get("timestamp")
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw)
            except ValueError:
                ts = datetime.utcnow()
        else:
            ts = datetime.utcnow()
        return NormalizedMessageDTO(
            provider="INSTAGRAM",
            external_message_id=external_message_id,
            from_id=from_id,
            chat_external_id=chat_external_id,
            text=text,
            timestamp=ts,
        )

    @staticmethod
    def normalize_email_message(payload: dict) -> NormalizedMessageDTO | None:
        """Normalize Email payload (inbound) to NormalizedMessageDTO (MVP).

        Expected simplified structure:
        {
            "from_email": "<sender email>",
            "thread_id": "<thread_or_message_id>",
            "subject": "<subject>",
            "text": "<plain text body>",
            "message_id": "<provider_message_id>",
            "timestamp": "<ISO 8601>",
        }
        Only `text` is required; subject is prepended to text if present.
        """
        body = (payload.get("text") or "").strip()
        subject = (payload.get("subject") or "").strip()
        if not body and not subject:
            return None
        text_parts = []
        if subject:
            text_parts.append(subject)
        if body:
            text_parts.append(body)
        text = "\n\n".join(text_parts).strip()
        from_id = (payload.get("from_email") or "").strip()
        chat_external_id = (payload.get("thread_id") or from_id or "").strip()
        if not from_id or not chat_external_id:
            return None
        external_message_id = str(payload.get("message_id") or chat_external_id)
        ts_raw = payload.get("timestamp")
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw)
            except ValueError:
                ts = datetime.utcnow()
        else:
            ts = datetime.utcnow()
        return NormalizedMessageDTO(
            provider="EMAIL",
            external_message_id=external_message_id,
            from_id=from_id,
            chat_external_id=chat_external_id,
            text=text,
            timestamp=ts,
        )

    # ---------- Identity & Routing (minimal) ----------

    async def _find_or_create_contact_for_normalized(
        self,
        dto: NormalizedMessageDTO,
    ) -> Contact:
        """Minimal identity: create contact keyed by provider-specific external id.

        For now we simply create a Contact per (business_account_id, provider, from_id)
        with external_ids carrying provider-specific identifiers.
        """
        from src.domain.entities.omnichannel_contact import Contact as OmniContact
        from sqlalchemy import select

        provider_key = dto.provider.lower() + "_user_id"
        async with self.session.begin_nested():
            result = await self.session.execute(
                select(OmniContact).where(
                    OmniContact.business_account_id == self.business_account_id,
                    OmniContact.external_ids[provider_key].as_string() == dto.from_id,
                )
            )
            contact = result.scalar_one_or_none()
            if contact:
                return contact
            external_ids = {provider_key: dto.from_id}
            contact = OmniContact(
                business_account_id=self.business_account_id,
                full_name=None,
                primary_phone=None,
                external_ids=external_ids,
            )
            self.session.add(contact)
            await self.session.flush()
            await self.session.refresh(contact)
            logger.info(
                "Omnichannel contact created from normalized message",
                extra={
                    "contact_id": str(contact.id),
                    "business_account_id": str(self.business_account_id),
                    "provider": dto.provider,
                },
            )
            return contact

    async def handle_inbound_normalized_message(
        self,
        dto: NormalizedMessageDTO,
    ) -> None:
        """Main pipeline: NormalizedMessageDTO → Contact/Chat → inbound Message (+ AI)."""
        omni_messages_total.labels(
            direction="INBOUND",
            actor_type="CLIENT",
            channel_id="normalized",
            business_account_id=str(self.business_account_id),
        ).inc()
        logger.info(
            "IntegrationGatewayService.handle_inbound_normalized_message",
            extra={
                "component": "integration_gateway",
                "event": "inbound_normalized",
                "business_account_id": str(self.business_account_id),
                "provider": dto.provider,
                "external_message_id": dto.external_message_id,
                "from_id": dto.from_id,
                "chat_external_id": dto.chat_external_id,
            },
        )
        contact = await self._find_or_create_contact_for_normalized(dto)
        # Bind chat to specific Channel if configured for this provider
        channel_id: UUID | None = await self.chat_service.get_or_create_channel_for_provider(
            business_account_id=self.business_account_id,
            provider=dto.provider,
        )
        chat = await self.chat_service.get_or_create_chat(
            business_account_id=self.business_account_id,
            contact=contact,
            channel_id=channel_id,
        )
        exists = await self.chat_service.exists_inbound_by_external_id(
            chat.id, dto.provider, dto.external_message_id
        )
        if exists:
            logger.info(
                "duplicate inbound message, skipping",
                extra={
                    "chat_id": str(chat.id),
                    "provider": dto.provider,
                    "external_message_id": dto.external_message_id,
                },
            )
            return
        message = await self.chat_service.create_inbound_message(
            chat=chat,
            contact=contact,
            content=dto.text,
            channel_id=channel_id,
            source_metadata={
                "provider": dto.provider,
                "external_message_id": dto.external_message_id,
                "from_id": dto.from_id,
                "chat_external_id": dto.chat_external_id,
                "timestamp": dto.timestamp.isoformat(),
            },
        )
        logger.info(
            "IntegrationGatewayService.inbound_message_persisted",
            extra={
                "component": "integration_gateway",
                "event": "inbound_persisted",
                "business_account_id": str(self.business_account_id),
                "chat_id": str(chat.id),
                "message_id": str(message.id),
                "provider": dto.provider,
                "correlation_chat_id": str(chat.id),
                "correlation_message_id": str(message.id),
            },
        )
        # Trigger AI orchestration (Phase 4)
        await self.ai_orchestrator.handle_incoming_for_ai(
            message=message,
            chat=chat,
            contact=contact,
        )

