"""Conversation repository implementation."""

import logging
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.conversation import Conversation
from src.domain.interfaces.repositories.conversation_repository import ConversationRepository

logger = logging.getLogger(__name__)


class ConversationRepositoryImpl(ConversationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, conversation: Conversation) -> Conversation:
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)
        logger.info("Conversation created", extra={"conversation_id": str(conversation.id), "clinic_id": str(conversation.clinic_id)})
        return conversation

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_clinic_patient(self, clinic_id: UUID, patient_id: UUID) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.clinic_id == clinic_id,
                Conversation.patient_id == patient_id,
                Conversation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def update(self, conversation: Conversation) -> Conversation:
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def list_for_clinic(
        self,
        clinic_id: UUID,
        filter_kind: str,
        assigned_admin_id: UUID | None,
        search: str | None,
        skip: int,
        limit: int,
    ) -> tuple[list[Conversation], int]:
        from src.domain.entities.patient import Patient

        query = select(Conversation).where(
            Conversation.clinic_id == clinic_id,
            Conversation.deleted_at.is_(None),
        )
        if filter_kind == "mine" and assigned_admin_id:
            query = query.where(Conversation.assigned_admin_id == assigned_admin_id)
        elif filter_kind == "unassigned":
            query = query.where(Conversation.assigned_admin_id.is_(None))
        subq = None
        if search and search.strip():
            subq = select(Patient.id).where(
                Patient.clinic_id == clinic_id,
                Patient.deleted_at.is_(None),
                (Patient.full_name.ilike(f"%{search.strip()}%") | Patient.phone.ilike(f"%{search.strip()}%")),
            )
            query = query.where(Conversation.patient_id.in_(subq))

        count_stmt = select(func.count()).select_from(Conversation).where(
            Conversation.clinic_id == clinic_id,
            Conversation.deleted_at.is_(None),
        )
        if filter_kind == "mine" and assigned_admin_id:
            count_stmt = count_stmt.where(Conversation.assigned_admin_id == assigned_admin_id)
        elif filter_kind == "unassigned":
            count_stmt = count_stmt.where(Conversation.assigned_admin_id.is_(None))
        if subq is not None:
            count_stmt = count_stmt.where(Conversation.patient_id.in_(subq))
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        query = query.order_by(Conversation.last_message_at.desc().nulls_last()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total
