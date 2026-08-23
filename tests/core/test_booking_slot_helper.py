"""Guarantees for tests.booking_slot (session-shared doctor slot uniqueness)."""

from datetime import date, timedelta

from tests.booking_slot import unique_booking_slot, unique_clock_time


def test_unique_booking_slot_no_collision_for_thousands_of_calls() -> None:
    base = date(2026, 1, 1)
    seen: set[tuple[date, object]] = set()
    for _ in range(5_000):
        slot = unique_booking_slot(base, hour=11)
        assert slot not in seen
        seen.add(slot)
        assert slot[0] >= base + timedelta(days=40)


def test_unique_clock_time_distinct_on_same_hour() -> None:
    times = [unique_clock_time(hour=10) for _ in range(500)]
    assert len(set(times)) == 500
    assert all(t.hour == 10 for t in times)
