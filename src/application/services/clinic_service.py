"""Clinic service."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.clinic_dto import (
    ClinicCreate,
    ClinicRead,
    ClinicUpdate,
    PaymentOptionRead,
)
from src.core.encryption import encrypt_plaintext
from src.domain.entities.clinic import Clinic
from src.domain.interfaces.repositories.clinic_repository import ClinicRepository
from src.infrastructure.database.clinic_repo_impl import ClinicRepositoryImpl
from src.application.services.business_lexicon_service import build_business_lexicon

logger = logging.getLogger(__name__)

GATEWAY_DISPLAY_NAMES: dict[str, str] = {
    "yookassa": "ЮKassa",
    "tinkoff": "Тинькофф",
    "sber": "Сбербанк",
    "robokassa": "Robokassa",
    "stripe": "Stripe",
    "paypal": "PayPal",
    "custom": "Своя касса",
}


def _build_payment_options(clinic: Clinic) -> list[PaymentOptionRead]:
    """Build list of payment options (enabled gateways) for the client. Currently one active gateway per clinic."""
    if not getattr(clinic, "prepayment_enabled", False):
        return []
    gateway = getattr(clinic, "payment_gateway", None) or "yookassa"
    display = (
        getattr(clinic, "payment_gateway_custom_name", None) or None
    ) or GATEWAY_DISPLAY_NAMES.get(gateway, gateway)
    return [PaymentOptionRead(gateway_id=gateway, display_name=display)]


class ClinicService:
    """Service for clinic operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.repository: ClinicRepository = ClinicRepositoryImpl(session)

    async def create_clinic(self, data: ClinicCreate) -> ClinicRead:
        """Create a new clinic."""
        payload = data.model_dump(exclude_none=True)
        clinic = Clinic(**payload)
        clinic = await self.repository.create(clinic)
        logger.info("Clinic created via service", extra={"clinic_id": str(clinic.id)})
        lexicon = build_business_lexicon(clinic)
        dto = ClinicRead.model_validate(clinic)
        dto.business_lexicon = lexicon
        dto.payment_options = _build_payment_options(clinic)
        return dto

    async def get_clinic(self, clinic_id: UUID) -> ClinicRead | None:
        """Get clinic by ID."""
        clinic = await self.repository.get_by_id(clinic_id)
        if clinic is None:
            return None
        dto = ClinicRead.model_validate(clinic)
        dto.business_lexicon = build_business_lexicon(clinic)
        dto.payment_options = _build_payment_options(clinic)
        return dto

    async def get_clinics(self, include_deleted: bool = False) -> list[ClinicRead]:
        """Get all clinics."""
        clinics = await self.repository.get_all(include_deleted=include_deleted)
        result: list[ClinicRead] = []
        for clinic in clinics:
            dto = ClinicRead.model_validate(clinic)
            dto.business_lexicon = build_business_lexicon(clinic)
            dto.payment_options = _build_payment_options(clinic)
            result.append(dto)
        return result

    async def update_clinic(self, clinic_id: UUID, data: ClinicUpdate) -> ClinicRead | None:
        """Update clinic."""
        clinic = await self.repository.get_by_id(clinic_id)
        if clinic is None:
            return None

        full = data.model_dump(exclude_unset=True)
        update_data = {k: v for k, v in full.items() if v is not None and k != "yookassa_secret_key"}
        if "yookassa_secret_key" in full:
            raw = full["yookassa_secret_key"]
            clinic.yookassa_secret_key_encrypted = encrypt_plaintext(raw) if (raw and str(raw).strip()) else None
        for key, value in update_data.items():
            if hasattr(clinic, key):
                setattr(clinic, key, value)

        clinic = await self.repository.update(clinic)
        logger.info("Clinic updated via service", extra={"clinic_id": str(clinic_id)})
        dto = ClinicRead.model_validate(clinic)
        dto.business_lexicon = build_business_lexicon(clinic)
        dto.payment_options = _build_payment_options(clinic)
        return dto

    async def delete_clinic(self, clinic_id: UUID) -> bool:
        """Soft delete clinic."""
        clinic = await self.repository.get_by_id(clinic_id)
        if clinic is None:
            return False
        await self.repository.delete(clinic_id)
        logger.info("Clinic deleted via service", extra={"clinic_id": str(clinic_id)})
        return True

