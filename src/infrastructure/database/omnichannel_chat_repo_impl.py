"""SQLAlchemy implementations of omnichannel chat repositories."""

import logging
from uuid import UUID

from sqlalchemy import Select, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.omnichannel_chat import Chat
from src.domain.entities.omnichannel_channel import Channel
from src.domain.entities.omnichannel_contact import Contact
from src.domain.entities.omnichannel_message import Message
from src.domain.interfaces.repositories.omnichannel_chat_repository import (
    ChatRepository,
    ContactRepository,
    MessageRepository,
)

logger = logging.getLogger(__name__)


class ContactRepositoryImpl(ContactRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, contact: Contact) -> Contact:
        self.session.add(contact)
        await self.session.flush()
        await self.session.refresh(contact)
        logger.info(
            "Omnichannel Contact created",
            extra={
                "contact_id": str(contact.id),
                "business_account_id": str(contact.business_account_id),
            },
        )
        return contact

    async def get_by_id(self, contact_id: UUID) -> Contact | None:
        result = await self.session.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        return result.scalar_one_or_none()

    async def find_by_external_id(
        self,
        business_account_id: UUID,
        external_key: str,
        external_value: str,
    ) -> Contact | None:
        # PostgreSQL JSON: external_ids->>'key' = value (SQLAlchemy 2.x: use as_string())
        stmt = (
            select(Contact)
            .where(
                Contact.business_account_id == business_account_id,
                Contact.external_ids[external_key].as_string() == external_value,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class ChatRepositoryImpl(ChatRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, chat: Chat) -> Chat:
        self.session.add(chat)
        await self.session.flush()
        await self.session.refresh(chat)
        logger.info(
            "Omnichannel Chat created",
            extra={
                "chat_id": str(chat.id),
                "business_account_id": str(chat.business_account_id),
                "contact_id": str(chat.contact_id),
            },
        )
        return chat

    async def get_by_id(self, chat_id: UUID) -> Chat | None:
        result = await self.session.execute(select(Chat).where(Chat.id == chat_id))
        return result.scalar_one_or_none()

    async def find_open_by_contact(
        self,
        business_account_id: UUID,
        contact_id: UUID,
    ) -> Chat | None:
        stmt: Select[tuple[Chat]] = (
            select(Chat)
            .where(
                Chat.business_account_id == business_account_id,
                Chat.contact_id == contact_id,
                Chat.status.in_(["OPEN", "WAITING_FOR_OPERATOR", "IN_PROGRESS"]),
            )
            .order_by(Chat.last_message_at.desc().nullslast())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_chats(
        self,
        business_account_id: UUID,
        status: str | None,
        search: str | None,
        channel_types: list[str] | None,
        skip: int,
        limit: int,
        assignee_admin_id: UUID | None = None,
        unassigned_only: bool = False,
    ) -> list[Chat]:
        stmt: Select[tuple[Chat]] = select(Chat).where(
            Chat.business_account_id == business_account_id
        )
        if channel_types:
            msg_has_any_type = (
                select(1)
                .select_from(Message)
                .join(Channel, Message.channel_id == Channel.id)
                .where(
                    Message.chat_id == Chat.id,
                    Channel.type.in_(channel_types),
                    Channel.business_account_id == business_account_id,
                )
                .limit(1)
            )
            stmt = stmt.where(exists(msg_has_any_type))
        if assignee_admin_id is not None:
            stmt = stmt.where(Chat.assignee_admin_id == assignee_admin_id)
        if unassigned_only:
            stmt = stmt.where(Chat.assignee_admin_id.is_(None))
        if status:
            stmt = stmt.where(Chat.status == status)
        if search:
            ilike_pattern = f"%{search}%"
            stmt = stmt.join(Contact, Chat.contact_id == Contact.id)
            stmt = stmt.where(
                or_(
                    Chat.title.ilike(ilike_pattern),
                    Contact.full_name.ilike(ilike_pattern),
                    Contact.primary_phone.ilike(ilike_pattern),
                )
            )
        stmt = (
            stmt.order_by(Chat.last_message_at.desc().nullslast())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class MessageRepositoryImpl(MessageRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        logger.info(
            "Omnichannel Message created",
            extra={
                "message_id": str(message.id),
                "chat_id": str(message.chat_id),
                "direction": message.direction,
                "actor_type": message.actor_type,
            },
        )
        return message

    async def get_by_id(self, message_id: UUID) -> Message | None:
        result = await self.session.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def exists_by_chat_and_external_id(
        self,
        chat_id: UUID,
        provider: str,
        external_message_id: str,
    ) -> bool:
        """Return True if an INBOUND message exists with this chat_id and source_metadata (provider, external_message_id)."""
        stmt = (
            select(1)
            .where(
                Message.chat_id == chat_id,
                Message.direction == "INBOUND",
                Message.source_metadata.isnot(None),
                Message.source_metadata["provider"].as_string() == provider,
                Message.source_metadata["external_message_id"].as_string() == external_message_id,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_last_messages(
        self,
        chat_id: UUID,
        limit: int,
        include_hidden: bool = False,
    ) -> list[Message]:
        base = select(Message).where(Message.chat_id == chat_id)
        if not include_hidden:
            base = base.where(Message.ui_hidden.is_(False))
        stmt: Select[tuple[Message]] = (
            base.order_by(Message.created_at.desc()).limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        # Return in chronological order
        return list(reversed(rows))

    async def list_messages_cursor(
        self,
        chat_id: UUID,
        limit: int,
        after_id: UUID | None = None,
        before_id: UUID | None = None,
        include_hidden: bool = False,
    ) -> list[Message]:
        """Messages in chronological order; after_id = messages after that id, before_id = messages before that id."""
        limit = max(1, min(limit, 200))
        base = select(Message).where(Message.chat_id == chat_id)
        if not include_hidden:
            base = base.where(Message.ui_hidden.is_(False))

        if after_id is not None:
            sub = (
                select(Message.created_at)
                .where(Message.id == after_id, Message.chat_id == chat_id)
                .limit(1)
                .scalar_subquery()
            )
            stmt = (
                base.where(Message.created_at > sub)
                .order_by(Message.created_at.asc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        if before_id is not None:
            sub = (
                select(Message.created_at)
                .where(Message.id == before_id, Message.chat_id == chat_id)
                .limit(1)
                .scalar_subquery()
            )
            stmt = (
                base.where(Message.created_at < sub)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            rows = list(result.scalars().all())
            return list(reversed(rows))
        stmt = base.order_by(Message.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        return list(reversed(rows))

    async def update(self, message: Message) -> Message:
        await self.session.flush()
        await self.session.refresh(message)
        return message

