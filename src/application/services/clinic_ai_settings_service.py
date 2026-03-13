"""Service for managing per-clinic AI settings and effective prompts."""

from __future__ import annotations

from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.clinic import Clinic
from src.domain.entities.clinic_ai_settings import ClinicAiSettings


ALLOWED_AI_MODES: set[str] = {"draft_only", "safe_autoreply", "analytics_only"}
ALLOWED_INTENTS: set[str] = {"schedule", "location", "faq", "booking_change", "price_info"}


class ClinicAiSettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_default(self, clinic_id: UUID) -> ClinicAiSettings:
        stmt = select(ClinicAiSettings).where(ClinicAiSettings.clinic_id == clinic_id)
        result = await self.session.execute(stmt)
        settings = result.scalars().first()
        if settings:
            return settings
        settings = ClinicAiSettings(
            clinic_id=clinic_id,
            ai_enabled=False,
            ai_mode="draft_only",
            ai_allowed_intents=[],
            ai_autoreply_enabled=False,
            ai_provider_type="external",
        )
        self.session.add(settings)
        await self.session.flush()
        return settings

    async def update_settings(self, clinic_id: UUID, data: dict) -> ClinicAiSettings:
        settings = await self.get_or_create_default(clinic_id)

        if "ai_mode" in data:
            mode = data["ai_mode"]
            if mode not in ALLOWED_AI_MODES:
                raise ValueError("Invalid ai_mode")
            settings.ai_mode = mode
        if "ai_enabled" in data:
            settings.ai_enabled = bool(data["ai_enabled"])
        if "ai_business_prompt" in data:
            settings.ai_business_prompt = data["ai_business_prompt"]
        if "ai_allowed_intents" in data:
            intents = list(data["ai_allowed_intents"] or [])
            filtered = [i for i in intents if i in ALLOWED_INTENTS]
            settings.ai_allowed_intents = filtered
        if "ai_autoreply_enabled" in data:
            settings.ai_autoreply_enabled = bool(data["ai_autoreply_enabled"])
        if "ai_autoreply_hours" in data:
            settings.ai_autoreply_hours = data["ai_autoreply_hours"]
        if "ai_provider_type" in data:
            settings.ai_provider_type = str(data["ai_provider_type"] or "external")

        await self.session.flush()
        return settings

    async def get_effective_prompt(self, clinic_id: UUID) -> str:
        """Compose full system prompt based on global, business and clinic-specific parts."""
        clinic = await self._load_clinic(clinic_id)
        settings = await self.get_or_create_default(clinic_id)

        base_prompt = (
            "Ты ассистент администратора сервиса записи. "
            "Отвечай вежливо, кратко и не давай медицинских рекомендаций. "
            "Не обещай скидок или услуг, которых явно нет в предоставленном контексте. "
        )

        business_prompt_parts: list[str] = []
        if clinic and getattr(clinic, "business_type", None):
            bt = clinic.business_type
            business_prompt_parts.append(f"Тип бизнеса: {bt}. ")
        if clinic and getattr(clinic, "business_type_custom_name", None):
            business_prompt_parts.append(
                f"Бренд/название: {clinic.business_type_custom_name}. "
            )

        custom_prompt = settings.ai_business_prompt or ""

        return base_prompt + "".join(business_prompt_parts) + custom_prompt

    async def _load_clinic(self, clinic_id: UUID) -> Clinic | None:
        result = await self.session.execute(select(Clinic).where(Clinic.id == clinic_id))
        return result.scalars().first()

