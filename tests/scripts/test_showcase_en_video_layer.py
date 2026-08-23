"""Pure helpers for the English showcase video layer (no DB)."""

from src.scripts.showcase_en_video_layer import (
    CAL_TITLE_RU_EN,
    SHOWCASE_STAFF_CAL_PREFIX,
    SHOWCASE_TASK_PREFIX,
    STAFF_CHAT_EXTRA_BODIES,
    STAFF_GROUP_THREADS,
    TASK_TITLE_RU_EN,
    doctor_short_label,
    english_prefix_fallback,
    strip_staff_demo_mark,
    video_omni_from_id,
    _turns_for_script,
)
from src.scripts.showcase_en_catalog import PATIENT_NAMES


def _has_cyrillic(text: str) -> bool:
    return any("а" <= ch.lower() <= "я" or ch in "ёЁ" for ch in text)


def test_extras_title_prefixes_stay_aligned_with_video_layer() -> None:
    from src.scripts import showcase_saas_extras as extras
    from src.scripts.showcase_en_video_layer import (
        CAL_PREFIX_LEGACY,
        FEED_PREFIX_LEGACY,
        PROMO_BODY_CANONICAL,
        PROMO_PREFIX_LEGACY,
        PROMO_TITLE_PREFIX,
        SHOWCASE_STAFF_CAL_PREFIX,
        SHOWCASE_TASK_PREFIX,
        STAFF_FEED_TITLE_PREFIX,
        STAFF_FEED_TITLE_WEEK,
        STAFF_GENERAL_OPENERS,
        TASK_PREFIX_LEGACY,
        TASK_TITLES_CANONICAL,
    )

    assert extras.SHOWCASE_TASK_PREFIX == TASK_PREFIX_LEGACY
    assert extras.SHOWCASE_STAFF_CAL_PREFIX == CAL_PREFIX_LEGACY
    assert extras.STAFF_FEED_TITLE_PREFIX == FEED_PREFIX_LEGACY
    assert extras.PROMO_TITLE_PREFIX == PROMO_PREFIX_LEGACY
    assert extras.SHOWCASE_TASK_PREFIX_EN == SHOWCASE_TASK_PREFIX
    assert extras.SHOWCASE_STAFF_CAL_PREFIX_EN == SHOWCASE_STAFF_CAL_PREFIX
    assert extras.STAFF_FEED_TITLE_PREFIX_EN == STAFF_FEED_TITLE_PREFIX
    assert extras.PROMO_TITLE_PREFIX_EN == PROMO_TITLE_PREFIX
    assert STAFF_FEED_TITLE_PREFIX + " Week plan" in extras.STAFF_FEED_POST1_TITLES
    assert STAFF_FEED_TITLE_WEEK in extras.STAFF_FEED_POST1_TITLES
    assert extras.TASK_TITLES_CANONICAL == TASK_TITLES_CANONICAL
    assert extras.PROMO_BODY_CANONICAL == PROMO_BODY_CANONICAL
    assert extras.STAFF_GENERAL_OPENERS == STAFF_GENERAL_OPENERS


def test_task_and_calendar_maps_are_english() -> None:
    assert TASK_TITLE_RU_EN
    assert CAL_TITLE_RU_EN
    for src, dst in {**TASK_TITLE_RU_EN, **CAL_TITLE_RU_EN}.items():
        assert not _has_cyrillic(dst), dst
        assert not dst.startswith("Demo "), dst
        if _has_cyrillic(src):
            assert dst != src


def test_prefix_fallback_unknown_legacy_title() -> None:
    legacy = "Демо Kanban: Something new from an older seed"
    got = english_prefix_fallback(legacy, "Демо Kanban:", SHOWCASE_TASK_PREFIX, TASK_TITLE_RU_EN)
    assert got == "Something new from an older seed"


def test_calendar_prefix_exact_and_fallback() -> None:
    src = next(iter(CAL_TITLE_RU_EN))
    assert english_prefix_fallback(src, "Демо календарь:", SHOWCASE_STAFF_CAL_PREFIX, CAL_TITLE_RU_EN) == CAL_TITLE_RU_EN[src]
    got = english_prefix_fallback(
        "Демо календарь: Mystery huddle",
        "Демо календарь:",
        SHOWCASE_STAFF_CAL_PREFIX,
        CAL_TITLE_RU_EN,
    )
    assert got == "Mystery huddle"


