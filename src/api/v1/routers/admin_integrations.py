"""Admin API: integration settings (1C, Bitrix24) per clinic."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.core.encryption import encrypt_plaintext
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic_integration_settings import ClinicIntegrationSettings

router = APIRouter(prefix="/admin/clinics", tags=["admin-integrations"])


class IntegrationSettingsRead(BaseModel):
    provider: str
    api_url: str | None = None
    has_credentials: bool = False


class IntegrationSettingsUpdate(BaseModel):
    api_url: str | None = Field(None, max_length=500)
    credentials: str | None = Field(None, max_length=500)


async def _get_settings(session: AsyncSession, clinic_id: UUID, provider: str) -> ClinicIntegrationSettings | None:
    result = await session.execute(
        select(ClinicIntegrationSettings).where(
            ClinicIntegrationSettings.clinic_id == clinic_id,
            ClinicIntegrationSettings.provider == provider,
        ).limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/{clinic_id}/integration-settings/{provider}", response_model=IntegrationSettingsRead)
async def get_integration_settings(
    clinic_id: UUID,
    provider: str,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> IntegrationSettingsRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if provider not in ("1c", "bitrix24"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="provider must be 1c or bitrix24")
    row = await _get_settings(session, clinic_id, provider)
    if not row:
        return IntegrationSettingsRead(provider=provider, api_url=None, has_credentials=False)
    return IntegrationSettingsRead(
        provider=row.provider,
        api_url=row.api_url,
        has_credentials=bool(row.credentials_encrypted and row.credentials_encrypted.strip()),
    )


@router.put("/{clinic_id}/integration-settings/{provider}", response_model=IntegrationSettingsRead)
async def update_integration_settings(
    clinic_id: UUID,
    provider: str,
    data: IntegrationSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> IntegrationSettingsRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if provider not in ("1c", "bitrix24"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="provider must be 1c or bitrix24")
    row = await _get_settings(session, clinic_id, provider)
    if not row:
        row = ClinicIntegrationSettings(clinic_id=clinic_id, provider=provider)
        session.add(row)
        await session.flush()
    if data.api_url is not None:
        row.api_url = data.api_url.strip() or None
    if data.credentials is not None:
        row.credentials_encrypted = encrypt_plaintext(data.credentials) if data.credentials.strip() else None
    await session.flush()
    await session.refresh(row)
    return IntegrationSettingsRead(
        provider=row.provider,
        api_url=row.api_url,
        has_credentials=bool(row.credentials_encrypted and row.credentials_encrypted.strip()),
    )
