"""Booking service."""

import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.booking_dto import (
    BookingCreateAdmin,
    BookingCreatePatient,
    BookingRead,
    BookingRescheduleRequest,
)
from src.application.services.schedule_service import ScheduleService
from src.domain.entities.booking import Booking
from src.domain.entities.service_doctor import ServiceDoctor
from src.domain.entities.waitlist_entry import WaitlistEntry
from src.domain.interfaces.repositories.booking_repository import BookingRepository
from src.infrastructure.database.booking_repo_impl import BookingRepositoryImpl
from src.application.events.event_bus import get_event_bus
from src.application.events.standard_events import (
    make_booking_completed_event,
    make_booking_created_event,
)
from src.application.services.loyalty_service import LoyaltyService
from src.application.services.loyalty_service import UseSubscriptionForBookingInput
from src.core.patient_messages import (
    BOOKING_CANNOT_CANCEL_PAST,
    BOOKING_CANNOT_CANCEL_STATUS,
    BOOKING_CANNOT_RESCHEDULE_CANCELLED,
    BOOKING_DOCTOR_DOES_NOT_PROVIDE_SERVICE,
    BOOKING_INVALID_STATUS,
    BOOKING_NOT_FOUND,
    BOOKING_ONLY_PENDING_CONFIRMED_COMPLETED,
    BOOKING_ONLY_PENDING_CONFIRMED_NO_SHOW,
    BOOKING_SLOT_ALREADY_BOOKED,
)

logger = logging.getLogger(__name__)


ALLOWED_STATUSES = {"pending", "confirmed", "cancelled", "completed", "no_show"}


