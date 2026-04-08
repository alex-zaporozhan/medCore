"""Admin CRM API: sales pipelines, stages, and leads Kanban."""

import logging
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import (
    AdminContext,
    get_request_context,
    get_session,
    require_permissions,
)
from src.api.v1.entitlement_dependencies import require_entitlement
from src.application.ai.tools_base import ToolContext, ToolError
from src.application.ai.tools_crm import (
    CreateTaskForLeadTool,
    SuggestNextStageForLeadTool,
    SummarizeLeadContextTool,
    UpdateLeadStageTool,
)
from src.application.dto.crm_dto import (
    ChangeLeadStageRequest,
    CreateLeadNoteRequest,
    LeadCardDto,
    LeadDetailsResponse,
    LeadKanbanCardDto,
    LeadKanbanListResponse,
    LeadListResponse,
    LeadNoteDto,
    LeadPipelineDto,
    LeadStageDto,
    UpdateLeadEstimatedValueRequest,
)
from src.application.dto.crm_ai_dto import (
    CreateLeadTaskInput,
    CreateLeadTaskOutput,
    IgnoreLeadRecommendationInput,
    IgnoreLeadRecommendationOutput,
    SuggestNextStageOutput,
    SummarizeLeadContextOutput,
    UpdateLeadStageInput,
    UpdateLeadStageOutput,
)
from src.application.dto.crm_semantics_dto import (
    LeadStageResolvedSemanticDto,
    LeadStageSemanticMappingDto,
    LeadStageSemanticMappingsResponse,
    UpsertLeadStageSemanticMappingRequest,
)
from src.application.services.booking_service import BookingService
from src.application.services.lead_service import LeadService, SemanticTransitionBlockedError
from src.application.services.lead_stage_semantics_service import LeadStageSemanticsService
from src.application.services.patient_service import PatientService
from src.application.services.schedule_service import ScheduleService
from src.core.metrics import crm_ai_recommendations_total, crm_leads_list_requests_total
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.entities.lead_stage_semantic_map import LeadStageSemanticMap
from src.domain.entities.lead_card import LeadCard

logger = logging.getLogger(__name__)

def _raise_for_tool_error(err: ToolError) -> None:
    """
    Normalize ToolError -> HTTPException mapping.

    - not_found -> 404
    - clinic_mismatch -> 400
    - forbidden/permission -> 403 (handled upstream by require_permissions but keep for completeness)
    - default -> 400
    """
    code = (err.code or "").lower()
    if code in {"lead_not_found", "not_found"} or code.endswith("_not_found"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err.message)
    if code == "clinic_mismatch":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err.message)
    if code in {"forbidden", "permission_denied"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err.message)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err.message)

