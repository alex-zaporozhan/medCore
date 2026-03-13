"""ChatMessage repository implementation."""

import logging
from uuid import UUID

from src.core.datetime_utils import utc_now

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.chat_message import ChatMessage
from src.domain.interfaces.repositories.chat_message_repository import ChatMessageRepository

logger = logging.getLogger(__name__)


class ChatMessageRepositoryImpl(ChatMessageRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, message: ChatMessage) -> ChatMessage:
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        logger.info("ChatMessage created", extra={"message_id": str(message.id), "conversation_id": str(message.conversation_id)})
        return message

    async def get_by_id(self, message_id: UUID) -> ChatMessage | None:
        result = await self.session.execute(
            select(ChatMessage).where(
                ChatMessage.id == message_id,
                ChatMessage.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_include_deleted(self, message_id: UUID) -> ChatMessage | None:
        result = await self.session.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        return result.scalar_one_or_none()

    async def list_by_conversation(
        self,
        conversation_id: UUID,
        cursor: UUID | None,
        limit: int,
        ascending: bool,
    ) -> list[ChatMessage]:
        query = (
            select(ChatMessage)
            .where(
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.deleted_at.is_(None),
            )
        )
        if cursor:
            cursor_msg = await self.get_by_id(cursor)
            if cursor_msg and cursor_msg.conversation_id == conversation_id:
                if ascending:
                    query = query.where(ChatMessage.created_at > cursor_msg.created_at)
                else:
                    query = query.where(ChatMessage.created_at < cursor_msg.created_at)
        order = ChatMessage.created_at.asc() if ascending else ChatMessage.created_at.desc()
        query = query.order_by(order).limit(limit + 1)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, message: ChatMessage) -> ChatMessage:
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def mark_read_by_patient_up_to(
        self, conversation_id: UUID, up_to_message_id: UUID | None
    ) -> int:
        now = utc_now()
        q = (
            update(ChatMessage)
            .where(
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.sender_type.in_(["admin", "system"]),
                ChatMessage.read_by_patient_at.is_(None),
                ChatMessage.deleted_at.is_(None),
            )
        )
        if up_to_message_id:
            msg = await self.get_by_id(up_to_message_id)
            if msg and msg.conversation_id == conversation_id:
                q = q.where(ChatMessage.created_at <= msg.created_at)
        q = q.values(read_by_patient_at=now)
        r = await self.session.execute(q)
        return r.rowcount or 0

    async def mark_read_by_admin_up_to(
        self, conversation_id: UUID, up_to_message_id: UUID | None
    ) -> int:
        now = utc_now()
        q = (
            update(ChatMessage)
            .where(
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.sender_type == "patient",
                ChatMessage.read_by_admin_at.is_(None),
                ChatMessage.deleted_at.is_(None),
            )
        )
        if up_to_message_id:
            msg = await self.get_by_id(up_to_message_id)
            if msg and msg.conversation_id == conversation_id:
                q = q.where(ChatMessage.created_at <= msg.created_at)
        q = q.values(read_by_admin_at=now)
        r = await self.session.execute(q)
        return r.rowcount or 0
