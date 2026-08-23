"""Pure helpers for the English ±14-day showcase window (no DB)."""

from datetime import date, time, timedelta
from uuid import UUID

from src.scripts.showcase_en_demo_window import (
    HUDDLE_BODIES,
    HUDDLE_TITLE,
    HUDDLE_TITLE_LEGACY,
    OMNI_SCRIPTS,
    TASK_COMMENTS,
    TASK_PREFIX_LEGACY,
    WINDOW_MEETINGS,
    WINDOW_TASKS,
    clinician_emails,
    meeting_anchor_days,
    window_booking_status,
    window_bounds,
)
from src.scripts.showcase_en_catalog import ORG_SPECS


def _has_cyrillic(text: str) -> bool:
    return any("а" <= ch.lower() <= "я" or ch in "ёЁ" for ch in text)


def test_window_is_fourteen_days_each_way() -> None:
    today = date(2026, 8, 21)
    start, end = window_bounds(today)
    assert start == today - timedelta(days=14)
    assert end == today + timedelta(days=14)


def test_window_copy_is_english() -> None:
    blobs = [
        HUDDLE_TITLE,
        *WINDOW_MEETINGS,
        *TASK_COMMENTS,
        *HUDDLE_BODIES,
    ]
    for suffix, *_rest in WINDOW_TASKS:
        blobs.append(suffix)
    for _provider, name, kind, turns in OMNI_SCRIPTS:
        blobs.append(name)
        blobs.append(kind)
        for _d, text in turns:
            blobs.append(text)
    for text in blobs:
        assert not _has_cyrillic(text), text
    assert HUDDLE_TITLE == "Two-week ops"
    assert HUDDLE_TITLE_LEGACY.startswith("Demo huddle:")
    assert TASK_PREFIX_LEGACY.startswith("Demo window:")
    for suffix, *_rest in WINDOW_TASKS:
        assert "Demo" not in suffix
    for title in WINDOW_MEETINGS:
        assert "Demo" not in title
    assert "Demo" not in HUDDLE_TITLE
    for body in HUDDLE_BODIES:
        if "@showcase-mt.demo" in body:
            continue
        assert "Demo" not in body, body
    for _provider, name, _kind, turns in OMNI_SCRIPTS:
        assert "Demo" not in name
        for _d, text in turns:
            assert "Demo" not in text
    assert {row[1] for row in OMNI_SCRIPTS} == {"Liam Brooks", "Sophie Harper", "Ethan Baker"}


def test_kanban_covers_board_statuses() -> None:
    statuses = {row[1] for row in WINDOW_TASKS}
    assert statuses >= {"open", "in_progress", "on_hold", "review", "done", "cancelled"}
    streams = {row[3] for row in WINDOW_TASKS}
    assert streams == {"general", "sales"}


def test_status_mix_is_stable_and_varied() -> None:
    clinic = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    doctor = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    today = date(2026, 8, 21)
    past = window_booking_status(today - timedelta(days=3), today, clinic, doctor, time(10, 0))
    future = window_booking_status(today + timedelta(days=3), today, clinic, doctor, time(10, 0))
    nine = window_booking_status(today, today, clinic, doctor, time(9, 0))
    ten = window_booking_status(today, today, clinic, doctor, time(10, 0))
    assert past in {"completed", "no_show", "canceled_by_patient"}
    assert future in {"pending", "confirmed"}
    assert nine == "in_progress"
    assert ten in {"registered", "confirmed"}
    assert window_booking_status(today - timedelta(days=3), today, clinic, doctor, time(10, 0)) == past


def test_each_org_has_doctor_login() -> None:
    rows = clinician_emails()
    assert len(rows) == len(ORG_SPECS)
    keys = {r[0] for r in rows}
    assert keys == {str(s["key"]) for s in ORG_SPECS}
    for _key, email, name in rows:
        assert email.startswith("doctor1.")
        assert email.endswith("@showcase-mt.demo")
        assert "Hannah Cole" in name
        assert not _has_cyrillic(email)
        assert not _has_cyrillic(name)


def test_meetings_straddle_today() -> None:
    today = date(2026, 8, 21)
    days = meeting_anchor_days(today, n=10)
    assert len(days) == 10
    assert all(d.weekday() < 5 for d in days)
    assert any(d < today for d in days)
    assert any(d >= today for d in days)
    start, end = window_bounds(today)
    assert min(days) >= start
    assert max(days) <= end
