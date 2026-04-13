"""Doctor calendar slot occupancy: shared by ORM index predicate and booking service.

Partial unique index on ``bookings`` (see Alembic) must use the same status literals
as ``status_releases_doctor_slot`` so application checks and DB constraints agree.

Must not import ``src.domain.entities.booking`` (that module imports this file for the
index predicate → circular import during Alembic metadata load).
"""

from __future__ import annotations

import hashlib
from datetime import date, time
from typing import Any
from uuid import UUID


def _status_str(status: Any) -> str:
    v = getattr(status, "value", status)
    return str(v)


# Statuses that do NOT reserve the (doctor_id, date, time) slot for uniqueness purposes.
BOOKING_STATUSES_RELEASE_DOCTOR_SLOT: frozenset[str] = frozenset(
    {
        "cancelled",
        "canceled_by_patient",
        "canceled_by_clinic",
        # Slot may be offered again after visit outcome (P1-1 backlog — must match partial unique index).
        "no_show",
        "completed",
    }
)


def status_releases_doctor_slot(status: Any) -> bool:
    """True if another booking may use the same doctor/date/time (cancel family)."""
    return _status_str(status) in BOOKING_STATUSES_RELEASE_DOCTOR_SLOT


def partial_unique_index_status_predicate_sql() -> str:
    """SQL fragment for PostgreSQL partial unique index (keep in sync with *_RELEASE_*)."""
    literals = ", ".join(f"'{s}'" for s in sorted(BOOKING_STATUSES_RELEASE_DOCTOR_SLOT))
    return f"deleted_at IS NULL AND status NOT IN ({literals})"


def _digest_to_int32_pair(digest: bytes) -> tuple[int, int]:
    def _i32(chunk: bytes) -> int:
        x = int.from_bytes(chunk, "big", signed=False) & 0xFFFFFFFF
        if x >= 2**31:
            x -= 2**32
        return int(x)

    return _i32(digest[0:4]), _i32(digest[4:8])


def doctor_slot_advisory_lock_int32_pair(
    doctor_id: UUID,
    appointment_date: date,
    appointment_time: time,
) -> tuple[int, int]:
    """Two int32 keys for ``pg_advisory_xact_lock`` (P1-1: serialize mutations per doctor slot)."""
    t = appointment_time.replace(microsecond=0)
    key = f"{doctor_id}:{appointment_date.isoformat()}:{t.isoformat(timespec='seconds')}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return _digest_to_int32_pair(digest)


# Substrings on IntegrityError / DBAPI message for doctor-slot uniqueness (legacy + partial index).
BOOKING_DOCTOR_SLOT_UNIQUE_NAMES: frozenset[str] = frozenset(
    {
        "ux_bookings_doctor_slot_active",
        "ux_bookings_doctor_slot",
    },
)


def is_booking_doctor_slot_unique_violation(exc: BaseException) -> bool:
    """True if this looks like a conflict on the doctor/date/time slot unique index."""
    msg = str(getattr(exc, "orig", exc) or exc).lower()
    return any(name in msg for name in BOOKING_DOCTOR_SLOT_UNIQUE_NAMES)
