"""Org-level access checks for platform SaaS billing revocation (ADR-012)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.platform_signup_intent import PlatformSignupIntent


async def organization_has_platform_billing_revoked(
    session: AsyncSession,
    organization_id: UUID,
) -> bool:
    """True if this org has a platform signup intent suspended after billing revocation."""
    r = await session.execute(
        select(PlatformSignupIntent.id).where(
            PlatformSignupIntent.organization_id == organization_id,
            PlatformSignupIntent.status == "suspended",
            PlatformSignupIntent.billing_revoked_at.isnot(None),
        ).limit(1)
    )
    return r.scalar_one_or_none() is not None
