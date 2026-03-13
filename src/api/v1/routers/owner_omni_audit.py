"""Owner API for omnichannel audit log (Phase 3 Review).

Endpoint: GET /owner/audit-log — list audit entries for current business with filters and pagination.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.core.datetime_utils import to_iso8601_utc
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.omnichannel_audit_log import AuditLog as OmniAuditLog

router = APIRouter(prefix="/owner/audit-log", tags=["owner-omni-audit"])


class OwnerAuditLogEntryDto(BaseModel):
    id: UUID
    business_account_id: UUID
    actor_id: UUID | None
    actor_type: str
    action_type: str
    target_type: str
    target_id: UUID | None
    meta: dict = Field(default_factory=dict, description="Data from audit metadata column")
    created_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str:
        return to_iso8601_utc(value) or ""


class OwnerAuditLogResponse(BaseModel):
    items: list[OwnerAuditLogEntryDto]
    total: int


@router.get("", response_model=OwnerAuditLogResponse)
async def get_owner_audit_log(
    type: str | None = Query(None, description="Filter by action_type"),
    actor: str | None = Query(None, description="Filter by actor_type"),
    from_date: datetime | None = Query(None, alias="from", description="Filter created_at >= from (ISO)"),
    to_date: datetime | None = Query(None, alias="to", description="Filter created_at <= to (ISO)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OwnerAuditLogResponse:
    """Return audit log entries for current business account with optional filters and pagination."""
    business_account_id: UUID = current_admin.clinic_id

    stmt = select(OmniAuditLog).where(
        OmniAuditLog.business_account_id == business_account_id
    )
    if type:
        stmt = stmt.where(OmniAuditLog.action_type == type)
    if actor:
        stmt = stmt.where(OmniAuditLog.actor_type == actor)
    if from_date is not None:
        stmt = stmt.where(OmniAuditLog.created_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(OmniAuditLog.created_at <= to_date)

    from sqlalchemy import func
    count_stmt = select(func.count(OmniAuditLog.id)).select_from(OmniAuditLog).where(
        OmniAuditLog.business_account_id == business_account_id
    )
    if type:
        count_stmt = count_stmt.where(OmniAuditLog.action_type == type)
    if actor:
        count_stmt = count_stmt.where(OmniAuditLog.actor_type == actor)
    if from_date is not None:
        count_stmt = count_stmt.where(OmniAuditLog.created_at >= from_date)
    if to_date is not None:
        count_stmt = count_stmt.where(OmniAuditLog.created_at <= to_date)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = stmt.order_by(OmniAuditLog.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    items = [
        OwnerAuditLogEntryDto(
            id=row.id,
            business_account_id=row.business_account_id,
            actor_id=row.actor_id,
            actor_type=row.actor_type,
            action_type=row.action_type,
            target_type=row.target_type,
            target_id=row.target_id,
            meta=row.meta or {},
            created_at=row.created_at,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
        )
        for row in rows
    ]
    return OwnerAuditLogResponse(items=items, total=total)
