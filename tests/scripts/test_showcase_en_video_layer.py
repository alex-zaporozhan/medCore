"""Pure helpers for the English showcase video layer (no DB)."""

from src.scripts.showcase_en_video_layer import (
    CAL_TITLE_RU_EN,
    SHOWCASE_STAFF_CAL_PREFIX,
    SHOWCASE_TASK_PREFIX,
    STAFF_CHAT_EXTRA_BODIES,
    TASK_TITLE_RU_EN,
    doctor_short_label,
    english_prefix_fallback,
    strip_staff_demo_mark,
    _turns_for_script,
)
from src.scripts.showcase_en_catalog import PATIENT_NAMES


def _has_cyrillic(text: str) -> bool:
    return any("а" <= ch.lower() <= "я" or ch in "ёЁ" for ch in text)


def test_task_and_calendar_maps_are_english() -> None:
    assert TASK_TITLE_RU_EN
    assert CAL_TITLE_RU_EN
    for src, dst in {**TASK_TITLE_RU_EN, **CAL_TITLE_RU_EN}.items():
        assert _has_cyrillic(src)
        assert not _has_cyrillic(dst)
        assert dst.startswith("Demo ")


def test_prefix_fallback_unknown_legacy_title() -> None:
    legacy = "Демо Kanban: Something new from an older seed"
    got = english_prefix_fallback(legacy, "Демо Kanban:", SHOWCASE_TASK_PREFIX, TASK_TITLE_RU_EN)
    assert got == f"{SHOWCASE_TASK_PREFIX} Something new from an older seed"


def test_calendar_prefix_exact_and_fallback() -> None:
    src = next(iter(CAL_TITLE_RU_EN))
    assert english_prefix_fallback(src, "Демо календарь:", SHOWCASE_STAFF_CAL_PREFIX, CAL_TITLE_RU_EN) == CAL_TITLE_RU_EN[src]
    got = english_prefix_fallback(
        "Демо календарь: Mystery huddle",
        "Демо календарь:",
        SHOWCASE_STAFF_CAL_PREFIX,
        CAL_TITLE_RU_EN,
    )
    assert got == f"{SHOWCASE_STAFF_CAL_PREFIX} Mystery huddle"


def test_strip_staff_demo_mark() -> None:
    assert strip_staff_demo_mark("[demo] Noted. I’ll text waitlist patients after lunch.") == (
        "Noted. I’ll text waitlist patients after lunch."
    )
    assert strip_staff_demo_mark(STAFF_CHAT_EXTRA_BODIES[0]) == STAFF_CHAT_EXTRA_BODIES[0]


def test_staff_extra_bodies_english_and_unique() -> None:
    assert len(STAFF_CHAT_EXTRA_BODIES) == 6
    assert len(set(STAFF_CHAT_EXTRA_BODIES)) == 6
    for body in STAFF_CHAT_EXTRA_BODIES:
        assert not _has_cyrillic(body)
        assert not body.startswith("[demo]")


def test_doctor_short_label() -> None:
    assert doctor_short_label("Marina Volkova, DDS") == "Dr. Volkova"


def test_turns_use_booking_line_when_present() -> None:
    line = "Friday 16:30 — Professional hygiene, Dr. Volkova"
    turns = _turns_for_script("TELEGRAM", "Anna Smirnova", line)
    assert len(turns) == 4
    assert all(t[0] in ("in", "out") for t in turns)
    assert line in turns[0][1]
    assert not any(_has_cyrillic(t[1]) for t in turns)


def test_turns_without_booking_do_not_claim_a_locked_slot() -> None:
    turns = _turns_for_script("TELEGRAM", "Anna Smirnova", None)
    blob = " ".join(t[1] for t in turns)
    assert "I’ll confirm in this thread" in blob
    assert "Kept as booked" not in blob


def test_video_patients_are_in_catalog() -> None:
    for name in ("Anna Smirnova", "Ivan Kozlov", "Maria Sokolova"):
        assert name in PATIENT_NAMES
