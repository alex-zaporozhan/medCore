"""OAuth-based authentication service for patients."""

import logging
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.datetime_utils import utc_now_naive
from src.core.security import create_access_token
from src.domain.entities.clinic import Clinic
from src.domain.entities.patient import Patient
from src.infrastructure.database.redis_client import get_redis

logger = logging.getLogger(__name__)


class OAuthAuthService:
    """Service for patient authentication via OAuth providers (VK, Yandex)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_default_clinic(self) -> Clinic:
        result = await self.session.execute(select(Clinic).limit(1))
        clinic = result.scalar_one_or_none()
        if clinic is None:
            raise RuntimeError("No clinic configured for auth")
        return clinic

    async def _get_redis(self) -> Redis:
        return await get_redis()

    async def _authenticate_patient_with_oauth_id(
        self,
        *,
        provider: str,
        oauth_id: str,
        email: str | None = None,
        login: str | None = None,
    ) -> tuple[str, UUID]:
        clinic = await self._get_default_clinic()
        now_utc = utc_now_naive()

        query = select(Patient).where(
            Patient.clinic_id == clinic.id,
            Patient.deleted_at.is_(None),
        )
        if provider == "vk":
            query = query.where(Patient.vk_id == oauth_id)
        elif provider == "yandex":
            query = query.where(Patient.yandex_id == oauth_id)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        result = await self.session.execute(query)
        patient = result.scalar_one_or_none()

        if patient is None:
            patient = Patient(
                clinic_id=clinic.id,
                phone="+0000000000",
            )
            if provider == "vk":
                patient.vk_id = oauth_id
            elif provider == "yandex":
                patient.yandex_id = oauth_id
                if login:
                    patient.yandex_login = login
            if email:
                patient.email = email
            patient.consent_pd_at = now_utc
            self.session.add(patient)
            await self.session.flush()
            await self.session.refresh(patient)
        else:
            updated = False
            if provider == "yandex" and login and not patient.yandex_login:
                patient.yandex_login = login
                updated = True
            if email and not patient.email:
                patient.email = email
                updated = True
            if updated:
                await self.session.flush()

        token = create_access_token(
            data={"sub": str(patient.id), "role": "patient"},
            expires_delta=settings.jwt_access_token_expire_minutes_patient,
        )

        logger.info(
            "Patient authenticated via OAuth",
            extra={
                "clinic_id": str(clinic.id),
                "patient_id": str(patient.id),
                "provider": provider,
            },
        )

        return token, patient.id

    async def authenticate_vk(self, profile: dict[str, Any]) -> tuple[str, UUID]:
        user_id = str(profile.get("user_id") or "")
        if not user_id:
            raise ValueError("VK profile missing user_id")
        email = profile.get("email")
        return await self._authenticate_patient_with_oauth_id(
            provider="vk",
            oauth_id=user_id,
            email=email,
        )

    async def authenticate_yandex(self, profile: dict[str, Any]) -> tuple[str, UUID]:
        user_id = str(profile.get("id") or "")
        if not user_id:
            raise ValueError("Yandex profile missing id")
        email = profile.get("email")
        login = profile.get("login")
        return await self._authenticate_patient_with_oauth_id(
            provider="yandex",
            oauth_id=user_id,
            email=email,
            login=login,
        )

