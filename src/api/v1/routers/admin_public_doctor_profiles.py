"""Admin API: manage public doctor profiles (client-facing)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.clinic_scope import assert_clinic_in_scope
from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.public_doctor_profile_dto import (
    PublicDoctorProfileCreate,
    PublicDoctorProfilePatch,
    PublicDoctorProfileRead,
)
from src.application.services.slug_service import validate_slug
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.doctor import Doctor
from src.domain.entities.public_doctor_profile import PublicDoctorProfile

router = APIRouter(prefix="/admin/clinics", tags=["admin-public-doctor-profiles"])


@router.get("/{clinic_id}/public-doctor-profiles", response_model=list[PublicDoctorProfileRead])
async def list_public_doctor_profiles(
    clinic_id: UUID,
    doctor_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[PublicDoctorProfileRead]:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    stmt = select(PublicDoctorProfile).where(
        PublicDoctorProfile.clinic_id == clinic_id,
        PublicDoctorProfile.deleted_at.is_(None),
    )
    if doctor_id is not None:
        stmt = stmt.where(PublicDoctorProfile.doctor_id == doctor_id)
    stmt = stmt.order_by(PublicDoctorProfile.updated_at.desc())
    res = await session.execute(stmt)
    return [PublicDoctorProfileRead.model_validate(x) for x in res.scalars().all()]


@router.post(
    "/{clinic_id}/public-doctor-profiles",
    response_model=PublicDoctorProfileRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_public_doctor_profile(
    clinic_id: UUID,
    data: PublicDoctorProfileCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
) -> PublicDoctorProfileRead:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    if not validate_slug(data.doctor_slug):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый slug")

    # Guard doctor belongs to clinic.
    d = await session.execute(
        select(Doctor).where(
            Doctor.id == data.doctor_id,
            Doctor.clinic_id == clinic_id,
            Doctor.deleted_at.is_(None),
        )
    )
    doctor = d.scalar_one_or_none()
    if doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Врач не найден")

    existing = await session.execute(
        select(PublicDoctorProfile).where(
            PublicDoctorProfile.clinic_id == clinic_id,
            PublicDoctorProfile.doctor_id == data.doctor_id,
            PublicDoctorProfile.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Публичная карточка для врача уже существует")

    slug_taken = await session.execute(
        select(PublicDoctorProfile.id).where(
            PublicDoctorProfile.clinic_id == clinic_id,
            PublicDoctorProfile.doctor_slug == data.doctor_slug.strip().lower(),
            PublicDoctorProfile.deleted_at.is_(None),
        )
    )
    if slug_taken.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug уже занят")

    row = PublicDoctorProfile(
        clinic_id=clinic_id,
        doctor_id=data.doctor_id,
        doctor_slug=data.doctor_slug.strip().lower(),
        is_published=bool(data.is_published),
        public_photo_url=data.public_photo_url,
        short_bio=data.short_bio,
        about_md=data.about_md,
        languages=data.languages,
        education=data.education,
        certifications=data.certifications,
        created_by_admin_id=current_admin.id,
        updated_by_admin_id=current_admin.id,
    )
    session.add(row)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug уже занят") from e
    await session.refresh(row)
    return PublicDoctorProfileRead.model_validate(row)


@router.patch(
    "/{clinic_id}/public-doctor-profiles/{profile_id}",
    response_model=PublicDoctorProfileRead,
)
async def patch_public_doctor_profile(
    clinic_id: UUID,
    profile_id: UUID,
    data: PublicDoctorProfilePatch,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
) -> PublicDoctorProfileRead:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    if not data.model_fields_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления")

    res = await session.execute(
        select(PublicDoctorProfile).where(
            PublicDoctorProfile.id == profile_id,
            PublicDoctorProfile.clinic_id == clinic_id,
            PublicDoctorProfile.deleted_at.is_(None),
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Карточка не найдена")

    if "doctor_slug" in data.model_fields_set and data.doctor_slug is not None:
        slug = data.doctor_slug.strip().lower()
        if not validate_slug(slug):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый slug")
        slug_taken = await session.execute(
            select(PublicDoctorProfile.id).where(
                PublicDoctorProfile.clinic_id == clinic_id,
                PublicDoctorProfile.doctor_slug == slug,
                PublicDoctorProfile.deleted_at.is_(None),
                PublicDoctorProfile.id != profile_id,
            )
        )
        if slug_taken.first() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug уже занят")
        row.doctor_slug = slug
    if "is_published" in data.model_fields_set and data.is_published is not None:
        row.is_published = bool(data.is_published)
    if "public_photo_url" in data.model_fields_set:
        row.public_photo_url = data.public_photo_url
    if "short_bio" in data.model_fields_set:
        row.short_bio = data.short_bio
    if "about_md" in data.model_fields_set:
        row.about_md = data.about_md
    if "languages" in data.model_fields_set:
        row.languages = data.languages
    if "education" in data.model_fields_set:
        row.education = data.education
    if "certifications" in data.model_fields_set:
        row.certifications = data.certifications

    row.updated_by_admin_id = current_admin.id
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug уже занят") from e
    await session.refresh(row)
    return PublicDoctorProfileRead.model_validate(row)


@router.delete(
    "/{clinic_id}/public-doctor-profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_public_doctor_profile(
    clinic_id: UUID,
    profile_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
) -> None:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    res = await session.execute(
        select(PublicDoctorProfile).where(
            PublicDoctorProfile.id == profile_id,
            PublicDoctorProfile.clinic_id == clinic_id,
            PublicDoctorProfile.deleted_at.is_(None),
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Карточка не найдена")
    row.deleted_at = datetime.utcnow()
    await session.flush()

