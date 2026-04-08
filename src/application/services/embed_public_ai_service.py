"""Public embed assistant: strict sanitizer + tokenizer budget (§24.2)."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.ai_config_service import AiConfigService, AiProviderConfig
from src.core.ai_sanitizer import AiSanitizer
from src.core.ai_token_estimate import estimate_llm_tokens
from src.core.config import settings
from src.domain.entities.clinic import Clinic
from src.infrastructure.external_apis.ai_client import AiClient, AiClientError
from src.infrastructure.external_apis.safe_ai_client import SafeAiClient

logger = logging.getLogger(__name__)


async def _first_clinic_id_for_organization(session: AsyncSession, organization_id: UUID) -> UUID | None:
    res = await session.execute(
        select(Clinic.id).where(Clinic.organization_id == organization_id).limit(1)
    )
    row = res.first()
    return row[0] if row else None


async def run_embed_public_assistant_turn(
    session: AsyncSession,
    organization_id: UUID,
    user_message: str,
) -> dict:
    """
    Always mask PII for the public embed contour; enforce tokenizer budget; optional LLM if configured.
    Returns dict: reply, mode, tokens_estimated_input, provider_called.
    """
    raw = (user_message or "").strip()
    if not raw:
        return {
            "reply": "",
            "mode": "empty",
            "tokens_estimated_input": 0,
            "provider_called": False,
        }

    strict = AiSanitizer(allow_personal_data=False)
    sanitized = strict.sanitize(raw).sanitized
    tokens_in = estimate_llm_tokens(sanitized)
    max_in = settings.embed_ai_max_input_tokens
    if tokens_in > max_in:
        return {
            "reply": "",
            "mode": "input_too_long",
            "tokens_estimated_input": tokens_in,
            "provider_called": False,
            "max_input_tokens": max_in,
        }

    clinic_id = await _first_clinic_id_for_organization(session, organization_id)
    config: AiProviderConfig
    if clinic_id is not None:
        config = await AiConfigService(session).get_clinic_ai_config(clinic_id)
    else:
        config = AiProviderConfig(
            base_url=(settings.ai_provider_base_url or "").rstrip("/"),
            api_key=settings.ai_provider_api_key or "",
            model=settings.ai_provider_model,
            allow_personal_data=False,
            provider_type="external",
        )

    base = AiClient(config=config)
    safe = SafeAiClient(base, sanitizer=strict)
    if not base.is_configured():
        return {
            "reply": sanitized[:2000],
            "mode": "echo_no_provider",
            "tokens_estimated_input": tokens_in,
            "provider_called": False,
        }

    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": "You are a concise assistant for a clinic embed widget. No personal data; reply in the user's language.",
            },
            {"role": "user", "content": sanitized},
        ],
        "max_tokens": min(settings.embed_ai_max_output_tokens, 1024),
    }
    try:
        data = await safe.complete(payload)
    except AiClientError as e:
        logger.warning("embed_public_ai_provider_error", extra={"error": str(e)})
        return {
            "reply": sanitized[:2000],
            "mode": "provider_error",
            "tokens_estimated_input": tokens_in,
            "provider_called": True,
        }

    choices = data.get("choices") if isinstance(data, dict) else None
    text = ""
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(msg, dict):
            text = (msg.get("content") or "").strip()
    tokens_out = estimate_llm_tokens(text)
    if tokens_out > settings.embed_ai_max_output_tokens:
        text = text[: settings.embed_ai_max_output_tokens * 4]

    return {
        "reply": text or sanitized[:500],
        "mode": "llm",
        "tokens_estimated_input": tokens_in,
        "provider_called": True,
    }
