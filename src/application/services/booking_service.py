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
    BookingCompletionResult,
)
from src.application.multitenancy import assert_entity_belongs_to_clinic
from src.application.services.schedule_service import ScheduleService
from src.application.services.booking_status_service import (
    BookingStatusService,
    all_booking_status_values,
)
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.doctor import Doctor
from src.domain.entities.service import Service
from src.domain.entities.service_doctor import ServiceDoctor
from src.application.services.waitlist_service import WaitlistService, WaitlistServiceError
from src.domain.entities.waitlist_entry import WaitlistEntry
from src.domain.interfaces.repositories.booking_repository import BookingRepository
from src.infrastructure.database.booking_repo_impl import BookingRepositoryImpl
from src.infrastructure.database.lead_repo_impl import LeadRepositoryImpl
from src.application.events.event_bus import get_event_bus
from src.application.events.standard_events import (
    make_booking_cancelled_event,
    make_booking_completed_event,
    make_booking_created_event,
    make_booking_no_show_event,
)
from src.application.services.loyalty_service import LoyaltyService
from src.application.services.loyalty_service import UseSubscriptionForBookingInput
from src.core.context import RequestContext
from src.core.metrics import waitlist_booking_conversion_total
from src.core.tracing import with_trace_id
from src.core.patient_messages import (
    BOOKING_CANNOT_CANCEL_PAST,
    BOOKING_CANNOT_CANCEL_STATUS,
    BOOKING_CANNOT_RESCHEDULE_CANCELLED,
    BOOKING_CLINIC_MISMATCH_PATIENT,
    BOOKING_DOCTOR_DOES_NOT_PROVIDE_SERVICE,
    BOOKING_ENTITY_CLINIC_MISMATCH,
    BOOKING_INVALID_STATUS,
    BOOKING_NOT_FOUND,
    BOOKING_ONLY_PENDING_CONFIRMED_COMPLETED,
    BOOKING_ONLY_PENDING_CONFIRMED_NO_SHOW,
    BOOKING_SLOT_ALREADY_BOOKED,
    BOOKING_WAITLIST_CONVERSION_FAILED,
)

logger = logging.getLogger(__name__)


ALLOWED_STATUSES = set(all_booking_status_values())


