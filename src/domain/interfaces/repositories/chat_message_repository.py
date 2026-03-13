"""ChatMessage repository interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.chat_message import ChatMessage


class ChatMessageRepository(ABC):
    @abstractmethod
    async def create(self, message: ChatMessage) -> ChatMessage:
        ...

    @abstractmethod
    async def get_by_id(self, message_id: UUID) -> ChatMessage | None:
        ...

    @abstractmethod
    async def get_by_id_include_deleted(self, message_id: UUID) -> ChatMessage | None:
        """Get message by id even if deleted (for soft-delete flow)."""
        ...

    @abstractmethod
    async def list_by_conversation(
        self,
        conversation_id: UUID,
        cursor: UUID | None,
        limit: int,
        ascending: bool,
    ) -> list[ChatMessage]:
        ...

    @abstractmethod
    async def update(self, message: ChatMessage) -> ChatMessage:
        ...

    @abstractmethod
    async def mark_read_by_patient_up_to(
        self, conversation_id: UUID, up_to_message_id: UUID | None
    ) -> int:
        ...

    @abstractmethod
    async def mark_read_by_admin_up_to(
        self, conversation_id: UUID, up_to_message_id: UUID | None
    ) -> int:
        ...
