"""Admin recall API: segments, templates, campaigns, automations."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.v1.entitlement_dependencies import require_entitlement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.application.dto.recall_dto import (
    RecallAutomationCreate,
    RecallAutomationRead,
    RecallAutomationUpdate,
    RecallCampaignCreate,
    RecallCampaignRead,
    RecallCampaignUpdate,
    RecallLogRead,
    RecallSegmentCreate,
    RecallSegmentRead,
    RecallSegmentUpdate,
    RecallSegmentWithCount,
    RecallTemplateCreate,
    RecallTemplateRead,
    RecallTemplateUpdate,
)
from src.application.services.recall_service import (
    create_automation,
    create_campaign,
    create_segment,
    create_template,
    get_segment_patient_count,
    run_campaign,
)
from src.domain.entities.recall_automation import RecallAutomation
from src.domain.entities.recall_campaign import RecallCampaign
from src.domain.entities.recall_log import RecallLog
from src.domain.entities.recall_segment import RecallSegment
from src.domain.entities.recall_template import RecallTemplate

router = APIRouter(
    prefix="/admin/clinics",
    tags=["admin-recall"],
    dependencies=[Depends(require_entitlement("marketing.attribution"))],
)


# --- Segments ---
@router.get(
    "/{clinic_id}/recall/segments",
    response_model=list[RecallSegmentWithCount],
)
async def list_recall_segments(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallSegment).where(RecallSegment.clinic_id == clinic_id)
    )
    segments = result.scalars().all()
    out = []
    for seg in segments:
        count = await get_segment_patient_count(session, clinic_id, seg.id)
        out.append(
            RecallSegmentWithCount(
                **RecallSegmentRead.model_validate(seg).model_dump(),
                patient_count=count,
            )
        )
    return out


@router.post(
    "/{clinic_id}/recall/segments",
    response_model=RecallSegmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_recall_segment(
    clinic_id: UUID,
    body: RecallSegmentCreate,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return await create_segment(session, clinic_id, body)


@router.get(
    "/{clinic_id}/recall/segments/{segment_id}",
    response_model=RecallSegmentWithCount,
)
async def get_recall_segment(
    clinic_id: UUID,
    segment_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallSegment).where(
            RecallSegment.id == segment_id,
            RecallSegment.clinic_id == clinic_id,
        )
    )
    seg = result.scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    count = await get_segment_patient_count(session, clinic_id, seg.id)
    return RecallSegmentWithCount(
        **RecallSegmentRead.model_validate(seg).model_dump(),
        patient_count=count,
    )


@router.put(
    "/{clinic_id}/recall/segments/{segment_id}",
    response_model=RecallSegmentRead,
)
async def update_recall_segment(
    clinic_id: UUID,
    segment_id: UUID,
    body: RecallSegmentUpdate,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallSegment).where(
            RecallSegment.id == segment_id,
            RecallSegment.clinic_id == clinic_id,
        )
    )
    seg = result.scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(seg, k, v)
    await session.flush()
    await session.refresh(seg)
    return RecallSegmentRead.model_validate(seg)


@router.delete(
    "/{clinic_id}/recall/segments/{segment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_recall_segment(
    clinic_id: UUID,
    segment_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallSegment).where(
            RecallSegment.id == segment_id,
            RecallSegment.clinic_id == clinic_id,
        )
    )
    seg = result.scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(seg)
    await session.flush()


# --- Templates ---
@router.get(
    "/{clinic_id}/recall/templates",
    response_model=list[RecallTemplateRead],
)
async def list_recall_templates(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallTemplate).where(RecallTemplate.clinic_id == clinic_id)
    )
    return [RecallTemplateRead.model_validate(r) for r in result.scalars().all()]


@router.post(
    "/{clinic_id}/recall/templates",
    response_model=RecallTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_recall_template(
    clinic_id: UUID,
    body: RecallTemplateCreate,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return await create_template(session, clinic_id, body)


@router.get(
    "/{clinic_id}/recall/templates/{template_id}",
    response_model=RecallTemplateRead,
)
async def get_recall_template(
    clinic_id: UUID,
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallTemplate).where(
            RecallTemplate.id == template_id,
            RecallTemplate.clinic_id == clinic_id,
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return RecallTemplateRead.model_validate(t)


@router.put(
    "/{clinic_id}/recall/templates/{template_id}",
    response_model=RecallTemplateRead,
)
async def update_recall_template(
    clinic_id: UUID,
    template_id: UUID,
    body: RecallTemplateUpdate,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallTemplate).where(
            RecallTemplate.id == template_id,
            RecallTemplate.clinic_id == clinic_id,
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(t, k, v)
    await session.flush()
    await session.refresh(t)
    return RecallTemplateRead.model_validate(t)


@router.delete(
    "/{clinic_id}/recall/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_recall_template(
    clinic_id: UUID,
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallTemplate).where(
            RecallTemplate.id == template_id,
            RecallTemplate.clinic_id == clinic_id,
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(t)
    await session.flush()


# --- Campaigns ---
@router.get(
    "/{clinic_id}/recall/campaigns",
    response_model=list[RecallCampaignRead],
)
async def list_recall_campaigns(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallCampaign).where(RecallCampaign.clinic_id == clinic_id)
    )
    return [RecallCampaignRead.model_validate(r) for r in result.scalars().all()]


@router.post(
    "/{clinic_id}/recall/campaigns",
    response_model=RecallCampaignRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_recall_campaign(
    clinic_id: UUID,
    body: RecallCampaignCreate,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return await create_campaign(session, clinic_id, body)


@router.get(
    "/{clinic_id}/recall/campaigns/{campaign_id}",
    response_model=RecallCampaignRead,
)
async def get_recall_campaign(
    clinic_id: UUID,
    campaign_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallCampaign).where(
            RecallCampaign.id == campaign_id,
            RecallCampaign.clinic_id == clinic_id,
        )
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return RecallCampaignRead.model_validate(c)


@router.put(
    "/{clinic_id}/recall/campaigns/{campaign_id}",
    response_model=RecallCampaignRead,
)
async def update_recall_campaign(
    clinic_id: UUID,
    campaign_id: UUID,
    body: RecallCampaignUpdate,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallCampaign).where(
            RecallCampaign.id == campaign_id,
            RecallCampaign.clinic_id == clinic_id,
        )
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(c, k, v)
    await session.flush()
    await session.refresh(c)
    return RecallCampaignRead.model_validate(c)


@router.delete(
    "/{clinic_id}/recall/campaigns/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_recall_campaign(
    clinic_id: UUID,
    campaign_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallCampaign).where(
            RecallCampaign.id == campaign_id,
            RecallCampaign.clinic_id == clinic_id,
        )
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(c)
    await session.flush()


@router.post(
    "/{clinic_id}/recall/campaigns/{campaign_id}/run",
    response_model=dict,
)
async def run_recall_campaign(
    clinic_id: UUID,
    campaign_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    sent, failed = await run_campaign(session, clinic_id, campaign_id)
    return {"sent": sent, "failed": failed}


# --- Automations ---
@router.get(
    "/{clinic_id}/recall/automations",
    response_model=list[RecallAutomationRead],
)
async def list_recall_automations(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallAutomation).where(RecallAutomation.clinic_id == clinic_id)
    )
    return [RecallAutomationRead.model_validate(r) for r in result.scalars().all()]


@router.post(
    "/{clinic_id}/recall/automations",
    response_model=RecallAutomationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_recall_automation(
    clinic_id: UUID,
    body: RecallAutomationCreate,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return await create_automation(session, clinic_id, body)


@router.get(
    "/{clinic_id}/recall/automations/{automation_id}",
    response_model=RecallAutomationRead,
)
async def get_recall_automation(
    clinic_id: UUID,
    automation_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallAutomation).where(
            RecallAutomation.id == automation_id,
            RecallAutomation.clinic_id == clinic_id,
        )
    )
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return RecallAutomationRead.model_validate(a)


@router.put(
    "/{clinic_id}/recall/automations/{automation_id}",
    response_model=RecallAutomationRead,
)
async def update_recall_automation(
    clinic_id: UUID,
    automation_id: UUID,
    body: RecallAutomationUpdate,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallAutomation).where(
            RecallAutomation.id == automation_id,
            RecallAutomation.clinic_id == clinic_id,
        )
    )
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(a, k, v)
    await session.flush()
    await session.refresh(a)
    return RecallAutomationRead.model_validate(a)


@router.delete(
    "/{clinic_id}/recall/automations/{automation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_recall_automation(
    clinic_id: UUID,
    automation_id: UUID,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(RecallAutomation).where(
            RecallAutomation.id == automation_id,
            RecallAutomation.clinic_id == clinic_id,
        )
    )
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(a)
    await session.flush()


# --- Recall logs (for campaigns) ---
@router.get(
    "/{clinic_id}/recall/logs",
    response_model=list[RecallLogRead],
)
async def list_recall_logs(
    clinic_id: UUID,
    campaign_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
):
    if clinic_id != _perm_ctx.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    stmt = select(RecallLog).where(RecallLog.clinic_id == clinic_id)
    if campaign_id is not None:
        stmt = stmt.where(RecallLog.campaign_id == campaign_id)
    result = await session.execute(stmt)
    return [RecallLogRead.model_validate(r) for r in result.scalars().all()]
