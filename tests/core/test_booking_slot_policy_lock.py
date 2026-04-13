"""P1-1: doctor slot advisory lock keys and unique-violation message sniffing."""

from datetime import date, time
from uuid import UUID

import pytest

from src.domain.booking_slot_policy import (
    BOOKING_DOCTOR_SLOT_UNIQUE_NAMES,
    doctor_slot_advisory_lock_int32_pair,
    is_booking_doctor_slot_unique_violation,
)


def test_doctor_slot_advisory_lock_keys_stable() -> None:
    did = UUID("11111111-1111-1111-1111-111111111111")
    d = date(2026, 6, 15)
    t = time(14, 30, 5)
    a = doctor_slot_advisory_lock_int32_pair(did, d, t)
    b = doctor_slot_advisory_lock_int32_pair(did, d, t)
    assert a == b
    assert isinstance(a[0], int) and isinstance(a[1], int)
    assert -(2**31) <= a[0] < 2**31
    assert -(2**31) <= a[1] < 2**31


def test_doctor_slot_advisory_lock_keys_differ_by_time() -> None:
    did = UUID("22222222-2222-2222-2222-222222222222")
    d = date(2026, 6, 15)
    k1 = doctor_slot_advisory_lock_int32_pair(did, d, time(10, 0, 0))
    k2 = doctor_slot_advisory_lock_int32_pair(did, d, time(10, 30, 0))
    assert k1 != k2


def test_is_booking_doctor_slot_unique_violation_positive() -> None:
    class _Fake:
        def __str__(self) -> str:
            return 'duplicate key value violates unique constraint "ux_bookings_doctor_slot_active"'

    exc = Exception("wrapper")
    exc.orig = _Fake()
    assert is_booking_doctor_slot_unique_violation(exc) is True


def test_is_booking_doctor_slot_unique_violation_negative() -> None:
    exc = Exception("other fk failure")
    exc.orig = Exception("violates foreign key")
    assert is_booking_doctor_slot_unique_violation(exc) is False


@pytest.mark.parametrize("name", sorted(BOOKING_DOCTOR_SLOT_UNIQUE_NAMES))
def test_unique_name_literals_are_non_empty(name: str) -> None:
    assert name
