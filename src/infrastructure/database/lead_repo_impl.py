"""SQLAlchemy implementation of LeadRepository for CRM Kanban."""

import logging
from datetime import datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_note import LeadNote
from src.domain.interfaces.repositories.lead_repository import LeadRepository

logger = logging.getLogger(__name__)


class LeadRepositoryImpl(LeadRepository):
    """SQLAlchemy implementation of LeadRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Pipelines
    async def get_default_pipeline(self, clinic_id: UUID) -> LeadPipeline | None:
        stmt = (
            select(LeadPipeline)
            .where(LeadPipeline.clinic_id == clinic_id, LeadPipeline.is_default.is_(True))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_pipelines(self, clinic_id: UUID) -> list[LeadPipeline]:
        stmt = select(LeadPipeline).where(LeadPipeline.clinic_id == clinic_id).order_by(
            LeadPipeline.created_at.asc()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # Stages
    async def list_stages_for_pipeline(
        self,
        clinic_id: UUID,
        pipeline_id: UUID,
    ) -> list[LeadStage]:
        stmt = (
            select(LeadStage)
            .where(
                LeadStage.clinic_id == clinic_id,
                LeadStage.pipeline_id == pipeline_id,
            )
            .order_by(LeadStage.order.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_stage_by_id(self, clinic_id: UUID, stage_id: UUID) -> LeadStage | None:
        stmt = select(LeadStage).where(
            LeadStage.id == stage_id,
            LeadStage.clinic_id == clinic_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_stage_by_pipeline_and_code(
        self, clinic_id: UUID, pipeline_id: UUID, code: str
    ) -> LeadStage | None:
        stmt = select(LeadStage).where(
            LeadStage.clinic_id == clinic_id,
            LeadStage.pipeline_id == pipeline_id,
            LeadStage.code == code,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # Leads
    async def create_lead(self, lead: LeadCard) -> LeadCard:
        self.session.add(lead)
        await self.session.flush()
        await self.session.refresh(lead)
        logger.info(
            "Lead created",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(lead.clinic_id),
                "pipeline_id": str(lead.pipeline_id),
                "stage_id": str(lead.stage_id),
            },
        )
        return lead

    async def update_lead(self, lead: LeadCard) -> LeadCard:
        await self.session.flush()
        await self.session.refresh(lead)
        logger.info(
            "Lead updated",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(lead.clinic_id),
                "stage_id": str(lead.stage_id),
                "status": lead.status,
            },
        )
        return lead

    async def get_lead_by_id(self, clinic_id: UUID, lead_id: UUID) -> LeadCard | None:
        stmt = select(LeadCard).where(
            LeadCard.id == lead_id,
            LeadCard.clinic_id == clinic_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_open_lead_for_contact_or_patient(
        self,
        clinic_id: UUID,
        omnichannel_contact_id: UUID | None,
        patient_id: UUID | None,
    ) -> LeadCard | None:
        conditions = [
            LeadCard.clinic_id == clinic_id,
            LeadCard.status == "open",
        ]
        contact_filters: list = []
        if omnichannel_contact_id is not None:
            contact_filters.append(LeadCard.omnichannel_contact_id == omnichannel_contact_id)
        if patient_id is not None:
            contact_filters.append(LeadCard.patient_id == patient_id)

        if not contact_filters:
            return None

        stmt = select(LeadCard).where(and_(*conditions, or_(*contact_filters))).order_by(
            LeadCard.created_at.desc()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_lead_by_primary_booking_id(
        self, clinic_id: UUID, booking_id: UUID
    ) -> LeadCard | None:
        stmt = select(LeadCard).where(
            LeadCard.clinic_id == clinic_id,
            LeadCard.primary_booking_id == booking_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_leads(
        self,
        clinic_id: UUID,
        stage_id: UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source: str | None = None,
        search: str | None = None,
        patient_id: UUID | None = None,
        booking_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LeadCard]:
        stmt = select(LeadCard).where(LeadCard.clinic_id == clinic_id)

        if stage_id:
            stmt = stmt.where(LeadCard.stage_id == stage_id)
        if status:
            stmt = stmt.where(LeadCard.status == status)
        if date_from:
            stmt = stmt.where(LeadCard.created_at >= date_from)
        if date_to:
            stmt = stmt.where(LeadCard.created_at <= date_to)
        if source:
            stmt = stmt.where(LeadCard.source == source)
        if search:
            ilike = f"%{search}%"
            stmt = stmt.where(or_(LeadCard.title.ilike(ilike)))
        if patient_id:
            stmt = stmt.where(LeadCard.patient_id == patient_id)
        if booking_id:
            stmt = stmt.where(LeadCard.primary_booking_id == booking_id)

        stmt = (
            stmt.order_by(LeadCard.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # Notes
    async def list_notes_for_lead(
        self,
        clinic_id: UUID,
        lead_id: UUID,
    ) -> list[LeadNote]:
        stmt = (
            select(LeadNote)
            .where(
                LeadNote.clinic_id == clinic_id,
                LeadNote.lead_id == lead_id,
            )
            .order_by(LeadNote.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_note(self, note: LeadNote) -> LeadNote:
        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note)
        logger.info(
            "Lead note created",
            extra={
                "note_id": str(note.id),
                "lead_id": str(note.lead_id),
                "clinic_id": str(note.clinic_id),
                "author_admin_id": str(note.author_admin_id),
            },
        )
        return note

