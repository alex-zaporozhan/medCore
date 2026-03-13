"""Service for storing and reading encrypted payment gateway credentials per clinic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.encryption import decrypt_ciphertext, encrypt_plaintext
from src.domain.entities.clinic_payment_gateway import ClinicPaymentGateway


class ClinicPaymentGatewayService:
    """Encapsulates work with clinic_payment_gateways table."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_by_clinic_and_gateway(
        self,
        clinic_id: UUID,
        gateway: str,
    ) -> ClinicPaymentGateway | None:
        stmt = select(ClinicPaymentGateway).where(
            ClinicPaymentGateway.clinic_id == clinic_id,
            ClinicPaymentGateway.gateway == gateway,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert_credentials(
        self,
        *,
        clinic_id: UUID,
        gateway: str,
        raw_payload: str,
        actor_id: UUID | None,
    ) -> ClinicPaymentGateway:
        """Create or update credentials for (clinic_id, gateway) with encrypted payload."""
        normalized_gateway = gateway.strip().lower()
        encrypted = encrypt_plaintext(raw_payload)

        row = await self._get_by_clinic_and_gateway(
            clinic_id=clinic_id,
            gateway=normalized_gateway,
        )
        if row is None:
            row = ClinicPaymentGateway(
                clinic_id=clinic_id,
                gateway=normalized_gateway,
                credentials_encrypted=encrypted,
                status="PENDING",
                created_by=actor_id,
                updated_by=actor_id,
            )
            self.session.add(row)
        else:
            row.credentials_encrypted = encrypted
            row.status = "PENDING"
            if row.created_by is None:
                row.created_by = actor_id
            row.updated_by = actor_id

        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_credentials(
        self,
        *,
        clinic_id: UUID,
        gateway: str,
    ) -> str | None:
        """Return decrypted JSON string payload for (clinic_id, gateway) or None."""
        normalized_gateway = gateway.strip().lower()
        row = await self._get_by_clinic_and_gateway(
            clinic_id=clinic_id,
            gateway=normalized_gateway,
        )
        if not row or not row.credentials_encrypted:
            return None
        return decrypt_ciphertext(row.credentials_encrypted)

