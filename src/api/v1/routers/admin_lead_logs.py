"""Admin API: immutable lead logs from omni-chat resolves."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.application.dto.omni_lead_log_dto import OmniLeadLogDetailDto, OmniLeadLogListItemDto
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omni_lead_log import OmniLeadLog


# Лог лидов omni — операционный контур; гейт только RBAC (не SKU `crm.pipeline`, иначе блок без CRM).
router = APIRouter(prefix="/admin/lead-logs", tags=["admin-lead-logs"])

class LeadLogsOutcomeStatDto(BaseModel):
    outcome: str
    count: int


class LeadLogsAdminStatDto(BaseModel):
    admin_id: UUID | None = None
    admin_name: str | None = None
    count: int


class LeadLogsStatsResponse(BaseModel):
    date_from: str = Field(..., description="YYYY-MM-DD (inclusive, UTC)")
    date_to: str = Field(..., description="YYYY-MM-DD (exclusive, UTC)")
    total: int
    by_outcome: list[LeadLogsOutcomeStatDto]
    by_admin: list[LeadLogsAdminStatDto]
    avg_time_to_close_seconds: float | None = None


async def _admin_display_names(session: AsyncSession, admin_ids: set[UUID]) -> dict[UUID, str]:
    if not admin_ids:
        return {}
    res = await session.execute(
        select(AdminUser.id, AdminUser.full_name, AdminUser.email).where(AdminUser.id.in_(admin_ids))
    )
    out: dict[UUID, str] = {}
    for aid, full_name, email in res.all():
        out[aid] = full_name or email or str(aid)
    return out


def _day_bounds_utc(d: date) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day)
    end = start + timedelta(days=1)
    return start, end


@router.get(
    "/stats",
    response_model=LeadLogsStatsResponse,
    dependencies=[Depends(require_permissions("leads.log.view"))],
)
async def lead_logs_stats(
    date_from: str = Query(..., description="YYYY-MM-DD (inclusive, UTC)"),
    date_to: str = Query(..., description="YYYY-MM-DD (exclusive, UTC)"),
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("leads.log.view")),
) -> LeadLogsStatsResponse:
    clinic_id = admin_ctx.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    try:
        df = date.fromisoformat(date_from)
        dt = date.fromisoformat(date_to)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from/date_to must be YYYY-MM-DD",
        )
    if not (df < dt):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must be < date_to",
        )
    start_dt = datetime(df.year, df.month, df.day)
    end_dt = datetime(dt.year, dt.month, dt.day)

    total_res = await session.execute(
        select(func.count())
        .select_from(OmniLeadLog)
        .where(
            OmniLeadLog.clinic_id == clinic_id,
            OmniLeadLog.closed_at >= start_dt,
            OmniLeadLog.closed_at < end_dt,
        )
    )
    total = int(total_res.scalar_one() or 0)

    by_outcome_rows = await session.execute(
        select(OmniLeadLog.outcome, func.count())
        .select_from(OmniLeadLog)
        .where(
            OmniLeadLog.clinic_id == clinic_id,
            OmniLeadLog.closed_at >= start_dt,
            OmniLeadLog.closed_at < end_dt,
        )
        .group_by(OmniLeadLog.outcome)
        .order_by(func.count().desc())
    )
    by_outcome = [
        LeadLogsOutcomeStatDto(outcome=str(o or "UNKNOWN"), count=int(c)) for o, c in by_outcome_rows.all()
    ]

    by_admin_rows = await session.execute(
        select(OmniLeadLog.opened_by_admin_id, func.count())
        .select_from(OmniLeadLog)
        .where(
            OmniLeadLog.clinic_id == clinic_id,
            OmniLeadLog.closed_at >= start_dt,
            OmniLeadLog.closed_at < end_dt,
        )
        .group_by(OmniLeadLog.opened_by_admin_id)
    )
    by_admin_map = {aid: int(cnt) for aid, cnt in by_admin_rows.all()}
    admin_ids = {aid for aid in by_admin_map.keys() if aid is not None}
    names = await _admin_display_names(session, admin_ids)
    by_admin = [
        LeadLogsAdminStatDto(admin_id=aid, admin_name=names.get(aid) if aid else None, count=cnt)
        for aid, cnt in sorted(by_admin_map.items(), key=lambda x: (-(x[1] or 0), str(x[0] or "")))
    ]

    avg_close_res = await session.execute(
        select(func.avg(func.extract("epoch", OmniLeadLog.closed_at - OmniLeadLog.opened_at)))
        .select_from(OmniLeadLog)
        .where(
            OmniLeadLog.clinic_id == clinic_id,
            OmniLeadLog.opened_at.is_not(None),
            OmniLeadLog.closed_at >= start_dt,
            OmniLeadLog.closed_at < end_dt,
        )
    )
    avg_close = avg_close_res.scalar_one_or_none()

    return LeadLogsStatsResponse(
        date_from=date_from,
        date_to=date_to,
        total=total,
        by_outcome=by_outcome,
        by_admin=by_admin,
        avg_time_to_close_seconds=float(avg_close) if avg_close is not None else None,
    )


@router.get(
    "",
    response_model=list[OmniLeadLogListItemDto],
    dependencies=[Depends(require_permissions("leads.log.view"))],
)
async def list_lead_logs(
    day: str = Query(..., description="YYYY-MM-DD (UTC day)"),
    outcome: str | None = Query(None, description="Optional: BOOKED | NOT_BOOKED | UNKNOWN"),
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("leads.log.view")),
) -> list[OmniLeadLogListItemDto]:
    clinic_id = admin_ctx.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    try:
        d = date.fromisoformat(day)
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="day must be YYYY-MM-DD")
    start_dt, end_dt = _day_bounds_utc(d)

    stmt = (
        select(OmniLeadLog, OmniContact)
        .join(OmniContact, OmniLeadLog.contact_id == OmniContact.id)
        .where(OmniLeadLog.clinic_id == clinic_id)
        .where(OmniLeadLog.closed_at >= start_dt, OmniLeadLog.closed_at < end_dt)
        .order_by(OmniLeadLog.closed_at.desc())
    )
    if outcome:
        stmt = stmt.where(OmniLeadLog.outcome == outcome.strip().upper())
    rows = (await session.execute(stmt)).all()
    admin_ids = {r[0].opened_by_admin_id for r in rows if r[0].opened_by_admin_id}
    names = await _admin_display_names(session, admin_ids)
    out: list[OmniLeadLogListItemDto] = []
    for log, contact in rows:
        out.append(
            OmniLeadLogListItemDto(
                id=log.id,
                clinic_id=log.clinic_id,
                omni_chat_id=log.omni_chat_id,
                contact_id=log.contact_id,
                contact_name=getattr(contact, "full_name", None),
                contact_primary_phone=getattr(contact, "primary_phone", None),
                opened_by_admin_id=log.opened_by_admin_id,
                opened_by_admin_name=names.get(log.opened_by_admin_id) if log.opened_by_admin_id else None,
                opened_at=log.opened_at,
                closed_at=log.closed_at,
                title=log.title,
                outcome=log.outcome,
                lead_id=log.lead_id,
                booking_id=log.booking_id,
                patient_id=log.patient_id,
            )
        )
    return out


@router.get(
    "/{log_id}",
    response_model=OmniLeadLogDetailDto,
    dependencies=[Depends(require_permissions("leads.log.view"))],
)
async def get_lead_log(
    log_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("leads.log.view")),
) -> OmniLeadLogDetailDto:
    clinic_id = admin_ctx.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    stmt = (
        select(OmniLeadLog, OmniContact)
        .join(OmniContact, OmniLeadLog.contact_id == OmniContact.id)
        .where(OmniLeadLog.id == log_id, OmniLeadLog.clinic_id == clinic_id)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead log not found")
    log, contact = row
    names = await _admin_display_names(session, {log.opened_by_admin_id} if log.opened_by_admin_id else set())
    return OmniLeadLogDetailDto(
        id=log.id,
        clinic_id=log.clinic_id,
        omni_chat_id=log.omni_chat_id,
        contact_id=log.contact_id,
        contact_name=getattr(contact, "full_name", None),
        contact_primary_phone=getattr(contact, "primary_phone", None),
        opened_by_admin_id=log.opened_by_admin_id,
        opened_by_admin_name=names.get(log.opened_by_admin_id) if log.opened_by_admin_id else None,
        opened_at=log.opened_at,
        closed_at=log.closed_at,
        title=log.title,
        outcome=log.outcome,
        lead_id=log.lead_id,
        booking_id=log.booking_id,
        patient_id=log.patient_id,
        transcript_text=log.transcript_text,
        transcript_json=log.transcript_json or {},
    )

