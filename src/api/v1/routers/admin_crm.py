"""Admin CRM API: sales pipelines, stages, and leads Kanban."""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.application.dto.crm_dto import (
    ChangeLeadStageRequest,
    CreateLeadNoteRequest,
    LeadCardDto,
    LeadDetailsResponse,
    LeadListResponse,
    LeadNoteDto,
    LeadPipelineDto,
    LeadStageDto,
)
from src.application.services.lead_service import LeadService
from src.domain.entities.lead_card import LeadCard

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/crm",
    tags=["admin-crm"],
    dependencies=[Depends(require_permissions("view_crm"))],
)


@router.get("/pipelines", response_model=list[LeadPipelineDto])
async def list_pipelines(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[LeadPipelineDto]:
    """Return CRM pipelines for current clinic."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = LeadService(session)
    pipelines = await service.list_pipelines(context.clinic_id)
    return [LeadPipelineDto.model_validate(p) for p in pipelines]


@router.get("/stages", response_model=list[LeadStageDto])
async def list_stages(
    pipeline_id: UUID = Query(...),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[LeadStageDto]:
    """Return stages for given pipeline in current clinic."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = LeadService(session)
    stages = await service.list_stages_for_pipeline(
        clinic_id=context.clinic_id,
        pipeline_id=pipeline_id,
    )
    return [LeadStageDto.model_validate(s) for s in stages]


@router.get("/leads", response_model=LeadListResponse)
async def list_leads(
    stage_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    source: str | None = Query(None),
    search: str | None = Query(None),
    patient_id: UUID | None = Query(None),
    booking_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> LeadListResponse:
    """List leads for Kanban board with filters and pagination."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    clinic_id = context.clinic_id
    skip = (page - 1) * page_size
    service = LeadService(session)

    leads = await service.list_leads(
        clinic_id=clinic_id,
        stage_id=stage_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        source=source,
        search=search,
        patient_id=patient_id,
        booking_id=booking_id,
        skip=skip,
        limit=page_size,
    )

    # Simpler total calculation for now (can be optimized later)
    count_stmt = select(func.count(LeadCard.id)).where(LeadCard.clinic_id == clinic_id)
    if stage_id:
        count_stmt = count_stmt.where(LeadCard.stage_id == stage_id)
    if status_filter:
        count_stmt = count_stmt.where(LeadCard.status == status_filter)
    if date_from:
        count_stmt = count_stmt.where(LeadCard.created_at >= date_from)
    if date_to:
        count_stmt = count_stmt.where(LeadCard.created_at <= date_to)
    if source:
        count_stmt = count_stmt.where(LeadCard.source == source)
    if search:
        ilike = f"%{search}%"
        count_stmt = count_stmt.where(LeadCard.title.ilike(ilike))
    if patient_id:
        count_stmt = count_stmt.where(LeadCard.patient_id == patient_id)
    if booking_id:
        count_stmt = count_stmt.where(LeadCard.primary_booking_id == booking_id)

    total_result = await session.execute(count_stmt)
    total = int(total_result.scalar_one() or 0)

    items = [LeadCardDto.model_validate(l) for l in leads]
    return LeadListResponse(items=items, total=total)


@router.get("/leads/{lead_id}", response_model=LeadDetailsResponse)
async def get_lead_details(
    lead_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> LeadDetailsResponse:
    """Return single lead details including notes."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    clinic_id = context.clinic_id
    service = LeadService(session)
    result = await service.get_lead_details(clinic_id=clinic_id, lead_id=lead_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )
    lead, notes = result
    return LeadDetailsResponse(
        lead=LeadCardDto.model_validate(lead),
        notes=[LeadNoteDto.model_validate(n) for n in notes],
    )


@router.patch("/leads/{lead_id}/stage", response_model=LeadCardDto)
async def change_lead_stage(
    lead_id: UUID,
    body: ChangeLeadStageRequest,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
    _: AdminContext = Depends(require_permissions("manage_crm")),
) -> LeadCardDto:
    """Change lead stage (Kanban drag&drop)."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    clinic_id = context.clinic_id
    service = LeadService(session)
    try:
        lead = await service.change_lead_stage(
            clinic_id=clinic_id,
            lead_id=lead_id,
            new_stage_id=body.new_stage_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return LeadCardDto.model_validate(lead)


@router.post(
    "/leads/{lead_id}/notes",
    response_model=LeadNoteDto,
    status_code=status.HTTP_201_CREATED,
)
async def add_lead_note(
    lead_id: UUID,
    body: CreateLeadNoteRequest,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
    _: AdminContext = Depends(require_permissions("manage_crm")),
) -> LeadNoteDto:
    """Add note to lead."""
    if context.clinic_id is None or context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic and user context are required")
    clinic_id = context.clinic_id
    service = LeadService(session)
    try:
        note = await service.add_lead_note(
            clinic_id=clinic_id,
            lead_id=lead_id,
            author_admin_id=context.user_id,
            text=body.text,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return LeadNoteDto.model_validate(note)

