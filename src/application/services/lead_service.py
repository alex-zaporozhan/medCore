"""LeadService for CRM Kanban (pipelines, stages, leads, notes)."""

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_note import LeadNote
from src.domain.interfaces.repositories.lead_repository import LeadRepository
from src.infrastructure.database.lead_repo_impl import LeadRepositoryImpl

logger = logging.getLogger(__name__)


class LeadService:
    """Application service for CRM leads and pipelines."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository: LeadRepository = LeadRepositoryImpl(session)

    # Pipelines & stages (Phase 1 – только чтение)
    async def get_default_pipeline_id(self, clinic_id: UUID) -> UUID | None:
        pipeline = await self.repository.get_default_pipeline(clinic_id)
        return pipeline.id if pipeline else None

    async def list_pipelines(self, clinic_id: UUID):
        return await self.repository.list_pipelines(clinic_id)

    async def list_stages_for_pipeline(self, clinic_id: UUID, pipeline_id: UUID):
        return await self.repository.list_stages_for_pipeline(clinic_id, pipeline_id)

    # Leads
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
        return await self.repository.list_leads(
            clinic_id=clinic_id,
            stage_id=stage_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            source=source,
            search=search,
            patient_id=patient_id,
            booking_id=booking_id,
            skip=skip,
            limit=limit,
        )

    async def get_lead_details(self, clinic_id: UUID, lead_id: UUID) -> tuple[LeadCard, list[LeadNote]] | None:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            return None
        notes = await self.repository.list_notes_for_lead(clinic_id, lead_id)
        return lead, notes

    async def create_lead_from_contact(
        self,
        clinic_id: UUID,
        omnichannel_contact_id: UUID | None,
        patient_id: UUID | None,
        title: str,
        source: str,
        estimated_value: Decimal | None = None,
    ) -> LeadCard:
        default_pipeline = await self.repository.get_default_pipeline(clinic_id)
        if not default_pipeline:
            raise RuntimeError("Default lead pipeline is not configured for clinic")

        stages = await self.repository.list_stages_for_pipeline(
            clinic_id=clinic_id,
            pipeline_id=default_pipeline.id,
        )
        if not stages:
            raise RuntimeError("Lead stages are not configured for default pipeline")

        first_stage = sorted(stages, key=lambda s: s.order)[0]
        lead = LeadCard(
            clinic_id=clinic_id,
            pipeline_id=default_pipeline.id,
            stage_id=first_stage.id,
            omnichannel_contact_id=omnichannel_contact_id,
            patient_id=patient_id,
            primary_booking_id=None,
            title=title,
            source=source,
            estimated_value=estimated_value or Decimal("0.00"),
            actual_value=Decimal("0.00"),
            status="open",
        )
        lead = await self.repository.create_lead(lead)
        logger.info(
            "[CRM] Lead created from contact",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(clinic_id),
                "contact_id": str(omnichannel_contact_id) if omnichannel_contact_id else None,
                "patient_id": str(patient_id) if patient_id else None,
            },
        )
        return lead

    async def change_lead_stage(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        new_stage_id: UUID,
    ) -> LeadCard:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        stage = await self.repository.get_stage_by_id(clinic_id, new_stage_id)
        if not stage:
            raise LookupError("LeadStage not found for clinic")

        lead.stage_id = new_stage_id
        lead = await self.repository.update_lead(lead)
        logger.info(
            "[CRM] Lead stage changed",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(clinic_id),
                "new_stage_id": str(new_stage_id),
            },
        )
        return lead

    async def attach_booking(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        booking_id: UUID,
        new_stage_id: UUID | None = None,
        new_estimated_value: Decimal | None = None,
    ) -> LeadCard:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        if lead.primary_booking_id is None:
            lead.primary_booking_id = booking_id

        if new_stage_id is not None:
            stage = await self.repository.get_stage_by_id(clinic_id, new_stage_id)
            if not stage:
                raise LookupError("LeadStage not found for clinic")
            lead.stage_id = new_stage_id

        if new_estimated_value is not None:
            lead.estimated_value = new_estimated_value

        lead = await self.repository.update_lead(lead)
        logger.info(
            "[CRM] Lead booking attached",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(clinic_id),
                "booking_id": str(booking_id),
                "primary_booking_id": str(lead.primary_booking_id),
            },
        )
        return lead

    async def apply_payment_to_lead(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        amount: Decimal,
        new_stage_id: UUID | None = None,
    ) -> LeadCard:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        lead.actual_value = (lead.actual_value or Decimal("0.00")) + amount

        if new_stage_id is not None:
            stage = await self.repository.get_stage_by_id(clinic_id, new_stage_id)
            if not stage:
                raise LookupError("LeadStage not found for clinic")
            lead.stage_id = new_stage_id

        lead = await self.repository.update_lead(lead)
        logger.info(
            "[CRM] Lead payment applied",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(clinic_id),
                "amount": str(amount),
                "actual_value": str(lead.actual_value),
            },
        )
        return lead

    async def close_lead_as_success(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        success_stage_id: UUID,
        actual_value: Decimal | None = None,
    ) -> LeadCard:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        stage = await self.repository.get_stage_by_id(clinic_id, success_stage_id)
        if not stage:
            raise LookupError("LeadStage not found for clinic")

        lead.stage_id = success_stage_id
        lead.status = "success"
        lead.closed_at = datetime.utcnow()
        if actual_value is not None:
            lead.actual_value = actual_value

        lead = await self.repository.update_lead(lead)
        logger.info(
            "[CRM] Lead closed as success",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(clinic_id),
                "actual_value": str(lead.actual_value),
            },
        )
        return lead

    async def add_lead_note(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        author_admin_id: UUID,
        text: str,
    ) -> LeadNote:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        note = LeadNote(
            clinic_id=clinic_id,
            lead_id=lead_id,
            author_admin_id=author_admin_id,
            text=text,
        )
        note = await self.repository.create_note(note)
        logger.info(
            "[CRM] Lead note created",
            extra={
                "lead_id": str(lead_id),
                "clinic_id": str(clinic_id),
                "author_admin_id": str(author_admin_id),
            },
        )
        return note