class BookingService:
    """Service for booking operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.session = session
        self.repository: BookingRepository = BookingRepositoryImpl(session)
        self.schedule_service = ScheduleService(session)

    async def _ensure_slot_available(
        self,
        doctor_id: UUID,
        appointment_date: date,
        appointment_time,
        ignore_booking_id: UUID | None = None,
    ) -> None:
        """Check that slot is free (no conflicting booking except maybe ignore_booking_id)."""
        existing = await self.repository.get_for_doctor_on_date(doctor_id, appointment_date)
        for b in existing:
            if (
                b.appointment_time == appointment_time
                and b.status != "cancelled"
                and (ignore_booking_id is None or b.id != ignore_booking_id)
            ):
                logger.info(
                    "Attempt to double book slot",
                    extra={
                        "doctor_id": str(doctor_id),
                        "date": appointment_date.isoformat(),
                        "time": appointment_time.isoformat(),
                        "existing_booking_id": str(b.id),
                    },
                )
                raise ValueError(BOOKING_SLOT_ALREADY_BOOKED)

    async def _ensure_service_doctor(self, service_id: UUID, doctor_id: UUID) -> None:
        """Raise ValueError if doctor does not provide this service (ServiceDoctor, active)."""
        result = await self.session.execute(
            select(ServiceDoctor).where(
                ServiceDoctor.service_id == service_id,
                ServiceDoctor.doctor_id == doctor_id,
                ServiceDoctor.is_active.is_(True),
            )
        )
        if result.scalar_one_or_none() is None:
            raise ValueError(BOOKING_DOCTOR_DOES_NOT_PROVIDE_SERVICE)

    async def create_patient_booking(
        self,
        patient_id: UUID,
        data: BookingCreatePatient,
    ) -> BookingRead:
        """Create booking from patient flow (status pending, no payment yet)."""
        await self._ensure_service_doctor(data.service_id, data.doctor_id)
        await self._ensure_slot_available(
            doctor_id=data.doctor_id,
            appointment_date=data.appointment_date,
            appointment_time=data.appointment_time,
        )

        booking = Booking(
            clinic_id=data.clinic_id,
            patient_id=patient_id,
            doctor_id=data.doctor_id,
            service_id=data.service_id,
            appointment_date=data.appointment_date,
            appointment_time=data.appointment_time,
            status="pending",
            prepayment_amount=Decimal("0.00"),
            notes=data.notes,
        )
        booking = await self.repository.create(booking)

        # Invalidate schedule cache for that day/doctor
        await self.schedule_service.invalidate_daily_schedule_cache(
            doctor_id=data.doctor_id,
            day=data.appointment_date,
        )

        try:
            from src.infrastructure.messaging.tasks.notifications import send_booking_created_task
            send_booking_created_task.delay(str(booking.id))
        except Exception as e:
            logger.warning("Failed to enqueue send_booking_created task", extra={"error": str(e)})

        event_bus = get_event_bus()
        try:
            await event_bus.publish(make_booking_created_event(booking))
        except Exception as e:
            logger.warning(
                "Failed to publish BookingCreated event (patient flow)",
                extra={"error": str(e), "booking_id": str(booking.id)},
            )

        logger.info(
            "Booking created via patient flow",
            extra={"booking_id": str(booking.id), "patient_id": str(patient_id)},
        )
        return BookingRead.model_validate(booking)

    async def create_admin_booking(self, clinic_id: UUID, data: BookingCreateAdmin) -> BookingRead:
        """Create booking from admin flow for a specific clinic. Optionally from waitlist (waitlist_entry_id)."""
        patient_id = data.patient_id
        doctor_id = data.doctor_id
        appointment_date = data.appointment_date
        appointment_time = data.appointment_time

        waitlist_entry: WaitlistEntry | None = None
        if data.waitlist_entry_id:
            waitlist_entry = await self.session.get(WaitlistEntry, data.waitlist_entry_id)
            if not waitlist_entry or waitlist_entry.clinic_id != clinic_id:
                raise LookupError("Waitlist entry not found")
            if waitlist_entry.status not in ("waiting", "notified"):
                raise ValueError("Waitlist entry is no longer available for conversion")
            patient_id = waitlist_entry.patient_id
            if waitlist_entry.doctor_id is not None:
                doctor_id = waitlist_entry.doctor_id
            if waitlist_entry.preferred_date is not None:
                appointment_date = waitlist_entry.preferred_date
            if waitlist_entry.preferred_time is not None:
                appointment_time = waitlist_entry.preferred_time

        if data.status not in ALLOWED_STATUSES:
            raise ValueError(BOOKING_INVALID_STATUS)
        await self._ensure_service_doctor(data.service_id, doctor_id)
        await self._ensure_slot_available(
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
        )

        prepayment = data.prepayment_amount or Decimal("0.00")

        booking = Booking(
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=data.service_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status=data.status,
            prepayment_amount=prepayment,
            notes=data.notes,
        )
        booking = await self.repository.create(booking)

        if waitlist_entry is not None:
            waitlist_entry.status = "converted"
            await self.session.flush()

        await self.schedule_service.invalidate_daily_schedule_cache(
            doctor_id=data.doctor_id,
            day=data.appointment_date,
        )

        try:
            from src.infrastructure.messaging.tasks.notifications import send_booking_created_task
            send_booking_created_task.delay(str(booking.id))
        except Exception as e:
            logger.warning("Failed to enqueue send_booking_created task", extra={"error": str(e)})

        event_bus = get_event_bus()
        try:
            await event_bus.publish(make_booking_created_event(booking))
        except Exception as e:
            logger.warning(
                "Failed to publish BookingCreated event (admin flow)",
                extra={"error": str(e), "booking_id": str(booking.id)},
            )

        logger.info(
            "Booking created via admin flow",
            extra={"booking_id": str(booking.id), "patient_id": str(data.patient_id)},
        )
        return BookingRead.model_validate(booking)

    async def get_patient_bookings(
        self,
        patient_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BookingRead]:
        """Get bookings for patient."""
        bookings = await self.repository.get_for_patient(
            patient_id=patient_id,
            skip=skip,
            limit=limit,
        )
        return [BookingRead.model_validate(b) for b in bookings]

    async def search_admin_bookings(
        self,
        clinic_id: UUID,
        doctor_id: UUID | None = None,
        date_filter: date | None = None,
        status: str | None = None,
        patient_phone: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BookingRead]:
        """Search bookings for admin with filters, scoped to clinic."""
        if status and status not in ALLOWED_STATUSES:
            raise ValueError(BOOKING_INVALID_STATUS)

        bookings = await self.repository.search_admin(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            date_filter=date_filter,
            status=status,
            patient_phone=patient_phone,
            skip=skip,
            limit=limit,
        )
        return [BookingRead.model_validate(b) for b in bookings]

    async def cancel_booking(self, clinic_id: UUID, booking_id: UUID) -> BookingRead:
        """Cancel booking within a specific clinic (ACL by clinic)."""
        booking = await self.repository.get_by_id(booking_id)
        if not booking or booking.clinic_id != clinic_id:
            raise LookupError(BOOKING_NOT_FOUND)

        if booking.status in {"completed", "cancelled"}:
            raise ValueError(BOOKING_CANNOT_CANCEL_STATUS)

        now = datetime.now()
        slot_date, slot_time = booking.appointment_date, booking.appointment_time
        if slot_date < now.date() or (
            slot_date == now.date() and slot_time <= now.time()
        ):
            raise ValueError(BOOKING_CANNOT_CANCEL_PAST)

        booking.status = "cancelled"
        booking = await self.repository.update(booking)

        try:
            await self.schedule_service.invalidate_daily_schedule_cache(
                doctor_id=booking.doctor_id,
                day=booking.appointment_date,
            )
        except Exception as e:
            logger.warning(
                "Schedule cache invalidation failed after cancel (Redis may be down)",
                extra={"booking_id": str(booking_id), "error": str(e)},
            )

        try:
            from src.infrastructure.messaging.tasks.notifications import send_booking_cancelled_task
            send_booking_cancelled_task.delay(str(booking_id))
        except Exception as e:
            logger.warning("Failed to enqueue send_booking_cancelled task", extra={"error": str(e)})

        try:
            from src.application.services.waitlist_service import WaitlistService
            waitlist_svc = WaitlistService(self.session)
            await waitlist_svc.notify_slot_freed(
                clinic_id=booking.clinic_id,
                doctor_id=booking.doctor_id,
                slot_date=booking.appointment_date,
                slot_time=booking.appointment_time,
            )
        except Exception as e:
            logger.warning("Waitlist notify_slot_freed failed", extra={"error": str(e)})

        logger.info(
            "Booking cancelled",
            extra={"booking_id": str(booking_id), "clinic_id": str(booking.clinic_id)},
        )
        return BookingRead.model_validate(booking)

    async def complete_booking(
        self,
        clinic_id: UUID,
        booking_id: UUID,
        use_subscription_id: UUID | None = None,
    ) -> BookingRead:
        """Mark booking as completed within a specific clinic (ACL by clinic).

        If use_subscription_id is provided, use that subscription for this booking (Checkout Hub).
        Otherwise try to auto-apply best subscription by priority.
        On successful usage mark booking.paid_by_subscription = True.
        Business errors from loyalty layer do not block completion.
        """
        booking = await self.repository.get_by_id(booking_id)
        if not booking or booking.clinic_id != clinic_id:
            raise LookupError(BOOKING_NOT_FOUND)

        if booking.status not in {"confirmed", "pending"}:
            raise ValueError(BOOKING_ONLY_PENDING_CONFIRMED_COMPLETED)

        loyalty_service = LoyaltyService(self.session)
        now = datetime.now()
        candidate = None
        if use_subscription_id is not None:
            sub = await loyalty_service.customer_repo.get_by_id(use_subscription_id)
            if (
                sub is not None
                and sub.clinic_id == clinic_id
                and sub.patient_id == booking.patient_id
                and sub.status == "active"
            ):
                candidate = sub
        if candidate is None and use_subscription_id is None:
            candidate = await loyalty_service.select_subscription_for_booking(
                clinic_id=booking.clinic_id,
                patient_id=booking.patient_id,
                booking_id=booking.id,
                on_date=now,
            )

        if candidate is not None:
            try:
                used_visits = 1 if (candidate.remaining_visits or 0) > 0 else None
                used_amount = None if used_visits else (candidate.remaining_amount or None)
                if used_visits is None and used_amount is None:
                    pass  # skip usage
                else:
                    await loyalty_service.use_subscription_for_booking(
                        UseSubscriptionForBookingInput(
                            clinic_id=booking.clinic_id,
                            booking_id=booking.id,
                            subscription_id=candidate.id,
                            used_visits=used_visits,
                            used_amount=used_amount,
                            used_at=now,
                        )
                    )
                    booking.paid_by_subscription = True
            except Exception as e:  # pragma: no cover
                logger.warning(
                    "Failed to apply subscription on booking completion",
                    extra={"booking_id": str(booking_id), "error": str(e)},
                )

        booking.status = "completed"
        booking = await self.repository.update(booking)

        event_bus = get_event_bus()
        try:
            await event_bus.publish(make_booking_completed_event(booking))
        except Exception as e:
            logger.warning(
                "Failed to publish BookingCompleted event",
                extra={"error": str(e), "booking_id": str(booking.id)},
            )

        logger.info(
            "Booking completed",
            extra={"booking_id": str(booking_id), "clinic_id": str(booking.clinic_id)},
        )
        return BookingRead.model_validate(booking)

    async def mark_no_show(self, clinic_id: UUID, booking_id: UUID) -> BookingRead:
        """Mark booking as no_show within a specific clinic (ACL by clinic)."""
        booking = await self.repository.get_by_id(booking_id)
        if not booking or booking.clinic_id != clinic_id:
            raise LookupError(BOOKING_NOT_FOUND)

        if booking.status not in {"confirmed", "pending"}:
            raise ValueError(BOOKING_ONLY_PENDING_CONFIRMED_NO_SHOW)

        booking.status = "no_show"
        booking = await self.repository.update(booking)

        logger.info(
            "Booking marked as no_show",
            extra={"booking_id": str(booking_id), "clinic_id": str(booking.clinic_id)},
        )
        return BookingRead.model_validate(booking)

    async def reschedule_booking(
        self,
        clinic_id: UUID,
        booking_id: UUID,
        data: BookingRescheduleRequest,
    ) -> BookingRead:
        """Reschedule booking to another slot; optionally to another doctor (validated via ServiceDoctor).

        ACL: booking must belong to the given clinic.
        """
        booking = await self.repository.get_by_id(booking_id)
        if not booking or booking.clinic_id != clinic_id:
            raise LookupError(BOOKING_NOT_FOUND)

        if booking.status == "cancelled":
            raise ValueError(BOOKING_CANNOT_RESCHEDULE_CANCELLED)

        target_doctor_id = data.to_doctor_id if data.to_doctor_id is not None else booking.doctor_id
        if target_doctor_id != booking.doctor_id:
            await self._ensure_service_doctor(booking.service_id, target_doctor_id)

        await self._ensure_slot_available(
            doctor_id=target_doctor_id,
            appointment_date=data.appointment_date,
            appointment_time=data.appointment_time,
            ignore_booking_id=booking.id,
        )

        old_doctor_id = booking.doctor_id
        old_date = booking.appointment_date
        booking.doctor_id = target_doctor_id
        booking.appointment_date = data.appointment_date
        booking.appointment_time = data.appointment_time
        booking = await self.repository.update(booking)

        await self.schedule_service.invalidate_daily_schedule_cache(
            doctor_id=old_doctor_id,
            day=old_date,
        )
        await self.schedule_service.invalidate_daily_schedule_cache(
            doctor_id=target_doctor_id,
            day=data.appointment_date,
        )
        if old_doctor_id != target_doctor_id:
            await self.schedule_service.invalidate_daily_schedule_cache(
                doctor_id=old_doctor_id,
                day=data.appointment_date,
            )
            await self.schedule_service.invalidate_daily_schedule_cache(
                doctor_id=target_doctor_id,
                day=old_date,
            )

        logger.info(
            "Booking rescheduled",
            extra={"booking_id": str(booking_id), "to_doctor_id": str(target_doctor_id)},
        )
        return BookingRead.model_validate(booking)

