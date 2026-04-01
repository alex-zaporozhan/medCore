"""Public API: doctor profile pages by clinic_slug + doctor_slug."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.public_doctor_profile_dto import PublicDoctorProfilePublicDto
from src.domain.entities.clinic import Clinic
from src.domain.entities.doctor import Doctor
from src.domain.entities.public_doctor_profile import PublicDoctorProfile

router = APIRouter(prefix="/public/clinics", tags=["public"])


@router.get("/by-slug/{clinic_slug}/doctors/{doctor_slug}", response_model=PublicDoctorProfilePublicDto)
async def get_public_doctor_profile_by_slugs(
    clinic_slug: str,
    doctor_slug: str,
    session: AsyncSession = Depends(get_session),
) -> PublicDoctorProfilePublicDto:
    clinic_slug_norm = (clinic_slug or "").strip().lower()
    doctor_slug_norm = (doctor_slug or "").strip().lower()
    if not clinic_slug_norm or not doctor_slug_norm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не найдено")

    c = await session.execute(
        select(Clinic).where(
            Clinic.clinic_slug == clinic_slug_norm,
            Clinic.deleted_at.is_(None),
        ).limit(1)
    )
    clinic = c.scalar_one_or_none()
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не найдено")

    stmt = (
        select(PublicDoctorProfile, Doctor)
        .join(Doctor, Doctor.id == PublicDoctorProfile.doctor_id)
        .where(
            PublicDoctorProfile.clinic_id == clinic.id,
            PublicDoctorProfile.doctor_slug == doctor_slug_norm,
            PublicDoctorProfile.is_published.is_(True),
            PublicDoctorProfile.deleted_at.is_(None),
            Doctor.deleted_at.is_(None),
            Doctor.is_active.is_(True),
        )
        .limit(1)
    )
    res = await session.execute(stmt)
    row = res.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не найдено")
    profile, doctor = row

    return PublicDoctorProfilePublicDto(
        clinic_id=str(clinic.id),
        clinic_slug=clinic_slug_norm,
        doctor_id=str(doctor.id),
        doctor_slug=doctor_slug_norm,
        doctor_full_name=doctor.full_name,
        doctor_specialization=doctor.specialization,
        doctor_photo_url=doctor.photo_url,
        doctor_display_role=getattr(doctor, "display_role", None),
        public_photo_url=profile.public_photo_url,
        short_bio=profile.short_bio,
        about_md=profile.about_md,
        languages=profile.languages,
        education=profile.education,
        certifications=profile.certifications,
    )

