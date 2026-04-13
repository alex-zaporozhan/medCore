"""PostgreSQL transaction-scoped advisory lock for a single doctor calendar slot (P1-1)."""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.booking_slot_policy import doctor_slot_advisory_lock_int32_pair


async def acquire_doctor_slot_xact_advisory_lock(
    session: AsyncSession,
    *,
    doctor_id: UUID,
    appointment_date: date,
    appointment_time: time,
) -> None:
    """Block until this transaction holds the advisory lock for (doctor, date, time)."""
    k1, k2 = doctor_slot_advisory_lock_int32_pair(
        doctor_id, appointment_date, appointment_time
    )
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:k1, :k2)"),
        {"k1": k1, "k2": k2},
    )
