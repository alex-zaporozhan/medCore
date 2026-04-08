"""Append-only audit for admin mutations on organization RAG KB (§24.3)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.organization_rag_kb_audit_log import OrganizationRagKbAuditLog


async def log_rag_kb_audit(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_admin_id: uuid.UUID | None,
    action: str,
    document_id: uuid.UUID | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    session.add(
        OrganizationRagKbAuditLog(
            id=uuid.uuid4(),
            organization_id=organization_id,
            actor_admin_id=actor_admin_id,
            action=action,
            document_id=document_id,
            meta=meta,
        )
    )
    await session.flush()
