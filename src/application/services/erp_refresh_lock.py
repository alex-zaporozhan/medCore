"""PostgreSQL advisory locks for per-clinic ERP vitrine refresh (QA_ARCH A11)."""

from __future__ import annotations

from uuid import UUID
from zlib import crc32

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Fixed namespace int4 for pg_advisory_xact_lock(int, int); second key from clinic_id.
_ERP_REFRESH_LOCK_NS = 8_842_001


async def acquire_erp_refresh_lock(session: AsyncSession, clinic_id: UUID) -> None:
    """Serialize manual/event refresh for one clinic (transaction-scoped)."""
    k = crc32(str(clinic_id).encode("utf-8")) & 0x7FFFFFFF
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:a, :b)"),
        {"a": _ERP_REFRESH_LOCK_NS, "b": k},
    )
