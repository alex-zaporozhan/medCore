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
    """

    # Minimal ruleset based on current implementation and ARCH_DEV_BKG_STATE_002.
    # We intentionally keep it conservative and backward compatible.
    _rules: tuple[BookingStatusTransitionRule, ...] = (
        BookingStatusTransitionRule(
            from_statuses=(BookingStatus.PENDING,),
            to_status=BookingStatus.CONFIRMED,
        ),
        BookingStatusTransitionRule(
            from_statuses=(BookingStatus.PENDING, BookingStatus.CONFIRMED),
            to_status=BookingStatus.COMPLETED,
        ),
        BookingStatusTransitionRule(
            from_statuses=(BookingStatus.PENDING, BookingStatus.CONFIRMED),
            to_status=BookingStatus.NO_SHOW,
        ),
        BookingStatusTransitionRule(
            from_statuses=(
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
                BookingStatus.AWAITING_PAYMENT,
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