class BookingService:
    """Service for booking operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.session = session
        self.repository: BookingRepository = BookingRepositoryImpl(session)
        self.schedule_service = ScheduleService(session)
        self.status_service = BookingStatusService()

    async def _omnichannel_contact_hint_for_patient(
        self,
        clinic_id: UUID,
        patient_id: UUID,
    ) -> UUID | None:
        """Best-effort: open lead may carry omnichannel contact for CRM BookingCreated payload."""
        lead_repo = LeadRepositoryImpl(self.session)
        lead = await lead_repo.find_open_lead_for_contact_or_patient(
            clinic_id, None, patient_id
        )
        return lead.omnichannel_contact_id if lead else None

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

    async def _ensure_booking_entities_in_clinic(
        self, clinic_id: UUID, service_id: UUID, doctor_id: UUID
    ) -> None:
        """Ensure doctor and service rows exist and belong to the same clinic as the booking."""
        doctor = await self.session.get(Doctor, doctor_id)
        if doctor is None or doctor.clinic_id != clinic_id:
            raise ValueError(BOOKING_ENTITY_CLINIC_MISMATCH)
        service = await self.session.get(Service, service_id)
        if service is None or service.clinic_id != clinic_id:
            raise ValueError(BOOKING_ENTITY_CLINIC_MISMATCH)

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
        patient_clinic_id: UUID,
        data: BookingCreatePatient,
        *,
        context: RequestContext | None = None,
    ) -> BookingRead:
        """Create booking from patient flow (status pending, no payment yet)."""
        if data.clinic_id != patient_clinic_id:
            raise ValueError(BOOKING_CLINIC_MISMATCH_PATIENT)
        await self._ensure_booking_entities_in_clinic(
            data.clinic_id, data.service_id, data.doctor_id
        )
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
            status=BookingStatus.PENDING,
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

            task_kwargs = with_trace_id(
                {
                    "booking_id": str(booking.id),
                },
                context,
            )
            send_booking_created_task.delay(**task_kwargs)
        except Exception as e:
            logger.warning("Failed to enqueue send_booking_created task", extra={"error": str(e)})

        event_bus = get_event_bus()
        try:
            omni = await self._omnichannel_contact_hint_for_patient(data.clinic_id, patient_id)
            await event_bus.publish(
                make_booking_created_event(
                    booking,
                    trace_id=getattr(context, "trace_id", None),
                    omnichannel_contact_id=omni,
                )
            )
        except Exception as e:
            logger.warning(
                "Failed to publish BookingCreated event (patient flow)",
                extra={"error": str(e), "booking_id": str(booking.id)},
            )

        logger.info(
            "Booking created via patient flow",
            extra={
                "booking_id": str(booking.id),
                "patient_id": str(patient_id),
                "clinic_id": str(data.clinic_id),
            },
        )
        return BookingRead.model_validate(booking)

    async def create_admin_booking(
        self,
        clinic_id: UUID,
        data: BookingCreateAdmin,
        *,
        context: RequestContext | None = None,
    ) -> BookingRead:
        """Create booking from admin flow for a specific clinic. Optionally from waitlist (waitlist_entry_id)."""
        if data.clinic_id != clinic_id:
            raise ValueError(BOOKING_ENTITY_CLINIC_MISMATCH)
        patient_id = data.patient_id
        doctor_id = data.doctor_id
        appointment_date = data.appointment_date
        appointment_time = data.appointment_time

        waitlist_entry: WaitlistEntry | None = None
        if data.waitlist_entry_id:
            wl = WaitlistService(self.session)
            waitlist_entry = await wl.lock_entry_for_admin_booking(
                clinic_id, data.waitlist_entry_id
            )
            patient_id = waitlist_entry.patient_id
            if waitlist_entry.doctor_id is not None:
                doctor_id = waitlist_entry.doctor_id
            if waitlist_entry.preferred_date is not None:
                appointment_date = waitlist_entry.preferred_date
            if waitlist_entry.preferred_time is not None:
                appointment_time = waitlist_entry.preferred_time

        if data.status not in ALLOWED_STATUSES:
            raise ValueError(BOOKING_INVALID_STATUS)
        await self._ensure_booking_entities_in_clinic(
            clinic_id, data.service_id, doctor_id
        )
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
            status=BookingStatus(data.status),
            prepayment_amount=prepayment,
            notes=data.notes,
        )
        booking = await self.repository.create(booking)

        if waitlist_entry is not None:
            try:
                await WaitlistService(self.session).mark_booked_after_booking_created(
                    clinic_id,
                    waitlist_entry.id,
                    booking.id,
                    actor_admin_id=None,
                )
            except (WaitlistServiceError, LookupError) as e:
                waitlist_booking_conversion_total.labels(
                    clinic_id=str(clinic_id), outcome="error"
                ).inc()
                logger.error(
                    "waitlist_mark_booked_failed",
                    extra={
                        "clinic_id": str(clinic_id),
                        "waitlist_entry_id": str(waitlist_entry.id),
                        "booking_id": str(booking.id),
                        "error": str(e.args[0]) if e.args else type(e).__name__,
                    },
                )
                try:
                    await self.repository.delete(booking.id)
                except Exception as del_err:
                    logger.error(
                        "waitlist_compensate_delete_failed",
                        extra={
                            "booking_id": str(booking.id),
                            "error": str(del_err),
                        },
                    )
                raise ValueError(BOOKING_WAITLIST_CONVERSION_FAILED) from e

        await self.schedule_service.invalidate_daily_schedule_cache(
            doctor_id=doctor_id,
            day=appointment_date,
        )

        try:
            from src.infrastructure.messaging.tasks.notifications import send_booking_created_task

            task_kwargs = with_trace_id(
                {
                    "booking_id": str(booking.id),
                },
                context,
            )
            send_booking_created_task.delay(**task_kwargs)
        except Exception as e:
            logger.warning("Failed to enqueue send_booking_created task", extra={"error": str(e)})

        event_bus = get_event_bus()
        try:
            omni = await self._omnichannel_contact_hint_for_patient(clinic_id, patient_id)
            await event_bus.publish(
                make_booking_created_event(
                    booking,
                    trace_id=getattr(context, "trace_id", None),
                    omnichannel_contact_id=omni,
                )
            )
        except Exception as e:
            logger.warning(
                "Failed to publish BookingCreated event (admin flow)",
                extra={"error": str(e), "booking_id": str(booking.id)},
            )

        logger.info(
            "Booking created via admin flow",
            extra={
                "booking_id": str(booking.id),
                "patient_id": str(patient_id),
                "clinic_id": str(clinic_id),
            },
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

    async def cancel_booking(
        self,
        clinic_id: UUID,
        booking_id: UUID,
        *,
        context: RequestContext | None = None,
    ) -> BookingRead:
        """Cancel booking within a specific clinic (ACL by clinic)."""
        booking = await self.repository.get_by_id(booking_id)
        if not booking:
            raise LookupError(BOOKING_NOT_FOUND)
        assert_entity_belongs_to_clinic(booking, clinic_id, entity_label="booking")

        if booking.status in {BookingStatus.COMPLETED, BookingStatus.CANCELLED}:
            raise ValueError(BOOKING_CANNOT_CANCEL_STATUS)

        now = datetime.now()
        slot_date, slot_time = booking.appointment_date, booking.appointment_time
        if slot_date < now.date() or (
            slot_date == now.date() and slot_time <= now.time()
        ):
            raise ValueError(BOOKING_CANNOT_CANCEL_PAST)

        await self.status_service.transition(booking, BookingStatus.CANCELLED, context={})
        booking = await self.repository.update(booking)

        event_bus = get_event_bus()
        try:
            await event_bus.publish(make_booking_cancelled_event(booking, trace_id=getattr(context, "trace_id", None)))
        except Exception as e:
            logger.warning(
                "Failed to publish BookingCancelled event",
                extra={"error": str(e), "booking_id": str(booking.id)},
            )

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

            task_kwargs = with_trace_id(
                {
                    "booking_id": str(booking_id),
                },
                context,
            )
            send_booking_cancelled_task.delay(**task_kwargs)
        except Exception as e:
            logger.warning("Failed to enqueue send_booking_cancelled task", extra={"error": str(e)})

        try:
            waitlist_svc = WaitlistService(self.session)
            await waitlist_svc.notify_slot_freed(
                clinic_id=booking.clinic_id,
                doctor_id=booking.doctor_id,
                slot_date=booking.appointment_date,
                slot_time=booking.appointment_time,
                service_id=booking.service_id,
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
        *,
        context: RequestContext | None = None,
    ) -> BookingRead:
        """Legacy entrypoint to mark booking as completed within a specific clinic (ACL by clinic).

        TODO (DEV_PROMPT_BKG_CORE_001): migrate this flow to BookingCompletionService facade.
        """
        booking = await self.repository.get_by_id(booking_id)
        if not booking:
            raise LookupError(BOOKING_NOT_FOUND)
        assert_entity_belongs_to_clinic(booking, clinic_id, entity_label="booking")

        if booking.status not in {BookingStatus.CONFIRMED, BookingStatus.PENDING}:
            raise ValueError(BOOKING_ONLY_PENDING_CONFIRMED_COMPLETED)

        loyalty_service = LoyaltyService(self.session)
        now = datetime.now()
        candidate = None
        if use_subscription_id is not None:
            sub = await loyalty_service.customer_repo.get_by_id(use_subscription_id)
            if (
                sub is not None
                and sub.clinic_id == clinic_id
                and sub.status == "active"
                and await loyalty_service.patient_can_use_subscription(
                    clinic_id,
                    sub,
                    booking.patient_id,
                    now,
                )
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
                            beneficiary_patient_id=booking.patient_id,
                        )
                    )
                    booking.paid_by_subscription = True
            except Exception as e:  # pragma: no cover
                logger.warning(
                    "Failed to apply subscription on booking completion",
                    extra={"booking_id": str(booking_id), "error": str(e)},
                )

        await self.status_service.transition(booking, BookingStatus.COMPLETED, context={})
        booking = await self.repository.update(booking)

        event_bus = get_event_bus()
        try:
            await event_bus.publish(make_booking_completed_event(booking, trace_id=getattr(context, "trace_id", None)))
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

    async def mark_no_show(
        self,
        clinic_id: UUID,
        booking_id: UUID,
        *,
        context: RequestContext | None = None,
    ) -> BookingRead:
        """Mark booking as no_show within a specific clinic (ACL by clinic)."""
        booking = await self.repository.get_by_id(booking_id)
        if not booking:
            raise LookupError(BOOKING_NOT_FOUND)
        assert_entity_belongs_to_clinic(booking, clinic_id, entity_label="booking")

        if booking.status not in {BookingStatus.CONFIRMED, BookingStatus.PENDING}:
            raise ValueError(BOOKING_ONLY_PENDING_CONFIRMED_NO_SHOW)

        await self.status_service.transition(booking, BookingStatus.NO_SHOW, context={})
        booking = await self.repository.update(booking)

        event_bus = get_event_bus()
        try:
            await event_bus.publish(make_booking_no_show_event(booking, trace_id=getattr(context, "trace_id", None)))
        except Exception as e:
            logger.warning(
                "Failed to publish BookingNoShow event",
                extra={"error": str(e), "booking_id": str(booking.id)},
            )

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
        if not booking:
            raise LookupError(BOOKING_NOT_FOUND)
        assert_entity_belongs_to_clinic(booking, clinic_id, entity_label="booking")

        if booking.status == BookingStatus.CANCELLED:
            raise ValueError(BOOKING_CANNOT_RESCHEDULE_CANCELLED)

        target_doctor_id = data.to_doctor_id if data.to_doctor_id is not None else booking.doctor_id
        target_doctor = await self.session.get(Doctor, target_doctor_id)
        if not target_doctor or target_doctor.clinic_id != clinic_id:
            raise ValueError(BOOKING_ENTITY_CLINIC_MISMATCH)
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
            extra={
                "booking_id": str(booking_id),
                "clinic_id": str(clinic_id),
                "to_doctor_id": str(target_doctor_id),
            },
        )
        return BookingRead.model_validate(booking)

