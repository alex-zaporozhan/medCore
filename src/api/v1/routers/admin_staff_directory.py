"""Staff directory: profession categories and clinic-scoped admin accounts."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.clinic_scope import assert_clinic_in_scope
from src.api.v1.dependencies import get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin, hash_password
from src.application.dto.staff_directory_dto import (
    StaffDirectoryAdminRead,
    StaffProfessionCategoryCreate,
    StaffProfessionCategoryPatch,
    StaffProfessionCategoryRead,
)
from src.application.services.staff_collaboration_service import StaffCollaborationService
from src.application.services.staff_directory_cache import (
    get_staff_cached_json,
    profession_categories_cache_key,
    set_staff_cached_json,
)
from src.application.services.rbac_user_roles_write import (
    ensure_role_codes_exist,
    replace_user_roles_for_clinic,
)
from src.application.services.staff_directory_service import StaffDirectoryService
from src.domain.entities.admin_user import AdminUser, EMPLOYMENT_ACTIVE, EMPLOYMENT_TERMINATED
from src.domain.entities.staff_profession_category import StaffProfessionCategory

router = APIRouter(
    prefix="/admin/clinics",
    tags=["admin-staff-directory"],
    dependencies=[Depends(require_permissions("manage_staff_directory"))],
)

MIN_PASSWORD_LENGTH = 8


def _svc(session: AsyncSession) -> StaffDirectoryService:
    return StaffDirectoryService(session)


class StaffAdminCreate(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=200)
    full_name: str | None = Field(None, max_length=255)
    birth_date: str | None = None
    profession_category_id: str | None = None
    role_codes: list[str] = Field(..., min_length=1, max_length=32)


class StaffAdminPatch(BaseModel):
    """PATCH body: only fields present in JSON are applied (see model_fields_set)."""

    model_config = ConfigDict(extra="forbid")
    employment_status: str | None = Field(default=None, description="active | terminated")
    profession_category_id: str | None = Field(default=None)


async def _assert_pc_in_clinic(
    session: AsyncSession, clinic_id: UUID, category_id: UUID
) -> StaffProfessionCategory:
    res = await session.execute(
        select(StaffProfessionCategory).where(
            StaffProfessionCategory.id == category_id,
            StaffProfessionCategory.clinic_id == clinic_id,
            StaffProfessionCategory.deleted_at.is_(None),
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимая категория профессии")
    return row


@router.get("/{clinic_id}/staff-directory/profession-categories")
async def list_profession_categories(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Response:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    key = profession_categories_cache_key(clinic_id)
    cached = await get_staff_cached_json(key)
    if cached is not None:
        return Response(content=cached, media_type="application/json")
    items = await _svc(session).list_profession_categories(clinic_id)
    payload = json.dumps([x.model_dump(mode="json") for x in items], ensure_ascii=False)
    await set_staff_cached_json(key, payload)
    return Response(content=payload, media_type="application/json")


@router.post(
    "/{clinic_id}/staff-directory/profession-categories",
    response_model=StaffProfessionCategoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_profession_category(
    clinic_id: UUID,
    data: StaffProfessionCategoryCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> StaffProfessionCategoryRead:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    await ensure_role_codes_exist(session, clinic_id, data.default_role_codes)
    try:
        return await _svc(session).create_profession_category(
            clinic_id, data.name, data.sort_order, data.default_role_codes
        )
    except ValueError as e:
        code = str(e)
        if code == "duplicate_name":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Категория с таким названием уже есть",
            ) from e
        if code == "empty_name":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустое название") from e
        raise


@router.patch(
    "/{clinic_id}/staff-directory/profession-categories/{category_id}",
    response_model=StaffProfessionCategoryRead,
)
async def patch_profession_category(
    clinic_id: UUID,
    category_id: UUID,
    data: StaffProfessionCategoryPatch,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> StaffProfessionCategoryRead:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    if not data.model_fields_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления")
    if "default_role_codes" in data.model_fields_set and data.default_role_codes is not None:
        await ensure_role_codes_exist(session, clinic_id, data.default_role_codes)
    try:
        row = await _svc(session).patch_profession_category(
            clinic_id,
            category_id,
            name=data.name if "name" in data.model_fields_set else None,
            sort_order=data.sort_order if "sort_order" in data.model_fields_set else None,
            default_role_codes=data.default_role_codes if "default_role_codes" in data.model_fields_set else None,
            actor_admin_id=current_admin.id,
        )
    except ValueError as e:
        code = str(e)
        if code == "duplicate_name":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Категория с таким названием уже есть",
            ) from e
        if code == "empty_name":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустое название") from e
        raise
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена")
    return row


@router.delete("/{clinic_id}/staff-directory/profession-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profession_category(
    clinic_id: UUID,
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    ok = await _svc(session).soft_delete_profession_category(clinic_id, category_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена")


@router.get("/{clinic_id}/staff-directory/admins", response_model=list[StaffDirectoryAdminRead])
async def list_staff_admins(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[StaffDirectoryAdminRead]:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    return await _svc(session).list_admins_with_profession(clinic_id)


@router.post("/{clinic_id}/staff-directory/admins", response_model=StaffDirectoryAdminRead, status_code=status.HTTP_201_CREATED)
async def create_staff_admin(
    clinic_id: UUID,
    data: StaffAdminCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> StaffDirectoryAdminRead:
    clinic = await assert_clinic_in_scope(session, current_admin, clinic_id)
    await ensure_role_codes_exist(session, clinic_id, data.role_codes)
    email = data.email.strip().lower()
    existing = await session.execute(
        select(AdminUser).where(AdminUser.email == email, AdminUser.deleted_at.is_(None)).limit(1)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Учётная запись с таким email уже занята в системе",
        )
    pc_id: UUID | None = None
    if data.profession_category_id:
        pc_id = UUID(data.profession_category_id)
        await _assert_pc_in_clinic(session, clinic_id, pc_id)

    birth_date = None
    if data.birth_date:
        try:
            from datetime import date

            birth_date = date.fromisoformat(data.birth_date)
        except ValueError:
            pass

    org_id = clinic.organization_id
    admin = AdminUser(
        clinic_id=clinic_id,
        organization_id=org_id,
        email=email,
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip() if data.full_name else None,
        birth_date=birth_date,
        profession_category_id=pc_id,
    )
    session.add(admin)
    await session.flush()
    await session.refresh(admin)
    await replace_user_roles_for_clinic(
        session,
        clinic_id=clinic_id,
        user_id=admin.id,
        role_codes=data.role_codes,
        actor_admin_id=current_admin.id,
        audit_action="staff.directory.user.create",
        entity_type="admin_user",
        entity_id=str(admin.id),
        note=None,
        preserve_owner_role=False,
    )
    rows = await _svc(session).list_admins_with_profession(clinic_id)
    match = next((r for r in rows if r.id == str(admin.id)), None)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Сотрудник не найден после сохранения",
        )
    return match


@router.patch("/{clinic_id}/staff-directory/admins/{admin_id}", response_model=StaffDirectoryAdminRead)
async def patch_staff_admin(
    clinic_id: UUID,
    admin_id: UUID,
    data: StaffAdminPatch,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> StaffDirectoryAdminRead:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    if not data.model_fields_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления")

    result = await session.execute(
        select(AdminUser).where(
            AdminUser.id == admin_id,
            AdminUser.clinic_id == clinic_id,
            AdminUser.deleted_at.is_(None),
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден")

    if "profession_category_id" in data.model_fields_set:
        if data.profession_category_id in (None, ""):
            target.profession_category_id = None
        else:
            pc = UUID(data.profession_category_id)
            await _assert_pc_in_clinic(session, clinic_id, pc)
            target.profession_category_id = pc

    if "employment_status" in data.model_fields_set:
        if data.employment_status is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="employment_status не может быть пустым")
        if data.employment_status not in (EMPLOYMENT_ACTIVE, EMPLOYMENT_TERMINATED):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый employment_status")
        if target.id == current_admin.id and data.employment_status == EMPLOYMENT_TERMINATED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя уволить самого себя",
            )
        target.employment_status = data.employment_status
        if data.employment_status == EMPLOYMENT_TERMINATED:
            collab = StaffCollaborationService(session)
            await collab.revoke_staff_chat_memberships_for_admin(admin_id)

    await session.flush()
    await session.refresh(target)
    rows = await _svc(session).list_admins_with_profession(clinic_id)
    match = next((r for r in rows if r.id == str(target.id)), None)
    if match is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Сотрудник не найден после сохранения")
    return match
