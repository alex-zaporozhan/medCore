"""Lead repository interfaces for CRM Kanban."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable
from uuid import UUID

from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_note import LeadNote


class LeadRepository(ABC):
    """Repository contract for CRM pipelines, stages, leads and notes."""

    # Pipelines
    @abstractmethod
    async def get_default_pipeline(self, clinic_id: UUID) -> LeadPipeline | None:
        ...

    @abstractmethod
    async def list_pipelines(self, clinic_id: UUID) -> list[LeadPipeline]:
        ...

    # Stages
    @abstractmethod
    async def list_stages_for_pipeline(
        self,
        clinic_id: UUID,
        pipeline_id: UUID,
    ) -> list[LeadStage]:
        ...

    @abstractmethod
    async def get_stage_by_id(self, clinic_id: UUID, stage_id: UUID) -> LeadStage | None:
        ...

    @abstractmethod
    async def get_stage_by_pipeline_and_code(
        self, clinic_id: UUID, pipeline_id: UUID, code: str
    ) -> LeadStage | None:
        ...

    # Leads
    @abstractmethod
    async def create_lead(self, lead: LeadCard) -> LeadCard:
        ...

    @abstractmethod
    async def update_lead(self, lead: LeadCard) -> LeadCard:
        ...

    @abstractmethod
    async def get_lead_by_id(self, clinic_id: UUID, lead_id: UUID) -> LeadCard | None:
        ...

    @abstractmethod
    async def find_open_lead_for_contact_or_patient(
        self,
        clinic_id: UUID,
        omnichannel_contact_id: UUID | None,
        patient_id: UUID | None,
    ) -> LeadCard | None:
        ...

    @abstractmethod
    async def get_lead_by_primary_booking_id(
        self, clinic_id: UUID, booking_id: UUID
    ) -> LeadCard | None:
        ...

    @abstractmethod
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
        ...

    # Notes
    @abstractmethod
    async def list_notes_for_lead(
        self,
        clinic_id: UUID,
        lead_id: UUID,
    ) -> list[LeadNote]:
        ...

    @abstractmethod
    async def create_note(self, note: LeadNote) -> LeadNote:
        ...

