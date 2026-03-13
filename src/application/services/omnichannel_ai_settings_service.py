"""Service for omnichannel AISettings (BUSINESS → CHANNEL → CHAT)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.omnichannel_ai_settings import AISettings as OmniAISettings


@dataclass
class EffectiveOmniAISettings:
    ai_mode: str
    working_hours_policy: dict | None
    confidence_thresholds: dict | None
    prompt_profile_id: str | None
    kb_profile_id: str | None


class OmnichannelAISettingsService:
    """Utility to compute effective AI settings for omnichannel assistant."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_single(
        self,
        scope: str,
        scope_id: UUID,
    ) -> OmniAISettings | None:
        stmt = select(OmniAISettings).where(
            OmniAISettings.scope == scope,
            OmniAISettings.scope_id == scope_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_or_create_business_settings(
        self,
        business_account_id: UUID,
    ) -> EffectiveOmniAISettings:
        """Return effective BUSINESS-level settings, creating default row if needed."""
        from src.domain.entities.omnichannel_ai_settings import AISettings as OmniAISettings
        from sqlalchemy import select

        result = await self.session.execute(
            select(OmniAISettings).where(
                OmniAISettings.scope == "BUSINESS",
                OmniAISettings.scope_id == business_account_id,
            ).limit(1)
        )
        row: OmniAISettings | None = result.scalar_one_or_none()
        if row is None:
            row = OmniAISettings(
                scope="BUSINESS",
                scope_id=business_account_id,
                ai_mode="DISABLED",
            )
            self.session.add(row)
            await self.session.flush()

        return EffectiveOmniAISettings(
            ai_mode=row.ai_mode or "DISABLED",
            working_hours_policy=row.working_hours_policy,
            confidence_thresholds=row.confidence_thresholds,
            prompt_profile_id=row.prompt_profile_id,
            kb_profile_id=row.kb_profile_id,
        )

    async def upsert_settings(
        self,
        *,
        scope: str,
        scope_id: UUID,
        data: dict,
    ) -> None:
        """Create or update OmniAISettings row for given scope."""
        from src.domain.entities.omnichannel_ai_settings import AISettings as OmniAISettings
        from sqlalchemy import select

        result = await self.session.execute(
            select(OmniAISettings).where(
                OmniAISettings.scope == scope,
                OmniAISettings.scope_id == scope_id,
            ).limit(1)
        )
        row: OmniAISettings | None = result.scalar_one_or_none()
        if row is None:
            row = OmniAISettings(scope=scope, scope_id=scope_id)
            self.session.add(row)

        if "ai_mode" in data and data["ai_mode"] is not None:
            row.ai_mode = str(data["ai_mode"])
        if "working_hours_policy" in data:
            row.working_hours_policy = data["working_hours_policy"]
        if "confidence_thresholds" in data:
            row.confidence_thresholds = data["confidence_thresholds"]
        if "prompt_profile_id" in data:
            row.prompt_profile_id = data["prompt_profile_id"]
        if "kb_profile_id" in data:
            row.kb_profile_id = data["kb_profile_id"]

        await self.session.flush()

    async def get_effective_settings(
        self,
        business_account_id: UUID,
        channel_id: UUID | None,
        chat_id: UUID | None,
    ) -> EffectiveOmniAISettings:
        """Read settings in order BUSINESS → CHANNEL → CHAT and merge."""
        business = await self._get_single("BUSINESS", business_account_id)
        channel = await self._get_single("CHANNEL", channel_id) if channel_id else None
        chat = await self._get_single("CHAT", chat_id) if chat_id else None

        # Default values
        ai_mode = "DISABLED"
        working_hours_policy: dict | None = None
        confidence_thresholds: dict | None = None
        prompt_profile_id: str | None = None
        kb_profile_id: str | None = None

        def _merge_from(src: OmniAISettings | None) -> None:
            nonlocal ai_mode, working_hours_policy, confidence_thresholds, prompt_profile_id, kb_profile_id
            if src is None:
                return
            if src.ai_mode:
                ai_mode = src.ai_mode
            if src.working_hours_policy is not None:
                working_hours_policy = src.working_hours_policy
            if src.confidence_thresholds is not None:
                confidence_thresholds = src.confidence_thresholds
            if src.prompt_profile_id is not None:
                prompt_profile_id = src.prompt_profile_id
            if src.kb_profile_id is not None:
                kb_profile_id = src.kb_profile_id

        # Merge in order: business → channel → chat
        _merge_from(business)
        _merge_from(channel)
        _merge_from(chat)

        return EffectiveOmniAISettings(
            ai_mode=ai_mode,
            working_hours_policy=working_hours_policy,
            confidence_thresholds=confidence_thresholds,
            prompt_profile_id=prompt_profile_id,
            kb_profile_id=kb_profile_id,
        )

