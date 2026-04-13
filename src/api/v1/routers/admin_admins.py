"""Admin API: list and create administrators (same clinic)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.clinic import Clinic

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin, hash_password
from src.application.services.staff_collaboration_service import StaffCollaborationService
from src.domain.entities.admin_user import AdminUser, EMPLOYMENT_ACTIVE, EMPLOYMENT_TERMINATED

router = APIRouter(prefix="/admin/admins", tags=["admin-admins"])

MIN_PASSWORD_LENGTH = 8
_DEFAULT_ADMINS_LIST_LIMIT = 500
_MAX_ADMINS_LIST_LIMIT = 2000


class AdminRead(BaseModel):
    id: str
    clinic_id: str
    email: str
    full_name: str | None
    birth_date: str | None
    employment_status: str
    profession_category_id: str | None = None
    profession_category_name: str | None = None


class AdminCreate(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=200)
    full_name: str | None = Field(None, max_length=255)
    birth_date: str | None = None


class AdminPatch(BaseModel):
    """Увольнение / восстановление доступа (коробка)."""

    employment_status: str | None = Field(
        None,
        description="active | terminated",
    )


@router.get("", response_model=list[AdminRead])
async def list_admins(
    skip: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_ADMINS_LIST_LIMIT, ge=1, le=_MAX_ADMINS_LIST_LIMIT),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[AdminRead]:
    result = await session.execute(
        select(AdminUser)
        .where(
            AdminUser.clinic_id == current_admin.clinic_id,
            AdminUser.deleted_at.is_(None),
        )
        .order_by(AdminUser.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    admins = list(result.scalars().all())
    return [
        AdminRead(
            id=str(a.id),
            clinic_id=str(a.clinic_id),
            email=a.email,
            full_name=a.full_name,
            birth_date=a.birth_date.isoformat() if a.birth_date else None,
            employment_status=a.employment_status,
            profession_category_id=str(a.profession_category_id) if a.profession_category_id else None,
            profession_category_name=None,
        )
        for a in admins
    ]


@router.post("", response_model=AdminRead, status_code=status.HTTP_201_CREATED)
async def create_admin(
    data: AdminCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminRead:
    email = data.email.strip().lower()
    existing = await session.execute(
        select(AdminUser).where(AdminUser.email == email, AdminUser.deleted_at.is_(None)).limit(1)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Администратор с таким email уже существует",
        )
    birth_date = None
    if data.birth_date:
        try:
            from datetime import date
            birth_date = date.fromisoformat(data.birth_date)
        except ValueError:
            pass
    cres = await session.execute(select(Clinic).where(Clinic.id == current_admin.clinic_id))
    clinic = cres.scalar_one_or_none()
    admin = AdminUser(
        clinic_id=current_admin.clinic_id,
        organization_id=clinic.organization_id if clinic else None,
        email=email,
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip() or None,
        birth_date=birth_date,
    )
    session.add(admin)
    await session.flush()
    await session.refresh(admin)
    return AdminRead(
        id=str(admin.id),
        clinic_id=str(admin.clinic_id),
        email=admin.email,
        full_name=admin.full_name,
        birth_date=admin.birth_date.isoformat() if admin.birth_date else None,
        employment_status=admin.employment_status,
        profession_category_id=str(admin.profession_category_id) if admin.profession_category_id else None,
        profession_category_name=None,
    )


def _to_admin_read(a: AdminUser) -> AdminRead:
    return AdminRead(
        id=str(a.id),
        clinic_id=str(a.clinic_id),
        email=a.email,
        full_name=a.full_name,
        birth_date=a.birth_date.isoformat() if a.birth_date else None,
        employment_status=a.employment_status,
        profession_category_id=str(a.profession_category_id) if a.profession_category_id else None,
        profession_category_name=None,
    )


@router.patch("/{admin_id}", response_model=AdminRead)
async def patch_admin(
    admin_id: UUID,
    data: AdminPatch,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminRead:
    """Смена статуса занятости (уволен — без входа в админку, участие в чатах снимается)."""
    if data.employment_status is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления")
    if data.employment_status not in (EMPLOYMENT_ACTIVE, EMPLOYMENT_TERMINATED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый employment_status")
    result = await session.execute(
        select(AdminUser).where(
            AdminUser.id == admin_id,
            AdminUser.clinic_id == current_admin.clinic_id,
            AdminUser.deleted_at.is_(None),
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Администратор не найден")
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
    return _to_admin_read(target)