def test_strip_staff_demo_mark() -> None:
    assert strip_staff_demo_mark("[demo] Noted. I’ll text waitlist patients after lunch.") == (
        "Noted. I’ll text waitlist patients after lunch."
    )
    assert strip_staff_demo_mark(STAFF_CHAT_EXTRA_BODIES[0]) == STAFF_CHAT_EXTRA_BODIES[0]


def test_staff_line_rewrites_cover_legacy_demo_copy() -> None:
    from src.scripts.showcase_en_video_layer import STAFF_CHAT_LINE_REWRITES

    assert STAFF_CHAT_LINE_REWRITES["Ivan has the disk. Anna said she will bring it."].startswith("Noah")
    for src, dst in STAFF_CHAT_LINE_REWRITES.items():
        assert "Demo path" not in dst
        assert "GitHub demo" not in dst
        assert not dst.startswith("Demo ")
    assert len(STAFF_CHAT_EXTRA_BODIES) == 6
    assert len(set(STAFF_CHAT_EXTRA_BODIES)) == 6
    for body in STAFF_CHAT_EXTRA_BODIES:
        assert not _has_cyrillic(body)
        assert not body.startswith("[demo]")


def test_doctor_short_label() -> None:
    assert doctor_short_label("Paul Brennan, DDS") == "Dr. Brennan"
    assert doctor_short_label("Marina Volkova, DDS") == "Dr. Volkova"


def test_staff_group_threads_five_by_ten_english() -> None:
    assert len(STAFF_GROUP_THREADS) == 5
    titles = [title for title, _bodies in STAFF_GROUP_THREADS]
    assert len(set(titles)) == 5
    for title, bodies in STAFF_GROUP_THREADS:
        assert not _has_cyrillic(title)
        assert len(bodies) == 10
        assert len(set(bodies)) == 10
        assert "Demo" not in title
        for body in bodies:
            assert not _has_cyrillic(body)
            assert "Demo" not in body
            assert ".env" not in body
            assert "Twilio" not in body
            assert "relabelled" not in body.lower()


def test_turns_use_booking_line_when_present() -> None:
    line = "Friday 16:30 — Professional hygiene, Dr. Brennan"
    turns = _turns_for_script("TELEGRAM", "Mary Collins", line)
    assert len(turns) == 10
    assert all(t[0] in ("in", "out") for t in turns)
    assert line in turns[0][1]
    assert not any(_has_cyrillic(t[1]) for t in turns)


def test_turns_without_booking_do_not_claim_a_locked_slot() -> None:
    turns = _turns_for_script("TELEGRAM", "Mary Collins", None)
    blob = " ".join(t[1] for t in turns)
    assert "I’ll confirm in this thread" in blob
    assert "Kept as booked" not in blob


def test_turns_match_us_primary_contour() -> None:
    blob = " ".join(
        t[1]
        for kind in ("TELEGRAM", "WHATSAPP", "WEBCHAT")
        for t in _turns_for_script(kind, "Mary Collins", None)
        + _turns_for_script(kind, "Mary Collins", "Friday 16:30 — Professional hygiene, Dr. Brennan")
    )
    assert "Krasnaya" not in blob
    assert "Larina" not in blob
    assert "Dr. Carter" in blob


def test_video_omni_from_id_is_stable_not_patient_phone() -> None:
    from uuid import UUID

    cid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    wa = video_omni_from_id("WHATSAPP", "kazan", cid)
    assert wa.startswith("+7999")
    assert video_omni_from_id("TELEGRAM", "kazan", cid) == "tg_video_kazan_anna"
    assert video_omni_from_id("WEBCHAT", "kazan", cid) == "web_video_kazan_maria"


def test_video_patients_are_in_catalog() -> None:
    assert PATIENT_NAMES
    for name in PATIENT_NAMES:
        assert name.strip()
        assert not _has_cyrillic(name)
    for name in ("Mary Collins", "Noah Bennett", "Olivia Chen"):
        assert name in PATIENT_NAMES
