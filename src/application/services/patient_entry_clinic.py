"""Resolve clinic for patient-facing auth (SMS/OAuth) from optional public slug."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.metrics import patient_auth_clinic_context_total
from src.core.patient_messages import AUTH_CLINIC_SLUG_REQUIRED, AUTH_UNKNOWN_CLINIC_SLUG
from src.domain.entities.clinic import Clinic


async def resolve_clinic_for_patient_entry(
    session: AsyncSession,
    clinic_slug: str | None,
) -> Clinic:
    """
    If ``clinic_slug`` is set: lookup active clinic by ``clinics.clinic_slug`` (case-insensitive).
    Otherwise: first clinic in DB (legacy single-tenant / dev), unless
    ``settings.patient_auth_require_clinic_slug`` is true (production policy).
    """
    if not (clinic_slug and clinic_slug.strip()):
        if settings.patient_auth_require_clinic_slug:
            patient_auth_clinic_context_total.labels(source="default", result="slug_required").inc()
            raise ValueError(AUTH_CLINIC_SLUG_REQUIRED)

    if clinic_slug and clinic_slug.strip():
        raw = clinic_slug.strip()
        result = await session.execute(
            select(Clinic)
            .where(
                func.lower(Clinic.clinic_slug) == func.lower(raw),
                Clinic.deleted_at.is_(None),
                Clinic.clinic_slug.is_not(None),
            )
            .limit(1)
        )
        clinic = result.scalar_one_or_none()
        if clinic is None:
            patient_auth_clinic_context_total.labels(source="slug", result="unknown").inc()
            raise ValueError(AUTH_UNKNOWN_CLINIC_SLUG)
        patient_auth_clinic_context_total.labels(source="slug", result="ok").inc()
        return clinic

    result = await session.execute(select(Clinic).where(Clinic.deleted_at.is_(None)).limit(1))
    clinic = result.scalar_one_or_none()
    if clinic is None:
        patient_auth_clinic_context_total.labels(source="default", result="empty_db").inc()
        raise RuntimeError("No clinic configured for auth")
    patient_auth_clinic_context_total.labels(source="default", result="ok").inc()
    return clinic
