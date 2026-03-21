from src.application.services.booking_status_service import BookingStatusService
from src.domain.entities.booking import BookingStatus


def test_allowed_transitions_basic():
    svc = BookingStatusService()

    assert BookingStatus.CONFIRMED in svc.allowed_next_statuses(BookingStatus.PENDING)
    assert BookingStatus.COMPLETED in svc.allowed_next_statuses(BookingStatus.PENDING)
    assert BookingStatus.COMPLETED in svc.allowed_next_statuses(BookingStatus.CONFIRMED)
    assert BookingStatus.NO_SHOW in svc.allowed_next_statuses(BookingStatus.PENDING)
    assert BookingStatus.NO_SHOW in svc.allowed_next_statuses(BookingStatus.CONFIRMED)


def test_cancellation_transitions():
    svc = BookingStatusService()

    assert svc.can_transition(BookingStatus.PENDING, BookingStatus.CANCELLED)
    assert svc.can_transition(BookingStatus.CONFIRMED, BookingStatus.CANCELLED)
    assert svc.can_transition(BookingStatus.AWAITING_PAYMENT, BookingStatus.CANCELLED)


def test_forbidden_transition():
    svc = BookingStatusService()

    assert svc.can_transition(BookingStatus.COMPLETED, BookingStatus.PENDING) is False
    assert svc.can_transition(BookingStatus.COMPLETED, BookingStatus.CONFIRMED) is False

