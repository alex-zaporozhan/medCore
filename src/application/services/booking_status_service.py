from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.domain.entities.booking import Booking, BookingStatus


@dataclass(frozen=True)
class BookingStatusTransitionRule:
    """Allowed transition from one status to another."""

    from_statuses: tuple[BookingStatus, ...]
    to_status: BookingStatus


class BookingStatusService:
    """
    Centralized state-machine for booking status transitions.

    Keeps all rules in one place so business logic is not scattered
    across services.

    Lifecycle (LEAD_BOOKING_STATUS_LIFECYCLE_RU): reception path may use
    pending → registered → confirmed → pending (зал ожидания) → in_progress;
    online prepayment may do pending → confirmed directly. See rules below.
    """

    _rules: tuple[BookingStatusTransitionRule, ...] = (
        # Подтверждение: оплата / политика (из pending), ресепшн после registered, webhook из awaiting_payment.
        BookingStatusTransitionRule(
            from_statuses=(BookingStatus.PENDING,),
            to_status=BookingStatus.CONFIRMED,
        ),
        BookingStatusTransitionRule(
            from_statuses=(BookingStatus.REGISTERED,),
            to_status=BookingStatus.CONFIRMED,
        ),
        BookingStatusTransitionRule(
            from_statuses=(BookingStatus.AWAITING_PAYMENT,),
            to_status=BookingStatus.CONFIRMED,
        ),
        # Регистрация на ресепшене (из «ожидает»).
        BookingStatusTransitionRule(
            from_statuses=(BookingStatus.PENDING,),
            to_status=BookingStatus.REGISTERED,
        ),
        # После подтверждения онлайн — в зал ожидания (тот же код pending).
        BookingStatusTransitionRule(
            from_statuses=(BookingStatus.CONFIRMED,),
            to_status=BookingStatus.PENDING,
        ),
        # На приём (кабинет).
        BookingStatusTransitionRule(
            from_statuses=(
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
                BookingStatus.REGISTERED,
            ),
            to_status=BookingStatus.IN_PROGRESS,
        ),
        BookingStatusTransitionRule(
            from_statuses=(
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
                BookingStatus.REGISTERED,
                BookingStatus.IN_PROGRESS,
            ),
            to_status=BookingStatus.COMPLETED,
        ),
        BookingStatusTransitionRule(
            from_statuses=(
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
                BookingStatus.REGISTERED,
                BookingStatus.IN_PROGRESS,
            ),
            to_status=BookingStatus.NO_SHOW,
        ),
        BookingStatusTransitionRule(
            from_statuses=(
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
                BookingStatus.AWAITING_PAYMENT,
                BookingStatus.REGISTERED,
                BookingStatus.IN_PROGRESS,
            ),
            to_status=BookingStatus.CANCELLED,
        ),
    )

    def allowed_next_statuses(self, from_status: BookingStatus) -> set[BookingStatus]:
        """Return all statuses that are allowed from given status."""
        allowed: set[BookingStatus] = set()
        for rule in self._rules:
            if from_status in rule.from_statuses:
                allowed.add(rule.to_status)
        return allowed

    def can_transition(self, from_status: BookingStatus, to_status: BookingStatus) -> bool:
        """Check if transition from -> to is allowed."""
        if from_status == to_status:
            return True
        return to_status in self.allowed_next_statuses(from_status)

    def assert_transition(self, from_status: BookingStatus, to_status: BookingStatus) -> None:
        """Raise ValueError if transition is not allowed."""
        if not self.can_transition(from_status, to_status):
            raise ValueError(f"Transition {from_status} -> {to_status} is not allowed")

    async def transition(self, booking: Booking, to_status: BookingStatus, *, context: dict | None = None) -> Booking:
        """
        Apply a status transition to booking with validation.

        This method only updates the in-memory object; caller is responsible
        for persisting changes via repository/session.
        """
        self.assert_transition(booking.status, to_status)
        booking.status = to_status
        return booking


def all_booking_status_values() -> Iterable[str]:
    """Utility: list of all status codes for validation and external contracts."""
    return [s.value for s in BookingStatus]
