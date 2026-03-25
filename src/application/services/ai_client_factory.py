from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.ai_config_service import AiConfigService, AiProviderConfig
from src.core.ai_sanitizer import AiSanitizer
from src.core.config import settings
from src.infrastructure.external_apis.ai_client import AiClient
from src.infrastructure.external_apis.safe_ai_client import SafeAiClient


@dataclass
class SafeAiClientContext:
    """Metadata about created SafeAiClient, useful for logging/metrics."""

    clinic_id: UUID | None
    provider_type: str
    allow_personal_data: bool


async def build_safe_ai_client(
    clinic_id: UUID | None,
    session: AsyncSession | None = None,
) -> tuple[SafeAiClient, SafeAiClientContext]:
    """
    Centralized helper to build SafeAiClient according to clinic AI policy.

    Behaviour by clinic/session:
    - When clinic_id and session are provided, uses AiConfigService.get_clinic_ai_config
      as the single source of truth for provider_type and allow_personal_data;
    - When clinic_id is None and/or session is None, always builds a strict config
      with provider_type="external" and allow_personal_data=False, regardless of
      ClinicAiSettings or other per-clinic flags. This mode is intended only for
      global / cross-clinic analytics and admin endpoints (admin-ai-status,
      ai_tasks, etc.) where personal data must never be sent.
    """
    if clinic_id is not None and session is not None:
        config = await AiConfigService(session).get_clinic_ai_config(clinic_id)
    else:
        # Safe default for cross-clinic / global analytics: external provider, no personal data.
        config = AiProviderConfig(
            base_url=(settings.ai_provider_base_url or "").rstrip("/"),
            api_key=settings.ai_provider_api_key or "",
            model=settings.ai_provider_model,
            allow_personal_data=False,
            provider_type="external",
        )

    base_client = AiClient(config=config)
    sanitizer = AiSanitizer(allow_personal_data=config.allow_personal_data)
    safe_client = SafeAiClient(base_client, sanitizer=sanitizer)

    ctx = SafeAiClientContext(
        clinic_id=clinic_id,
        provider_type=config.provider_type,
        allow_personal_data=config.allow_personal_data,
    )
    return safe_client, ctx

