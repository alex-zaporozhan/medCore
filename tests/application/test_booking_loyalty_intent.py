"""Unit tests for LEAD B2: loyalty intent encoding on booking notes."""

from uuid import uuid4

import pytest

from src.application.booking_loyalty_intent import (
    append_loyalty_intent_to_notes,
    parse_use_subscription_id_from_notes,
    strip_loyalty_intent_from_notes,
)


def test_append_and_parse_roundtrip() -> None:
    sid = uuid4()
    base = "Please morning slot"
    notes = append_loyalty_intent_to_notes(user_notes=base, use_subscription_id=sid)
    assert notes is not None
    assert base in notes
    assert parse_use_subscription_id_from_notes(notes) == sid
    stripped = strip_loyalty_intent_from_notes(notes)
    assert stripped == base


def test_parse_none_without_suffix() -> None:
    assert parse_use_subscription_id_from_notes("plain notes") is None
    assert strip_loyalty_intent_from_notes("plain") == "plain"


def test_append_without_user_notes() -> None:
    sid = uuid4()
    notes = append_loyalty_intent_to_notes(user_notes=None, use_subscription_id=sid)
    assert notes is not None
    assert parse_use_subscription_id_from_notes(notes) == sid


def test_strip_removes_only_intent_line() -> None:
    sid = uuid4()
    raw = f"line1\nline2\n[loyalty_booking_intent]use_subscription_id={sid}"
    assert strip_loyalty_intent_from_notes(raw) == "line1\nline2"


def test_append_raises_when_too_long() -> None:
    sid = uuid4()
    long_base = "x" * 1990
    with pytest.raises(ValueError, match="notes_too_long"):
        append_loyalty_intent_to_notes(user_notes=long_base, use_subscription_id=sid)


def test_parse_invalid_uuid_in_suffix() -> None:
    notes = "[loyalty_booking_intent]use_subscription_id=not-a-uuid"
    # Line must be at end for regex
    text = f"hello\n{notes}"
    assert parse_use_subscription_id_from_notes(text) is None


def test_append_none_subscription_returns_base() -> None:
    assert append_loyalty_intent_to_notes(user_notes="  hi  ", use_subscription_id=None) == "  hi"
