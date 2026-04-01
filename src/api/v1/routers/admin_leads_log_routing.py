"""Admin API: lead-log routing rules (per clinic)."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.application.dto.lead_log_routing_dto import (
    LeadLogRoutingRuleDto,
    ReplaceLeadLogRoutingRulesRequest,
    SimulateLeadLogRoutingRequest,
    SimulateLeadLogRoutingResponse,
)
from src.domain.entities.lead_log_routing_rule import LeadLogRoutingRule
from src.domain.entities.task_stream import TaskStream


router = APIRouter(prefix="/admin/leads-log", tags=["admin-leads-log-routing"])


def err_payload(detail: str, code: str, field: str | None = None) -> dict:
    return {"detail": detail, "code": code, "field": field}


async def _ensure_stream_in_clinic(session: AsyncSession, clinic_id: UUID, stream_id: UUID) -> None:
    res = await session.execute(
        select(TaskStream.id).where(
            TaskStream.id == stream_id,
            TaskStream.clinic_id == clinic_id,
            TaskStream.is_archived.is_(False),
        )
    )
    if res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err_payload("Поток не найден или архивирован", "STREAM_INVALID", field="target_stream_id"),
        )


@router.get(
    "/routing-rules",
    response_model=list[LeadLogRoutingRuleDto],
    dependencies=[Depends(require_permissions("leads.log.view"))],
)
async def list_routing_rules(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[LeadLogRoutingRuleDto]:
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    stmt = (
        select(LeadLogRoutingRule)
        .where(LeadLogRoutingRule.clinic_id == clinic_id)
        .order_by(LeadLogRoutingRule.sort_order.asc(), LeadLogRoutingRule.id.asc())
    )
    res = await session.execute(stmt)
    return [LeadLogRoutingRuleDto.model_validate(r) for r in res.scalars().all()]


@router.put(
    "/routing-rules",
    response_model=list[LeadLogRoutingRuleDto],
    dependencies=[Depends(require_permissions("leads.log.manage"))],
)
async def replace_routing_rules(
    body: ReplaceLeadLogRoutingRulesRequest,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[LeadLogRoutingRuleDto]:
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")

    # Validate streams exist in this clinic before mutating.
    uniq_stream_ids = list({r.target_stream_id for r in body.rules})
    for sid in uniq_stream_ids:
        await _ensure_stream_in_clinic(session, clinic_id, sid)

    await session.execute(delete(LeadLogRoutingRule).where(LeadLogRoutingRule.clinic_id == clinic_id))
    rows: list[LeadLogRoutingRule] = []
    for r in body.rules:
        rows.append(
            LeadLogRoutingRule(
                id=uuid4(),
                clinic_id=clinic_id,
                channel_type=(r.channel_type.strip().upper() if r.channel_type and r.channel_type.strip() else None),
                source_key=(r.source_key.strip() if r.source_key and r.source_key.strip() else None),
                target_stream_id=r.target_stream_id,
                is_active=bool(r.is_active),
                sort_order=int(r.sort_order or 0),
            )
        )
    if rows:
        session.add_all(rows)
    await session.flush()
    return [LeadLogRoutingRuleDto.model_validate(r) for r in sorted(rows, key=lambda x: (x.sort_order, str(x.id)))]


@router.post(
    "/routing-rules/simulate",
    response_model=SimulateLeadLogRoutingResponse,
    dependencies=[Depends(require_permissions("leads.log.manage"))],
)
async def simulate_routing(
    body: SimulateLeadLogRoutingRequest,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> SimulateLeadLogRoutingResponse:
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    ch = body.channel_type.strip().upper() if body.channel_type and body.channel_type.strip() else None
    sk = body.source_key.strip() if body.source_key and body.source_key.strip() else None

    stmt = (
        select(LeadLogRoutingRule)
        .where(LeadLogRoutingRule.clinic_id == clinic_id, LeadLogRoutingRule.is_active.is_(True))
        .order_by(LeadLogRoutingRule.sort_order.asc(), LeadLogRoutingRule.id.asc())
    )
    res = await session.execute(stmt)
    rules = list(res.scalars().all())
    for r in rules:
        if r.channel_type and ch and r.channel_type != ch:
            continue
        if r.channel_type and ch is None:
            continue
        if r.source_key and sk and r.source_key != sk:
            continue
        if r.source_key and sk is None:
            continue
        return SimulateLeadLogRoutingResponse(matched_rule_id=r.id, target_stream_id=r.target_stream_id)
    return SimulateLeadLogRoutingResponse(matched_rule_id=None, target_stream_id=None)

