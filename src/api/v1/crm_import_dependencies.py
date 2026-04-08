"""CRM import: effective organization + entitlement (Phase 3+, QA_ARCH hardening).

Router-level require_entitlement(admin.organization_id) would bypass SaaS gate when the admin
row has no organization_id but the clinic is linked to an org with enforced entitlements.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.effective_organization import resolve_effective_organization_id
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.organization_entitlement_access import (
    ensure_org_has_any_entitlement_for_organization,
)
from src.domain.entities.admin_user import AdminUser


async def get_crm_import_organization_id(
    admin: AdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> UUID:
    try:
        org_id = await resolve_effective_organization_id(session, admin)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "organization_required_for_crm_import",
                    "message": "Импорт CRM привязан к организации; у клиники нет organization_id.",
                },
            ) from exc
        raise

    await ensure_org_has_any_entitlement_for_organization(session, org_id, "import.crm_v1")
    return org_id
