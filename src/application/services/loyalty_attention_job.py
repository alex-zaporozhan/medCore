"""Batch job helpers for creating Tasks from loyalty campaign rules (LOY_AI_014)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.loyalty_campaign_engine import run_campaigns_for_clinic


async def run_loyalty_attention_job(session: AsyncSession, clinic_id: UUID) -> int:
    """Run :func:`run_campaigns_for_clinic` and return total tasks created.

    Campaign types: expiring packages, high balance + low activity, reengagement.
    """
    r = await run_campaigns_for_clinic(session, clinic_id)
    return (
        r.created_expiring + r.created_high_balance + r.created_reengagement
    )

