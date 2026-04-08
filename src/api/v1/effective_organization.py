"""Effective organization_id for admin routes (Phase 3+ QA_ARCH): admin row vs clinic.organization_id."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic


async def resolve_effective_organization_id(session: AsyncSession, admin: AdminUser) -> UUID:
    """
    Same resolution rules as CRM import / vertical: prefer admin.organization_id, else clinic.organization_id;
    reject when both are set and differ.
    """
    clinic = await session.get(Clinic, admin.clinic_id)
    org_from_clinic = clinic.organization_id if clinic is not None else None
    org_from_admin = admin.organization_id

    if (
        org_from_admin is not None
        and org_from_clinic is not None
        and org_from_admin != org_from_clinic
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "admin_clinic_organization_mismatch",
                "message": "organization_id администратора не совпадает с организацией клиники.",
            },
        )

    org_id = org_from_admin if org_from_admin is not None else org_from_clinic
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "organization_required",
                "message": "Нет привязанной организации для этой операции.",
            },
        )
    return org_id
