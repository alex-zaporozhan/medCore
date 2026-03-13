"""Admin API: store encrypted payment gateway credentials per clinic (non-YooKassa)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.clinic_payment_gateway_service import (
    ClinicPaymentGatewayService,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic

router = APIRouter(prefix="/admin/clinics", tags=["admin-payment-gateway"])


class AdminPaymentGatewayCredentialsRequest(BaseModel):
    gateway: str = Field(
        ...,
        max_length=32,
        description='Gateway code (e.g. "tinkoff", "sber", "robokassa", "stripe", "paypal", "custom")',
    )
    payload: str = Field(
        ...,
        max_length=8000,
        description="JSON string with provider-specific credentials",
    )


async def _ensure_clinic_belongs_to_admin(
    session: AsyncSession,
    clinic_id: UUID,
    current_admin: AdminUser,
) -> Clinic:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found",
        )
    stmt = select(Clinic).where(Clinic.id == clinic_id).limit(1)
    result = await session.execute(stmt)
    clinic = result.scalar_one_or_none()
    if clinic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found",
        )
    return clinic


@router.post(
    "/{clinic_id}/payment-gateway/credentials",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def set_clinic_payment_gateway_credentials(
    clinic_id: UUID,
    body: AdminPaymentGatewayCredentialsRequest,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    """Store or update encrypted payment gateway credentials for clinic.

    Raw payload is provided as JSON string and is never returned back to clients.
    """
    await _ensure_clinic_belongs_to_admin(session, clinic_id, current_admin)

    gateway = (body.gateway or "").strip().lower()
    if not gateway:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="gateway must be non-empty",
        )

    svc = ClinicPaymentGatewayService(session)
    await svc.upsert_credentials(
        clinic_id=clinic_id,
        gateway=gateway,
        raw_payload=body.payload,
        actor_id=current_admin.id,
    )

