"""Shared helpers for admin staff routers.

Keep router modules decoupled: do not import from each other.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.application.services.staff_collaboration_service import StaffCollaborationService
from src.domain.entities.admin_user import AdminUser, EMPLOYMENT_ACTIVE


def staff_collab_svc(session: AsyncSession) -> StaffCollaborationService:
    return StaffCollaborationService(session)


def require_clinic_id(ctx: AdminContext) -> UUID:
    if ctx.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    return ctx.clinic_id


async def _admin_in_clinic(session: AsyncSession, clinic_id: UUID, admin_id: UUID) -> bool:
    res = await session.execute(
        select(AdminUser.id).where(
            AdminUser.id == admin_id,
            AdminUser.clinic_id == clinic_id,
            AdminUser.deleted_at.is_(None),
            AdminUser.employment_status == EMPLOYMENT_ACTIVE,
        )
    )
    return res.scalar_one_or_none() is not None


async def require_active_clinic_admin(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions()),
) -> AdminContext:
    """Любой активный администратор в контексте своей клиники.

    Для **внутренней стены** (лента персонала): чтение, лайки и комментарии доступны всем
    сотрудникам с учётной записью админки этой клиники, без отдельного ``view_staff_collab``.
    Чат, календарь и база знаний по-прежнему требуют ``view_staff_collab``.
    """

    if context.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Требуется пользователь",
        )
    cid = require_clinic_id(context)
    if not await _admin_in_clinic(session, cid, context.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к клинике",
        )
    return context

