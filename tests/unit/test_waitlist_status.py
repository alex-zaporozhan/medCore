"""Domain rules for waitlist statuses."""

from src.domain.entities.waitlist_status import (
    WaitlistStatus,
    can_transition_waitlist,
    normalize_waitlist_status,
)


def test_normalize_legacy_converted():
    assert normalize_waitlist_status("converted") == WaitlistStatus.BOOKED.value


def test_normalize_unknown_falls_back():
    assert normalize_waitlist_status("garbage") == WaitlistStatus.WAITING.value


def test_transitions_waiting():
    assert can_transition_waitlist("waiting", "notified")
    assert can_transition_waitlist("waiting", "booked")
    assert can_transition_waitlist("waiting", "cancelled")


def test_transitions_terminal_blocked():
    assert can_transition_waitlist("booked", "waiting") is False
    assert can_transition_waitlist("cancelled", "waiting") is False
