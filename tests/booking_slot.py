"""Unique Booking (date, time) under ux_bookings_doctor_slot_active.

Session-scoped seed_data truncates once per pytest process. Inserts with occupying
statuses (pending / confirmed / awaiting_payment / …) share one doctor and collide
if they reuse clock time or a hardcoded slot. Cancelled / no_show / completed do
not occupy the partial unique index (see booking_slot_policy).

Uniqueness is a process-wide counter, not uuid modulo (birthday collisions).
"""

from __future__ import annotations

from datetime import date, time, timedelta
from itertools import count

_seq = count(1)


def unique_clock_time(*, hour: int | None = None) -> time:
    """Time only; keep a caller-chosen calendar day (campaign 'recent visit', ERP day)."""
    n = next(_seq)
    h = (hour % 24) if hour is not None else 6 + (n % 12)
    us = n % 1_000_000
    carry = n // 1_000_000
    sec = carry % 60
    minute = (carry // 60) % 60
    return time(h, minute, sec, us)


def unique_booking_slot(base_day: date | None = None, *, hour: int | None = 6) -> tuple[date, time]:
    """Far-future occupying slot for the session-scoped seed doctor."""
    n = next(_seq)
    origin = base_day if base_day is not None else date.today()
    if hour is None:
        day = origin + timedelta(days=40 + n // 86_400)
        rem = n % 86_400
        return day, time(rem // 3600, (rem % 3600) // 60, rem % 60)
    day = origin + timedelta(days=40 + n // 3600)
    bucket = n % 3600
    return day, time(hour % 24, bucket // 60, bucket % 60)
