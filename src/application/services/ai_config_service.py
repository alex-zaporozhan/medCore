from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.domain.entities.clinic_ai_settings import ClinicAiSettings


@dataclass
class AiProviderConfig:
    base_url: str
    api_key: str
    model: str
    allow_personal_data: bool
    provider_type: str  # "external" | "ru_compliant" | "on_premise"


class AiConfigService:
    """Centralized provider of AI configuration per clinic."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def get_clinic_ai_config(self, clinic_id: UUID) -> AiProviderConfig:
        """
        Build effective AI provider config for a clinic.

        - base URL / api_key / model come from global Settings;
        - provider_type and allow_personal_data derived from ClinicAiSettings if available.
        """
        base_url = (settings.ai_provider_base_url or "").rstrip("/")
        api_key = settings.ai_provider_api_key or ""
        model = settings.ai_provider_model

        allow_personal_data = False
        provider_type = "external"

        if self._session is not None:
            from sqlalchemy import select

            result = await self._session.execute(
                select(ClinicAiSettings).where(ClinicAiSettings.clinic_id == clinic_id).limit(1)
            )
            row = result.scalars().first()
            if row is not None:
                provider_type = row.ai_provider_type or "external"
                # Simple policy: allow personal data only if ai_enabled and provider explicitly marked as compliant/on-prem
                allow_personal_data = bool(row.ai_enabled and provider_type in {"ru_compliant", "on_premise"})

        return AiProviderConfig(
            base_url=base_url,
            api_key=api_key,
            model=model,
            allow_personal_data=allow_personal_data,
            provider_type=provider_type,
        )
