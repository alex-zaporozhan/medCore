"""Waitlist lifecycle statuses (BKG_WAITLIST_004)."""

from __future__ import annotations

import logging
from enum import StrEnum

logger = logging.getLogger(__name__)


class WaitlistStatus(StrEnum):
    WAITING = "waiting"
    NOTIFIED = "notified"
    BOOKED = "booked"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


ALL_WAITLIST_STATUSES: frozenset[str] = frozenset(s.value for s in WaitlistStatus)

# Legacy value stored before BOOKED was introduced
LEGACY_CONVERTED_STATUS = "converted"


def normalize_waitlist_status(raw: str | None) -> str:
    """Map legacy DB values to canonical status strings."""
    if raw == LEGACY_CONVERTED_STATUS:
        return WaitlistStatus.BOOKED.value
    if raw in ALL_WAITLIST_STATUSES:
        return raw
    if not raw:
        return WaitlistStatus.WAITING.value
    logger.warning(
        "waitlist_unknown_status_normalized",
        extra={"raw_status": repr(raw)},
    )
    return WaitlistStatus.WAITING.value


def is_terminal_status(status: str) -> bool:
    s = normalize_waitlist_status(status)
    return s in (
        WaitlistStatus.BOOKED.value,
        WaitlistStatus.CANCELLED.value,
        WaitlistStatus.EXPIRED.value,
    )


def can_transition_waitlist(from_status: str, to_status: str) -> bool:
    """Allowed transitions for manual / system updates (excluding idempotent no-ops)."""
    f = normalize_waitlist_status(from_status)
    t = normalize_waitlist_status(to_status)
    if f == t:
        return True
    if f in (WaitlistStatus.BOOKED.value, WaitlistStatus.CANCELLED.value, WaitlistStatus.EXPIRED.value):
        return False
    allowed: dict[str, frozenset[str]] = {
        WaitlistStatus.WAITING.value: frozenset(
            {
                WaitlistStatus.NOTIFIED.value,
                WaitlistStatus.BOOKED.value,
                WaitlistStatus.CANCELLED.value,
                WaitlistStatus.EXPIRED.value,
            }
        ),
        WaitlistStatus.NOTIFIED.value: frozenset(
            {
                WaitlistStatus.WAITING.value,
                WaitlistStatus.BOOKED.value,
                WaitlistStatus.CANCELLED.value,
                WaitlistStatus.EXPIRED.value,
            }
        ),
    }
    return t in allowed.get(f, frozenset())
