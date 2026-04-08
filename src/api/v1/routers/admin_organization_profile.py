"""Admin: organization vertical profile (Phase 3+, МП §14)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.api.v1.effective_organization import resolve_effective_organization_id
from src.api.v1.routers.admin_auth import get_current_admin
from src.core.industry_profile import (
    ALLOWED_INDUSTRY_PROFILES,
    INDUSTRY_PROFILE_DENTAL,
    normalize_industry_profile,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.organization import Organization
from src.domain.entities.organization_industry_profile_audit import OrganizationIndustryProfileAudit

router = APIRouter(prefix="/admin/organization", tags=["admin-organization"])


class IndustryProfileRead(BaseModel):
    industry_profile: str
    organization_id: str | None = None


class IndustryProfileUpdate(BaseModel):
    industry_profile: str = Field(..., description="industry_dental | industry_generic")


@router.get("/industry-profile", response_model=IndustryProfileRead)
async def get_industry_profile(
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    _: None = Depends(require_permissions("view_crm")),
) -> IndustryProfileRead:
    """Чтение профиля отрасли по организации текущей клиники (RBAC: любой с view_crm)."""
    try:
        org_id = await resolve_effective_organization_id(session, admin)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            return IndustryProfileRead(
                industry_profile=INDUSTRY_PROFILE_DENTAL,
                organization_id=None,
            )
        raise
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организация не найдена")
    return IndustryProfileRead(
        industry_profile=org.industry_profile,
        organization_id=str(org_id),
    )


@router.patch("/industry-profile", response_model=IndustryProfileRead)
async def patch_industry_profile(
    data: IndustryProfileUpdate,
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    ctx: AdminContext = Depends(get_request_context),
    _: None = Depends(require_permissions("manage_crm")),
) -> IndustryProfileRead:
    """Смена vertical: только роль owner (сеть / владелец бизнеса)."""
    if "owner" not in ctx.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "owner_role_required",
                "message": "Профиль отрасли может менять только владелец организации.",
            },
        )
    org_id = await resolve_effective_organization_id(session, admin)
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организация не найдена")
    old_profile = org.industry_profile
    try:
        org.industry_profile = normalize_industry_profile(data.industry_profile)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_industry_profile",
                "message": str(e),
                "allowed": sorted(ALLOWED_INDUSTRY_PROFILES),
            },
        ) from e
    if org.industry_profile != old_profile:
        session.add(
            OrganizationIndustryProfileAudit(
                organization_id=org_id,
                actor_admin_id=admin.id,
                old_profile=old_profile,
                new_profile=org.industry_profile,
            )
        )
    await session.flush()
    return IndustryProfileRead(
        industry_profile=org.industry_profile,
        organization_id=str(org_id),
    )
