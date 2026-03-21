"""Unit tests for booking domain event dedup ids (no DB)."""

from uuid import UUID

from src.application.events.standard_events import (
    BOOKING_CANCELLED,
    BOOKING_CREATED,
    booking_event_dedup_id,
)


def test_booking_event_dedup_id_stable_per_booking_and_event_type():
    bid = UUID("11111111-1111-1111-1111-111111111111")
    a = booking_event_dedup_id(BOOKING_CREATED, bid)
    b = booking_event_dedup_id(BOOKING_CREATED, bid)
    c = booking_event_dedup_id(BOOKING_CANCELLED, bid)
    assert a == b
    assert a != c


def test_booking_event_dedup_id_differs_by_booking():
    b1 = UUID("22222222-2222-2222-2222-222222222222")
    b2 = UUID("33333333-3333-3333-3333-333333333333")
    assert booking_event_dedup_id(BOOKING_CREATED, b1) != booking_event_dedup_id(BOOKING_CREATED, b2)
