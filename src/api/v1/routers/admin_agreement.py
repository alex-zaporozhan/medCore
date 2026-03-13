"""Admin API: agreement settings (PD text, allow registration without mailing consent)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.agreement_dto import AgreementSettingsRead, AgreementSettingsUpdate
from src.domain.entities.agreement_settings import AgreementSettings

router = APIRouter(prefix="/admin/clinics", tags=["admin-agreement"])


@router.get("/{clinic_id}/agreement-settings", response_model=AgreementSettingsRead)
async def get_agreement_settings(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AgreementSettingsRead:
    """Get agreement settings for clinic. Creates default row if missing."""
    result = await session.execute(
        select(AgreementSettings).where(AgreementSettings.clinic_id == clinic_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return AgreementSettingsRead(
            clinic_id=clinic_id,
            pd_agreement_text=None,
            allow_registration_without_mailing_consent=True,
        )
    return AgreementSettingsRead(
        clinic_id=row.clinic_id,
        pd_agreement_text=row.pd_agreement_text,
        allow_registration_without_mailing_consent=row.allow_registration_without_mailing_consent,
    )


@router.put("/{clinic_id}/agreement-settings", response_model=AgreementSettingsRead)
async def update_agreement_settings(
    clinic_id: UUID,
    body: AgreementSettingsUpdate,
    session: AsyncSession = Depends(get_session),
) -> AgreementSettingsRead:
    """Create or update agreement settings for clinic."""
    result = await session.execute(
        select(AgreementSettings).where(AgreementSettings.clinic_id == clinic_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = AgreementSettings(
            clinic_id=clinic_id,
            pd_agreement_text=body.pd_agreement_text,
            allow_registration_without_mailing_consent=(
                body.allow_registration_without_mailing_consent
                if body.allow_registration_without_mailing_consent is not None
                else True
            ),
        )
        session.add(row)
        await session.flush()
        await session.refresh(row)
    else:
        if body.pd_agreement_text is not None:
            row.pd_agreement_text = body.pd_agreement_text
        if body.allow_registration_without_mailing_consent is not None:
            row.allow_registration_without_mailing_consent = body.allow_registration_without_mailing_consent
        await session.flush()
        await session.refresh(row)
    return AgreementSettingsRead(
        clinic_id=row.clinic_id,
        pd_agreement_text=row.pd_agreement_text,
        allow_registration_without_mailing_consent=row.allow_registration_without_mailing_consent,
    )
