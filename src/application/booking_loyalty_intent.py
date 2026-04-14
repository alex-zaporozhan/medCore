"""LEAD B2: persist patient-chosen subscription intent on booking.notes (no migration).

Machine-readable suffix is stripped from ``BookingRead`` for API consumers.
"""

from __future__ import annotations

import re
from uuid import UUID

_INTENT_LINE = re.compile(r"\n?\[loyalty_booking_intent\]([^\n]*)$")
_INTENT_SUB = re.compile(r"(?:^|&)use_subscription_id=([0-9a-fA-F-]{36})(?:&|$)")


def append_loyalty_intent_to_notes(
    *,
    user_notes: str | None,
    use_subscription_id: UUID | None,
) -> str | None:
    """Return notes with loyalty intent line appended (within practical length)."""
    base = (user_notes or "").rstrip()
    if use_subscription_id is None:
        return base or None
    suffix = f"[loyalty_booking_intent]use_subscription_id={use_subscription_id}"
    combined = f"{base}\n{suffix}".strip() if base else suffix
    if len(combined) > 2000:
        raise ValueError("notes_too_long_with_loyalty_intent")
    return combined


def parse_use_subscription_id_from_notes(notes: str | None) -> UUID | None:
    """Extract subscription id encoded by ``append_loyalty_intent_to_notes``."""
    if not notes:
        return None
    m = _INTENT_LINE.search(notes)
    if not m:
        return None
    body = m.group(1) or ""
    sm = _INTENT_SUB.search(body)
    if not sm:
        return None
    try:
        return UUID(sm.group(1))
    except ValueError:
        return None


def strip_loyalty_intent_from_notes(notes: str | None) -> str | None:
    """Remove machine intent line for patient/admin reads."""
    if not notes:
        return None
    out = _INTENT_LINE.sub("", notes).strip()
    return out or None
