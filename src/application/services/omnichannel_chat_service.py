"""Basic chat service for omnichannel assistant (Phase 1).

Provides minimal operations to create contacts/chats and append messages
without real channel integrations or AI orchestration.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.metrics import omni_messages_total
from src.core.prometheus_labels import account_bucket_label
from src.domain.entities.omnichannel_chat import Chat
from src.domain.entities.omnichannel_channel import Channel
from src.domain.entities.omnichannel_contact import Contact
from src.domain.entities.omnichannel_message import Message
from src.domain.interfaces.repositories.omnichannel_chat_repository import (
    ChatRepository,
    ContactRepository,
    MessageRepository,
)
from src.infrastructure.database.omnichannel_chat_repo_impl import (
    ChatRepositoryImpl,
    ContactRepositoryImpl,
    MessageRepositoryImpl,
)

logger = logging.getLogger(__name__)


class OmnichannelChatService:
    """Conversation Service for omnichannel assistant (Phase 1–3)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.contacts: ContactRepository = ContactRepositoryImpl(session)
        self.chats: ChatRepository = ChatRepositoryImpl(session)
        self.messages: MessageRepository = MessageRepositoryImpl(session)

    # ---------- Contact & Chat helpers ----------

    async def create_contact(
        self,
        business_account_id: UUID,
        full_name: str | None,
        primary_phone: str | None,
    ) -> Contact:
        contact = Contact(
            business_account_id=business_account_id,
            full_name=full_name,
            primary_phone=primary_phone,
        )
        contact = await self.contacts.create(contact)
        return contact

    async def get_or_create_contact_for_patient(
        self,
        business_account_id: UUID,
        patient_id: UUID,
        full_name: str | None,
        primary_phone: str | None,
    ) -> Contact:
        """Find or create Contact by patient_id (external_ids.patient_id)."""
        contact = await self.contacts.find_by_external_id(
            business_account_id=business_account_id,
            external_key="patient_id",
            external_value=str(patient_id),
        )
        if contact:
            return contact
        contact = Contact(
            business_account_id=business_account_id,
            full_name=full_name,
            primary_phone=primary_phone,
            external_ids={"patient_id": str(patient_id)},
        )
        contact = await self.contacts.create(contact)
        return contact

    async def get_or_create_channel_for_provider(
        self,
        business_account_id: UUID,
        provider: str,
    ) -> UUID | None:
        """Return Channel.id for given provider, creating a stub if needed.

        Provider mapping (MVP):
        - TELEGRAM  -> TELEGRAM_BOT
        - WEBCHAT   -> WEB_WIDGET
        - WEB_APP   -> WEB_APP (PWA bridge)
        - WHATSAPP  -> WHATSAPP_BUSINESS
        - VK        -> VK_BOT
        - INSTAGRAM -> INSTAGRAM_DM
        - EMAIL     -> EMAIL_INBOX
        """
        provider_upper = provider.upper()
        if provider_upper == "TELEGRAM":
            channel_type = "TELEGRAM_BOT"
        elif provider_upper == "WEBCHAT":
            channel_type = "WEB_WIDGET"
        elif provider_upper == "WEB_APP":
            channel_type = "WEB_APP"
        elif provider_upper == "WHATSAPP":
            channel_type = "WHATSAPP_BUSINESS"
        elif provider_upper == "VK":
            channel_type = "VK_BOT"
        elif provider_upper == "INSTAGRAM":
            channel_type = "INSTAGRAM_DM"
        elif provider_upper == "EMAIL":
            channel_type = "EMAIL_INBOX"
        else:
            return None

        async with self.session.begin_nested():
            from sqlalchemy import select

            result = await self.session.execute(
                select(Channel).where(
                    Channel.business_account_id == business_account_id,
                    Channel.type == channel_type,
                ).limit(1)
            )
            channel = result.scalar_one_or_none()
            if channel:
                return channel.id
            channel = Channel(
                business_account_id=business_account_id,
                type=channel_type,
                display_name=channel_type,
                status="PENDING_SETUP",
            )
            self.session.add(channel)
            await self.session.flush()
            return channel.id

    async def get_or_create_chat(
        self,
        business_account_id: UUID,
        contact: Contact,
        channel_id: UUID | None = None,
    ) -> Chat:
        """Find existing open chat for contact or create a new one."""
        existing = await self.chats.find_open_by_contact(
            business_account_id=business_account_id,
            contact_id=contact.id,
        )
        if existing:
            return existing
        chat = Chat(
            business_account_id=business_account_id,
            contact_id=contact.id,
            channel_id=channel_id,
            title=None,
        )
        chat = await self.chats.create(chat)
        return chat

    async def get_chat_for_business(
        self,
        business_account_id: UUID,
        chat_id: UUID,
    ) -> Chat | None:
        chat = await self.chats.get_by_id(chat_id)
        if chat is None or chat.business_account_id != business_account_id:
            return None
        return chat

    async def get_chat_by_webchat_anonymous_id(
        self,
        business_account_id: UUID,
        anonymous_id: str,
    ) -> Chat | None:
        """Find open chat for webchat widget by anonymous_id (contact.external_ids['webchat_user_id'])."""
        contact = await self.contacts.find_by_external_id(
            business_account_id=business_account_id,
            external_key="webchat_user_id",
            external_value=anonymous_id.strip(),
        )
        if not contact:
            return None
        return await self.chats.find_open_by_contact(
            business_account_id=business_account_id,
            contact_id=contact.id,
        )

    async def exists_inbound_by_external_id(
        self,
        chat_id: UUID,
        provider: str,
        external_message_id: str,
    ) -> bool:
        """True if inbound message with this external id already exists in chat."""
        return await self.messages.exists_by_chat_and_external_id(
            chat_id=chat_id,
            provider=provider,
            external_message_id=external_message_id,
        )

    # ---------- Conversation operations ----------

    async def create_inbound_message(
        self,
        chat: Chat,
        contact: Contact | None,
        content: str,
        channel_id: UUID | None = None,
        source_metadata: dict | None = None,
    ) -> Message:
        """Create inbound client message and update chat state."""
        msg = Message(
            chat_id=chat.id,
            contact_id=contact.id if contact else None,
            channel_id=channel_id,
            direction="INBOUND",
            actor_type="CLIENT",
            content_type="TEXT",
            content=content,
            source_metadata=source_metadata or {},
        )
        msg = await self.messages.create(msg)
        # Normalize to offset-naive datetime for TIMESTAMP WITHOUT TIME ZONE columns
        created_at = msg.created_at.replace(tzinfo=None) if getattr(msg, "created_at", None) and msg.created_at.tzinfo else msg.created_at
        chat.last_message_at = created_at
        chat.last_actor_type = msg.actor_type
        await self.session.flush()
        omni_messages_total.labels(
            direction="INBOUND",
            actor_type=msg.actor_type,
            channel_id=str(channel_id) if channel_id else "unknown",
            account_bucket=account_bucket_label(chat.business_account_id),
        ).inc()
        logger.info(
            "Omnichannel inbound message created",
            extra={
                "component": "omni_conversation_service",
                "event": "inbound_message_created",
                "chat_id": str(chat.id),
                "message_id": str(msg.id),
                "business_account_id": str(chat.business_account_id),
                "direction": msg.direction,
                "actor_type": msg.actor_type,
                "correlation_chat_id": str(chat.id),
                "correlation_message_id": str(msg.id),
            },
        )
        return msg

    async def append_outbound_message(
        self,
        chat: Chat,
        actor_type: str,
        content: str,
        channel_id: UUID | None = None,
    ) -> Message:
        """Create outbound message from HUMAN_ADMIN / AI / SYSTEM and update chat."""
        msg = Message(
            chat_id=chat.id,
            contact_id=None,
            channel_id=channel_id,
            direction="OUTBOUND",
            actor_type=actor_type,
            content_type="TEXT",
            content=content,
        )
        msg = await self.messages.create(msg)
        created_at = msg.created_at.replace(tzinfo=None) if getattr(msg, "created_at", None) and msg.created_at.tzinfo else msg.created_at
        chat.last_message_at = created_at
        chat.last_actor_type = msg.actor_type
        if chat.status == "OPEN":
            chat.status = "IN_PROGRESS"
        await self.session.flush()
        omni_messages_total.labels(
            direction="OUTBOUND",
            actor_type=actor_type,
            channel_id=str(channel_id) if channel_id else "unknown",
            account_bucket=account_bucket_label(chat.business_account_id),
        ).inc()
        logger.info(
            "Omnichannel outbound message created",
            extra={
                "component": "omni_conversation_service",
                "event": "outbound_message_created",
                "chat_id": str(chat.id),
                "message_id": str(msg.id),
                "business_account_id": str(chat.business_account_id),
                "direction": msg.direction,
                "actor_type": actor_type,
                "correlation_chat_id": str(chat.id),
                "correlation_message_id": str(msg.id),
            },
        )
        return msg

    async def list_messages(
        self,
        chat_id: UUID,
        limit: int = 50,
        after_id: UUID | None = None,
        before_id: UUID | None = None,
        include_hidden: bool = False,
    ) -> list[Message]:
        """Return messages for chat in chronological order; optional cursor via after_id/before_id."""
        limit = max(1, min(limit, 200))
        if after_id is not None or before_id is not None:
            return await self.messages.list_messages_cursor(
                chat_id=chat_id,
                limit=limit,
                after_id=after_id,
                before_id=before_id,
                include_hidden=include_hidden,
            )
        return await self.messages.list_last_messages(
            chat_id=chat_id, limit=limit, include_hidden=include_hidden
        )

    async def soft_hide_message(
        self,
        business_account_id: UUID,
        message: Message,
        reason: str,
        actor_id: UUID | None,
        actor_type: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Message:
        """Soft-hide a message and write to omni_audit_logs."""
        from src.domain.entities.omnichannel_audit_log import AuditLog as OmniAuditLog

        if not message.ui_hidden:
            message.ui_hidden = True
            message.hidden_reason = reason
            await self.messages.update(message)
        audit = OmniAuditLog(
            business_account_id=business_account_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action_type="MESSAGE_SOFT_HIDE",
            target_type="MESSAGE",
            target_id=message.id,
            meta={"reason": reason},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(audit)
        await self.session.flush()
        logger.info(
            "Omnichannel message soft-hidden",
            extra={
                "message_id": str(message.id),
                "business_account_id": str(business_account_id),
                "actor_type": actor_type,
            },
        )
        return message


