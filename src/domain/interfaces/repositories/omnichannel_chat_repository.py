"""Repositories for omnichannel chat core entities."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.omnichannel_chat import Chat
from src.domain.entities.omnichannel_contact import Contact
from src.domain.entities.omnichannel_message import Message


class ContactRepository(ABC):
    @abstractmethod
    async def create(self, contact: Contact) -> Contact:
        ...

    @abstractmethod
    async def get_by_id(self, contact_id: UUID) -> Contact | None:
        ...

    @abstractmethod
    async def find_by_external_id(
        self,
        business_account_id: UUID,
        external_key: str,
        external_value: str,
    ) -> Contact | None:
        """Find contact by external_ids[external_key] == external_value (e.g. webchat_user_id, telegram_user_id)."""
        ...


class ChatRepository(ABC):
    @abstractmethod
    async def create(self, chat: Chat) -> Chat:
        ...

    @abstractmethod
    async def get_by_id(self, chat_id: UUID) -> Chat | None:
        ...

    @abstractmethod
    async def find_open_by_contact(
        self,
        business_account_id: UUID,
        contact_id: UUID,
    ) -> Chat | None:
        ...

    @abstractmethod
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
        ...


class MessageRepository(ABC):
    @abstractmethod
    async def create(self, message: Message) -> Message:
        ...

    @abstractmethod
    async def get_by_id(self, message_id: UUID) -> Message | None:
        ...

    @abstractmethod
    async def list_last_messages(
        self,
        chat_id: UUID,
        limit: int,
        include_hidden: bool = False,
    ) -> list[Message]:
        ...

    @abstractmethod
    async def list_messages_cursor(
        self,
        chat_id: UUID,
        limit: int,
        after_id: UUID | None = None,
        before_id: UUID | None = None,
        include_hidden: bool = False,
    ) -> list[Message]:
        """Return messages in chronological order, optionally after/before given message id (cursor pagination)."""
        ...

    @abstractmethod
    async def exists_by_chat_and_external_id(
        self,
        chat_id: UUID,
        provider: str,
        external_message_id: str,
    ) -> bool:
        """Return True if an INBOUND message already exists with this chat_id and source_metadata (provider, external_message_id)."""
        ...

    @abstractmethod
    async def update(self, message: Message) -> Message:
        ...