router = APIRouter(
    prefix="/admin/crm",
    tags=["admin-crm"],
    dependencies=[
        Depends(require_permissions("view_crm")),
        Depends(require_entitlement("crm.pipeline")),
    ],
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
    """Return stages for given pipeline in current clinic with aggregates (leads_count, sum_estimated_value)."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = LeadService(session)
    stages = await service.list_stages_for_pipeline(
        clinic_id=context.clinic_id,
        pipeline_id=pipeline_id,
    )
    if not stages:
        return []
    stage_ids = [s.id for s in stages]
    # Single query: aggregates per stage for Kanban header (B4.1)
    agg_result = await session.execute(
        select(
            LeadCard.stage_id,
            func.count(LeadCard.id).label("leads_count"),
            func.coalesce(func.sum(LeadCard.estimated_value), 0).label("sum_estimated_value"),
        )
        .where(
            LeadCard.clinic_id == context.clinic_id,
            LeadCard.stage_id.in_(stage_ids),
        )
        .group_by(LeadCard.stage_id)
    )
    agg_map = {row.stage_id: (int(row.leads_count), row.sum_estimated_value) for row in agg_result.all()}
    out: list[LeadStageDto] = []
    for s in stages:
        cnt, sval = agg_map.get(s.id, (0, 0))
        d = LeadStageDto.model_validate(s).model_dump()
        d["leads_count"] = cnt
        d["sum_estimated_value"] = sval
        out.append(LeadStageDto(**d))
    return out


@router.get(
    "/pipelines/{pipeline_id}/stage-semantics",
    response_model=LeadStageSemanticMappingsResponse,
)
async def get_pipeline_stage_semantics(
    pipeline_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> LeadStageSemanticMappingsResponse:
    """Return configured (or empty) semantic mappings for a pipeline."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")

    # Ensure pipeline exists in clinic boundary.
    leads = LeadService(session)
    pipeline = await leads.repository.get_pipeline_by_id(context.clinic_id, pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")

    res = await session.execute(
        select(LeadStageSemanticMap).where(
            LeadStageSemanticMap.clinic_id == context.clinic_id,
            LeadStageSemanticMap.pipeline_id == pipeline_id,
        )
    )
    rows = list(res.scalars().all())
    rows.sort(key=lambda r: (r.semantic or ""))

    supported = [
        LeadStageSemanticsService.SEM_START,
        LeadStageSemanticsService.SEM_SCHEDULED,
        LeadStageSemanticsService.SEM_STALE,
        LeadStageSemanticsService.SEM_WON,
        LeadStageSemanticsService.SEM_LOST,
    ]
    stages_list = await leads.list_stages_for_pipeline(context.clinic_id, pipeline_id)
    semantics_svc = LeadStageSemanticsService(session)
    resolved: list[LeadStageResolvedSemanticDto] = []
    for st in stages_list:
        rsem = await semantics_svc.get_semantic_for_stage(
            clinic_id=context.clinic_id,
            pipeline_id=pipeline_id,
            stage=st,
        )
        resolved.append(LeadStageResolvedSemanticDto(stage_id=st.id, semantic=rsem))

    return LeadStageSemanticMappingsResponse(
        pipeline_id=pipeline_id,
        supported_semantics=supported,
        mappings=[
            LeadStageSemanticMappingDto(semantic=r.semantic, stage_id=r.stage_id)
            for r in rows
        ],
        resolved_stage_semantics=resolved,
    )


@router.put(
    "/pipelines/{pipeline_id}/stage-semantics",
    response_model=LeadStageSemanticMappingsResponse,
    dependencies=[Depends(require_permissions("manage_crm"))],
)
async def upsert_pipeline_stage_semantics(
    pipeline_id: UUID,
    body: UpsertLeadStageSemanticMappingRequest,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> LeadStageSemanticMappingsResponse:
    """Upsert a single semantic→stage_id mapping for a pipeline."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")

    leads = LeadService(session)
    pipeline = await leads.repository.get_pipeline_by_id(context.clinic_id, pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")

    # Validate stage belongs to pipeline (clinic boundary + pipeline match).
    stage = await leads.repository.get_stage_by_id(context.clinic_id, body.stage_id)
    if stage is None or stage.pipeline_id != pipeline_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="stage_id is not in pipeline")

    semantics = LeadStageSemanticsService(session)
    await semantics.set_semantic_mapping(
        clinic_id=context.clinic_id,
        pipeline_id=pipeline_id,
        semantic=body.semantic,
        stage_id=body.stage_id,
    )

    # Return updated list.
    return await get_pipeline_stage_semantics(
        pipeline_id=pipeline_id,
        session=session,
        context=context,
    )


@router.get(
    "/leads",
    response_model=LeadListResponse | LeadKanbanListResponse,
)
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
    pagination: Literal["page", "cursor"] = Query(
        "page",
        description="`cursor` + `projection=kanban`: stable keyset pagination (created_at DESC, id DESC).",
    ),
    cursor: str | None = Query(
        None,
        description="Opaque cursor from previous `next_cursor` (Kanban column load-more).",
    ),
    projection: Literal["full", "kanban"] = Query(
        "full",
        description="Use `kanban` for a lighter payload and ORM load_only (Kanban board).",
    ),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> LeadListResponse | LeadKanbanListResponse:
    """List leads for Kanban board with filters and pagination."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    clinic_id = context.clinic_id
    service = LeadService(session)
    kanban_projection = projection == "kanban"

    crm_leads_list_requests_total.labels(projection=projection).inc()

    if pagination == "cursor":
        if projection != "kanban":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="pagination=cursor requires projection=kanban",
            )
        try:
            leads, next_cursor, total = await service.list_leads_cursor(
                clinic_id=clinic_id,
                stage_id=stage_id,
                status=status_filter,
                date_from=date_from,
                date_to=date_to,
                source=source,
                search=search,
                patient_id=patient_id,
                booking_id=booking_id,
                cursor_token=cursor,
                limit=page_size,
                kanban_projection=True,
            )
        except ValueError as exc:
            if str(exc) == "invalid_cursor":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor",
                ) from exc
            raise
        return LeadKanbanListResponse(
            items=[LeadKanbanCardDto.model_validate(lead) for lead in leads],
            total=total,
            next_cursor=next_cursor,
        )

    skip = (page - 1) * page_size
    leads, total = await service.list_leads(
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
        kanban_projection=kanban_projection,
    )

    if kanban_projection:
        return LeadKanbanListResponse(
            items=[LeadKanbanCardDto.model_validate(lead) for lead in leads],
            total=total,
        )
    return LeadListResponse(items=[LeadCardDto.model_validate(lead) for lead in leads], total=total)


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
            request_context=context,
            enforce_semantic=body.enforce_semantic_transition,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SemanticTransitionBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "semantic_transition_invalid",
                "from_semantic": exc.from_semantic,
                "to_semantic": exc.to_semantic,
            },
        ) from exc
    return LeadCardDto.model_validate(lead)


