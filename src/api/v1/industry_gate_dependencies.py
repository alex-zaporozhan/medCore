"""FastAPI dependencies: industry / vertical gates (Phase 3+ §14)."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.core.industry_profile import is_dental_clinical_vertical
from src.domain.entities.clinic import Clinic
from src.domain.entities.organization import Organization


async def require_dental_medical_clinic(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Stomatology-specific medical record module: disabled when org vertical is not dental.
    Clinics without organization_id remain dental (legacy installs).
    """
    clinic = await session.get(Clinic, clinic_id)
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Клиника не найдена")
    if clinic.organization_id is None:
        return
    org = await session.get(Organization, clinic.organization_id)
    profile = org.industry_profile if org else None
    if is_dental_clinical_vertical(profile):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "medical_module_industry_not_dental",
            "message": "Медицинская карта недоступна для выбранного профиля отрасли организации.",
        },
    )
