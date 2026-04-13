"""P1-1: partial unique predicate SQL stays aligned with release-status set."""

from src.domain.booking_slot_policy import (
    BOOKING_STATUSES_RELEASE_DOCTOR_SLOT,
    partial_unique_index_status_predicate_sql,
)


def test_partial_unique_predicate_contains_all_release_statuses() -> None:
    sql = partial_unique_index_status_predicate_sql()
    for s in sorted(BOOKING_STATUSES_RELEASE_DOCTOR_SLOT):
        assert f"'{s}'" in sql


def test_release_set_includes_outcome_statuses() -> None:
    assert "completed" in BOOKING_STATUSES_RELEASE_DOCTOR_SLOT
    assert "no_show" in BOOKING_STATUSES_RELEASE_DOCTOR_SLOT