@router.patch("/leads/{lead_id}/estimated-value", response_model=LeadCardDto)
async def update_lead_estimated_value(
    lead_id: UUID,
    body: UpdateLeadEstimatedValueRequest,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
    _: AdminContext = Depends(require_permissions("manage_crm")),
) -> LeadCardDto:
    """Set CRM forecast ``estimated_value`` (not ``actual_value`` — that comes from ERP only)."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    clinic_id = context.clinic_id
    service = LeadService(session)
    lead_before = await service.repository.get_lead_by_id(clinic_id, lead_id)
    try:
        lead = await service.recalculate_estimated_value(
            clinic_id=clinic_id,
            lead_id=lead_id,
            explicit=body.estimated_value,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if lead_before is not None and context.user_id is not None:
        await service.append_estimated_value_compliance_audit(
            clinic_id=clinic_id,
            lead_id=lead_id,
            old_value=lead_before.estimated_value,
            new_value=lead.estimated_value,
            admin_user_id=context.user_id,
            trace_id=context.trace_id,
        )
    logger.info(
        "crm_lead_estimated_value_api_update",
        extra={
            "trace_id": context.trace_id,
            "clinic_id": str(clinic_id),
            "lead_id": str(lead_id),
            "actor_id": str(context.user_id) if context.user_id else None,
            "estimated_value": str(body.estimated_value),
        },
    )
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


@router.get("/leads/{lead_id}/ai/summary", response_model=SummarizeLeadContextOutput)
async def ai_summarize_lead(
    lead_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> SummarizeLeadContextOutput:
    """Return AI-generated (or fallback) summary for lead context."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")

    tool = SummarizeLeadContextTool()
    tool_ctx = ToolContext(
        db=session,
        clinic_id=context.clinic_id,
        request_context=context,
        source="admin_crm",
        booking_service=BookingService(session),
        schedule_service=ScheduleService(session),
        patient_service=PatientService(session),
    )
    args = tool.args_schema.model_validate(
        {
            "clinic_id": context.clinic_id,
            "lead_id": lead_id,
            "lead_token": None,
            "trace_id": context.trace_id,
        }
    )
    result = await tool(tool_ctx, args)
    if isinstance(result, ToolError):
        _raise_for_tool_error(result)
    return result


