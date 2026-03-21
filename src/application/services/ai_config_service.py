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
    """
    Centralized provider of AI configuration per clinic.

    Policy (BUSINESS_LOGIC_V2) for personal data and provider type:

    - When provider_type == "external": allow_personal_data is always False;
    - When provider_type in {"ru_compliant", "on_premise"} and ai_enabled == True:
      allow_personal_data is True;
    - In all other cases (including ai_enabled == False or unknown provider_type):
      allow_personal_data is False.

    This method is the single source of truth for deriving allow_personal_data
    from ClinicAiSettings and global settings.
    """

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

        # Default: strict external provider with no personal data
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
                # Policy:
                # - external -> allow_personal_data=False always;
                # - ru_compliant/on_premise with ai_enabled=True -> allow_personal_data=True;
                # - all other combinations -> allow_personal_data=False.
                allow_personal_data = bool(
                    row.ai_enabled and provider_type in {"ru_compliant", "on_premise"}
                )

        return AiProviderConfig(
            base_url=base_url,
            api_key=api_key,
            model=model,
            allow_personal_data=allow_personal_data,
            provider_type=provider_type,
        )
