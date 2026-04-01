"""Admin staff announcements publish policy.

Moved out of `admin_staff_collab` to keep rights/policies centralized.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.api.v1.routers._admin_staff_common import (
    require_active_clinic_admin,
    require_clinic_id as _clinic_id,
    staff_collab_svc as _svc,
)
from src.application.dto.staff_collab_dto import (
    StaffAnnouncementPublishPolicyAuditListResponse,
    StaffAnnouncementPublishPolicyResponse,
    StaffAnnouncementPublishPolicyRow,
)

router = APIRouter(prefix="/admin/staff", tags=["admin-staff-announcement-policy"])


@router.get(
    "/feed/announcements/publish-policy",
    response_model=StaffAnnouncementPublishPolicyResponse,
    dependencies=[Depends(require_permissions("rbac.manage"))],
)
async def get_staff_announcement_publish_policy(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffAnnouncementPublishPolicyResponse:
    cid = _clinic_id(context)
    return await _svc(session).list_announcement_publish_policies(cid)


@router.put(
    "/feed/announcements/publish-policy",
    response_model=StaffAnnouncementPublishPolicyResponse,
    dependencies=[Depends(require_permissions("rbac.manage"))],
)
async def put_staff_announcement_publish_policy(
    rows: list[StaffAnnouncementPublishPolicyRow],
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffAnnouncementPublishPolicyResponse:
    cid = _clinic_id(context)
    return await _svc(session).upsert_announcement_publish_policies(
        cid,
        actor_admin_id=context.user_id,
        rows=rows,
    )


@router.get(
    "/feed/announcements/publish-policy/audit",
    response_model=StaffAnnouncementPublishPolicyAuditListResponse,
)
async def list_staff_announcement_publish_policy_audit(
    limit: int = Query(200, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> StaffAnnouncementPublishPolicyAuditListResponse:
    # Owner-only by default, with optional individual grant.
    is_owner = "owner" in set(context.roles or set())
    has_perm = "staff.announcements.policy.audit.view" in set(context.permissions or set())
    if not (is_owner or has_perm):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return await _svc(session).list_announcement_publish_policy_audits(_clinic_id(context), limit=limit)

