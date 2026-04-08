"""Auth service for patient SMS-based authentication."""

import logging
import os
import random
import re
from datetime import date, timedelta
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.datetime_utils import utc_now_naive
from src.core.patient_messages import (
    AUTH_CONSENT_MAILING_REQUIRED,
    AUTH_CONSENT_PD_REQUIRED,
    AUTH_INVALID_OR_EXPIRED_CODE,
)
from src.core.security import create_access_token
from src.domain.entities.patient import Patient
from src.application.services.patient_entry_clinic import resolve_clinic_for_patient_entry
from src.infrastructure.database.redis_client import get_redis
from src.infrastructure.external_apis.sms_client import SmsClient, SmsClientError

logger = logging.getLogger(__name__)


class AuthService:
    """Service for patient auth via SMS code."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.session = session
        self._sms_client = SmsClient(timeout_seconds=settings.smsc_timeout_seconds, enabled=settings.smsc_enabled)

    async def _get_redis(self) -> Redis:
        """Get Redis client instance."""
        return await get_redis()

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone to E.164-like format for Russia."""
        # Remove all non-digit characters
        digits = re.sub(r"\D", "", phone)

        # If starts with 8 and 11 digits -> replace with 7
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]

        # If 10 digits (without country code) -> assume Russia
        if len(digits) == 10:
            digits = "7" + digits

        if not digits.startswith("7"):
            # Fallback: keep as is, but log only masked information to avoid leaking PD
            masked_raw = f"...{phone[-4:]}" if phone and len(phone) >= 4 else None
            masked_digits = f"...{digits[-4:]}" if digits and len(digits) >= 4 else None
            logger.warning(
                "Unexpected phone format",
                extra={
                    "phone_last4": masked_raw,
                    "digits_last4": masked_digits,
                    "raw_len": len(phone),
                    "digits_len": len(digits),
                },
            )

        return f"+{digits}"

    @staticmethod
    def _code_key(clinic_id: UUID, phone: str) -> str:
        """Build Redis key for auth code."""
        return f"auth:code:{clinic_id}:{phone}"

    async def send_code(self, phone: str, clinic_slug: str | None = None) -> None:
        """Generate and store SMS code, ensure patient exists."""
        clinic = await resolve_clinic_for_patient_entry(self.session, clinic_slug)
        normalized_phone = self._normalize_phone(phone)
        redis = await self._get_redis()

        code = f"{random.randint(0, 999_999):06d}"
        key = self._code_key(clinic.id, normalized_phone)

        # Ensure patient exists (MVP: minimal record with phone only)
        result = await self.session.execute(
            select(Patient).where(
                Patient.clinic_id == clinic.id,
                Patient.phone == normalized_phone,
                Patient.deleted_at.is_(None),
            )
        )
        patient = result.scalar_one_or_none()
        if patient is None:
            patient = Patient(clinic_id=clinic.id, phone=normalized_phone)
            self.session.add(patient)
            await self.session.flush()
            await self.session.refresh(patient)

        # Store code for 5 minutes only after we know the patient entity exists.
        await redis.setex(key, 300, code)

        masked_phone = f"...{normalized_phone[-4:]}" if len(normalized_phone) >= 4 else normalized_phone

        # In tests, skip real SMS; code is already in Redis for verify-code.
        if os.environ.get("TESTING") == "1":
            logger.info(
                "Auth code generated (TESTING=1, SMS skipped)",
                extra={
                    "clinic_id": str(clinic.id),
                    "phone_last4": masked_phone,
                    "patient_id": str(patient.id),
                },
            )
            return

        if self._sms_client.is_configured():
            try:
                # We never log the actual code or full phone number.
                await self._sms_client.send_sms(
                    normalized_phone,
                    "Код для входа в личный кабинет: {code}".format(code=code),
                )
            except SmsClientError as exc:
                logger.exception(
                    "Failed to send auth SMS",
                    extra={
                        "clinic_id": str(clinic.id),
                        "phone_last4": masked_phone,
                        "patient_id": str(patient.id),
                    },
                )
                raise RuntimeError("Не удалось отправить SMS с кодом. Попробуйте ещё раз позже.") from exc
        else:
            # In development or when SMS is disabled, we keep behaviour without external sending.
            logger.info(
                "Auth code generated (SMS sending is disabled)",
                extra={
                    "clinic_id": str(clinic.id),
                    "phone_last4": masked_phone,
                    "patient_id": str(patient.id),
                },
            )

    async def verify_code(
        self,
        phone: str,
        code: str,
        consent_pd: bool = True,
        consent_mailing: bool = False,
        full_name: str | None = None,
        birth_date: str | None = None,
        session_id: str | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        utm_content: str | None = None,
        utm_term: str | None = None,
        landing_page: str | None = None,
        anchor: str | None = None,
        clinic_slug: str | None = None,
    ) -> tuple[str, UUID]:
        """Verify SMS code and issue access token. Store consent and optional FIO/DOB."""
        clinic = await resolve_clinic_for_patient_entry(self.session, clinic_slug)
        normalized_phone = self._normalize_phone(phone)
        redis = await self._get_redis()

        key = self._code_key(clinic.id, normalized_phone)
        stored_code = await redis.get(key)

        if not stored_code or stored_code != code:
            masked_phone = f"...{normalized_phone[-4:]}" if len(normalized_phone) >= 4 else normalized_phone
            logger.warning(
                "Invalid auth code",
                extra={"clinic_id": str(clinic.id), "phone_last4": masked_phone},
            )
            raise ValueError(AUTH_INVALID_OR_EXPIRED_CODE)

        if not consent_pd:
            raise ValueError(AUTH_CONSENT_PD_REQUIRED)

        from src.domain.entities.agreement_settings import AgreementSettings

        result = await self.session.execute(
            select(AgreementSettings).where(AgreementSettings.clinic_id == clinic.id)
        )
        agreement = result.scalar_one_or_none()
        if agreement is not None and not agreement.allow_registration_without_mailing_consent and not consent_mailing:
            raise ValueError(AUTH_CONSENT_MAILING_REQUIRED)

        # One-time code: delete after successful verification
        await redis.delete(key)

        # Load patient (should exist after send_code; create as safety)
        result = await self.session.execute(
            select(Patient).where(
                Patient.clinic_id == clinic.id,
                Patient.phone == normalized_phone,
                Patient.deleted_at.is_(None),
            )
        )
        patient = result.scalar_one_or_none()
        now_utc = utc_now_naive()
        birth_date_parsed: date | None = None
        if birth_date:
            try:
                birth_date_parsed = date.fromisoformat(birth_date.strip())
            except ValueError:
                pass
        is_new_patient = patient is None
        if is_new_patient:
            patient = Patient(
                clinic_id=clinic.id,
                phone=normalized_phone,
                full_name=full_name.strip() if full_name and full_name.strip() else None,
                birth_date=birth_date_parsed,
                consent_pd_at=now_utc if consent_pd else None,
                consent_mailing=consent_mailing,
            )
            self.session.add(patient)
            await self.session.flush()
            await self.session.refresh(patient)
        else:
            if full_name and full_name.strip():
                patient.full_name = full_name.strip()
            if birth_date_parsed is not None:
                patient.birth_date = birth_date_parsed
            if consent_pd and patient.consent_pd_at is None:
                patient.consent_pd_at = now_utc
            patient.consent_mailing = consent_mailing
            await self.session.flush()

        # Try to link existing VisitAttribution (from landing/PWA) to this patient on first successful auth.
        if is_new_patient and session_id:
            from src.domain.entities.visit_attribution import VisitAttribution

            stmt = (
                select(VisitAttribution)
                .where(
                    VisitAttribution.clinic_id == clinic.id,
                    VisitAttribution.patient_id.is_(None),
                    VisitAttribution.session_id == session_id,
                )
                .order_by(VisitAttribution.created_at.asc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            visit = result.scalar_one_or_none()
            if visit is not None:
                visit.patient_id = patient.id
                self.session.add(visit)
                await self.session.flush()

        # Issue JWT access token for patient.
        # Token revocation (versioning/blacklist) is intentionally not implemented here (future hardening).
        token = create_access_token(
            data={
                "sub": str(patient.id),
                "role": "patient",
            },
            expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes_patient),
        )

        logger.info(
            "Patient authenticated",
            extra={"clinic_id": str(clinic.id), "patient_id": str(patient.id)},
        )

        return token, patient.id

