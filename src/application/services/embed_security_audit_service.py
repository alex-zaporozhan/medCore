"""DB audit for embed key lifecycle and webhook secret (Phase 1e-F4)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.organization_embed_audit_log import OrganizationEmbedAuditLog


async def log_organization_embed_audit(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_admin_id: uuid.UUID | None,
    action: str,
    embed_api_key_id: uuid.UUID | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    session.add(
        OrganizationEmbedAuditLog(
            id=uuid.uuid4(),
            organization_id=organization_id,
            actor_admin_id=actor_admin_id,
            action=action,
            embed_api_key_id=embed_api_key_id,
            meta=meta,
        )
    )
    await session.flush()
