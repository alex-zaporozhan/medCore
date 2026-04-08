"""FastAPI dependencies for SaaS entitlement gates (Phase 1c)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.organization_entitlement_access import ensure_org_has_any_entitlement
from src.domain.entities.admin_user import AdminUser


def require_entitlement(*keys: str):
    """
    Dependency factory: org must have at least one of the keys when SaaS enforcement is active.

    Usage:
        router = APIRouter(..., dependencies=[Depends(require_entitlement("tasks.kanban"))])
    """
    if not keys:
        raise ValueError("require_entitlement needs at least one entitlement key")

    async def _dep(
        admin: AdminUser = Depends(get_current_admin),
        session: AsyncSession = Depends(get_session),
    ) -> None:
        await ensure_org_has_any_entitlement(session, admin, *keys)

    return _dep
