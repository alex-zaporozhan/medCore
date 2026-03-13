"""Admin API: list and create administrators (same clinic)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin, hash_password
from src.domain.entities.admin_user import AdminUser

router = APIRouter(prefix="/admin/admins", tags=["admin-admins"])

MIN_PASSWORD_LENGTH = 8


class AdminRead(BaseModel):
    id: str
    clinic_id: str
    email: str
    full_name: str | None
    birth_date: str | None


class AdminCreate(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=200)
    full_name: str | None = Field(None, max_length=255)
    birth_date: str | None = None


@router.get("", response_model=list[AdminRead])
async def list_admins(
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[AdminRead]:
    result = await session.execute(
        select(AdminUser).where(
            AdminUser.clinic_id == current_admin.clinic_id,
            AdminUser.deleted_at.is_(None),
        ).order_by(AdminUser.created_at.asc())
    )
    admins = list(result.scalars().all())
    return [
        AdminRead(
            id=str(a.id),
            clinic_id=str(a.clinic_id),
            email=a.email,
            full_name=a.full_name,
            birth_date=a.birth_date.isoformat() if a.birth_date else None,
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
    admin = AdminUser(
        clinic_id=current_admin.clinic_id,
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
    )