@router.get("/leads/{lead_id}/ai/suggest-next-stage", response_model=SuggestNextStageOutput)
async def ai_suggest_next_stage(
    lead_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> SuggestNextStageOutput:
    """Return AI suggestion for the next lead stage (read-only)."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")

    tool = SuggestNextStageForLeadTool()
    tool_ctx = ToolContext(
        db=session,
        clinic_id=context.clinic_id,
        request_context=context,
        source="admin_crm",
        booking_service=BookingService(session),
        schedule_service=ScheduleService(session),
        patient_service=PatientService(session),
    )
    args = tool.args_schema.model_validate(
        {
            "clinic_id": context.clinic_id,
            "lead_id": lead_id,
            "lead_token": None,
            "trace_id": context.trace_id,
        }
    )
    result = await tool(tool_ctx, args)
    if isinstance(result, ToolError):
        _raise_for_tool_error(result)
    return result


@router.patch(
    "/leads/{lead_id}/ai/stage",
    response_model=UpdateLeadStageOutput,
    dependencies=[Depends(require_permissions("manage_crm"))],
)
async def ai_update_lead_stage(
    lead_id: UUID,
    body: UpdateLeadStageInput,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> UpdateLeadStageOutput:
    """Apply lead stage update using AI-safe handler (audited)."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    if body.clinic_id != context.clinic_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="clinic_id mismatch")

    tool = UpdateLeadStageTool()
    tool_ctx = ToolContext(
        db=session,
        clinic_id=context.clinic_id,
        request_context=context,
        source="admin_crm",
        booking_service=BookingService(session),
        schedule_service=ScheduleService(session),
        patient_service=PatientService(session),
    )
    args = tool.args_schema.model_validate(
        {**body.model_dump(), "lead_id": lead_id, "lead_token": None, "trace_id": context.trace_id}
    )
    result = await tool(tool_ctx, args)
    if isinstance(result, ToolError):
        _raise_for_tool_error(result)
    return result


@router.post(
    "/leads/{lead_id}/ai/tasks",
    response_model=CreateLeadTaskOutput,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_tasks"))],
)
async def ai_create_task_for_lead(
    lead_id: UUID,
    body: CreateLeadTaskInput,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> CreateLeadTaskOutput:
    """Create a task linked to a lead (created_by=ai_suggested)."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    if body.clinic_id != context.clinic_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="clinic_id mismatch")

    tool = CreateTaskForLeadTool()
    tool_ctx = ToolContext(
        db=session,
        clinic_id=context.clinic_id,
        request_context=context,
        source="admin_crm",
        booking_service=BookingService(session),
        schedule_service=ScheduleService(session),
        patient_service=PatientService(session),
    )
    args = tool.args_schema.model_validate(
        {**body.model_dump(), "lead_id": lead_id, "lead_token": None, "trace_id": context.trace_id}
    )
    result = await tool(tool_ctx, args)
    if isinstance(result, ToolError):
        _raise_for_tool_error(result)
    return result


@router.post(
    "/leads/{lead_id}/ai/recommendations/ignore",
    response_model=IgnoreLeadRecommendationOutput,
    status_code=status.HTTP_201_CREATED,
)
async def ai_ignore_recommendation(
    lead_id: UUID,
    body: IgnoreLeadRecommendationInput,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> IgnoreLeadRecommendationOutput:
    """Record that an AI recommendation was ignored by operator (for metrics/audit)."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    if body.clinic_id != context.clinic_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="clinic_id mismatch")

    # Ensure lead exists in clinic boundary (avoid leaking foreign ids into metrics).
    service = LeadService(session)
    lead = await service.repository.get_lead_by_id(context.clinic_id, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    kind = (body.kind or "unknown").lower()
    crm_ai_recommendations_total.labels(
        clinic_bucket=clinic_bucket_label(context.clinic_id),
        kind=kind,
        outcome="ignored",
    ).inc()
    logger.info(
        "crm_ai_recommendation_ignored",
        extra={
            "trace_id": body.trace_id or context.trace_id,
            "clinic_id": str(context.clinic_id),
            "lead_id": str(lead_id),
            "kind": kind,
            "reason": (body.reason or "")[:500] if body.reason else None,
            "actor_id": str(context.user_id) if context.user_id else None,
        },
    )
    return IgnoreLeadRecommendationOutput(success=True, trace_id=body.trace_id or context.trace_id)

