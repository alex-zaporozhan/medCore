"""Strict clinic scope checks for multi-clinic / network owners (enterprise)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic
from src.infrastructure.database.rbac_repo_impl import RbacRepositoryImpl


async def assert_clinic_in_scope(
    session: AsyncSession,
    admin: AdminUser,
    target_clinic_id: UUID,
) -> Clinic:
    """
    Resolve clinic for admin operations.

    - Same clinic as JWT: always allowed.
    - Another clinic in the same organization: only role ``owner`` at home clinic.
    - Otherwise: 404 (no cross-tenant leakage) or 403.
    """
    result = await session.execute(
        select(Clinic).where(Clinic.id == target_clinic_id, Clinic.deleted_at.is_(None))
    )
    clinic = result.scalar_one_or_none()
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Клиника не найдена")
    if admin.clinic_id == target_clinic_id:
        return clinic
    if admin.organization_id is None or clinic.organization_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Клиника не найдена")
    if admin.organization_id != clinic.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Клиника не найдена")
    rbac = RbacRepositoryImpl(session)
    roles = await rbac.get_role_codes_for_user(admin.id, admin.clinic_id)
    if "owner" not in set(roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой клинике")
    return clinic


async def resolve_effective_clinic_id(
    session: AsyncSession,
    admin: AdminUser,
    jwt_clinic_id: UUID,
    effective_clinic_id: UUID | None,
) -> UUID:
    """Use JWT clinic unless owner explicitly targets another clinic in the same organization."""
    if effective_clinic_id is None or effective_clinic_id == jwt_clinic_id:
        return jwt_clinic_id
    await assert_clinic_in_scope(session, admin, effective_clinic_id)
    return effective_clinic_id
