from src.application.services.booking_status_service import BookingStatusService
from src.domain.entities.booking import BookingStatus


def test_pending_to_registered_confirmed_and_in_progress():
    svc = BookingStatusService()
    assert svc.can_transition(BookingStatus.PENDING, BookingStatus.REGISTERED)
    assert svc.can_transition(BookingStatus.PENDING, BookingStatus.CONFIRMED)
    assert svc.can_transition(BookingStatus.PENDING, BookingStatus.IN_PROGRESS)


def test_registered_to_confirmed():
    svc = BookingStatusService()
    assert svc.can_transition(BookingStatus.REGISTERED, BookingStatus.CONFIRMED)
    assert svc.can_transition(BookingStatus.REGISTERED, BookingStatus.IN_PROGRESS)
    assert svc.can_transition(BookingStatus.REGISTERED, BookingStatus.CANCELLED)


def test_confirmed_to_in_progress_and_final():
    svc = BookingStatusService()
    assert svc.can_transition(BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS)
    assert svc.can_transition(BookingStatus.CONFIRMED, BookingStatus.COMPLETED)
    assert svc.can_transition(BookingStatus.CONFIRMED, BookingStatus.NO_SHOW)
    assert svc.can_transition(BookingStatus.CONFIRMED, BookingStatus.CANCELLED)


def test_in_progress_to_final_only():
    svc = BookingStatusService()
    assert svc.can_transition(BookingStatus.IN_PROGRESS, BookingStatus.COMPLETED)
    assert svc.can_transition(BookingStatus.IN_PROGRESS, BookingStatus.NO_SHOW)
    assert svc.can_transition(BookingStatus.IN_PROGRESS, BookingStatus.CANCELLED)
    assert svc.can_transition(BookingStatus.IN_PROGRESS, BookingStatus.CONFIRMED) is False


def test_awaiting_payment_to_confirmed_and_cancelled():
    svc = BookingStatusService()
    assert svc.can_transition(BookingStatus.AWAITING_PAYMENT, BookingStatus.CONFIRMED)
    assert svc.can_transition(BookingStatus.AWAITING_PAYMENT, BookingStatus.CANCELLED)


def test_cancellation_from_active_statuses():
    svc = BookingStatusService()
    assert svc.can_transition(BookingStatus.PENDING, BookingStatus.CANCELLED)
    assert svc.can_transition(BookingStatus.CONFIRMED, BookingStatus.CANCELLED)
    assert svc.can_transition(BookingStatus.AWAITING_PAYMENT, BookingStatus.CANCELLED)
    assert svc.can_transition(BookingStatus.REGISTERED, BookingStatus.CANCELLED)
    assert svc.can_transition(BookingStatus.IN_PROGRESS, BookingStatus.CANCELLED)


def test_forbidden_from_terminal():
    svc = BookingStatusService()
    assert svc.can_transition(BookingStatus.COMPLETED, BookingStatus.PENDING) is False
    assert svc.can_transition(BookingStatus.COMPLETED, BookingStatus.CONFIRMED) is False
    assert svc.can_transition(BookingStatus.NO_SHOW, BookingStatus.PENDING) is False
