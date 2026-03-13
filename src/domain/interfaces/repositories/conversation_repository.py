"""Conversation repository interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.conversation import Conversation


class ConversationRepository(ABC):
    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        ...

    @abstractmethod
    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        ...

    @abstractmethod
    async def get_by_clinic_patient(self, clinic_id: UUID, patient_id: UUID) -> Conversation | None:
        ...

    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation:
        ...

    @abstractmethod
    async def list_for_clinic(
        self,
        clinic_id: UUID,
        filter_kind: str,
        assigned_admin_id: UUID | None,
        search: str | None,
        skip: int,
        limit: int,
    ) -> tuple[list[Conversation], int]:
        ...
