import uuid
from decimal import Decimal
from uuid import UUID

from src.domain.entities.booking import Booking
from src.domain.entities.payment import Payment

from .domain_event import DomainEvent


BOOKING_CREATED = "BookingCreated"
BOOKING_COMPLETED = "BookingCompleted"
BOOKING_CANCELLED = "BookingCancelled"
BOOKING_NO_SHOW = "BookingNoShow"
PAYMENT_SUCCESS = "PaymentSuccess"
CONTACT_CREATED = "ContactCreated"
LEAD_STAGE_CHANGED = "LeadStageChanged"

# Stable namespace for idempotent handler dedup (Tasks, CRM side-effects).
_BOOKING_EVENT_DEDUP_NS = uuid.UUID("3d813cbb-47b8-4ebe-a005-5c2c9b8f0e1a")


def booking_event_dedup_id(event_name: str, booking_id: UUID) -> UUID:
    """Deterministic id per (event type, booking) for Task.source_event_id / dedup."""
    return uuid.uuid5(_BOOKING_EVENT_DEDUP_NS, f"{event_name}:{booking_id}")


def make_booking_created_event(
    booking: Booking,
    *,
    trace_id: str | None = None,
    omnichannel_contact_id: UUID | None = None,
) -> DomainEvent:
    payload: dict[str, str | object | None] = {
        "booking_id": str(booking.id),
        "clinic_id": str(booking.clinic_id),
        "patient_id": str(booking.patient_id),
        "doctor_id": str(booking.doctor_id),
        "service_id": str(booking.service_id),
        "status": booking.status,
        "appointment_date": booking.appointment_date.isoformat(),
        "appointment_time": booking.appointment_time.isoformat(),
        "trace_id": trace_id,
        "dedup_id": str(booking_event_dedup_id(BOOKING_CREATED, booking.id)),
    }
    if omnichannel_contact_id is not None:
        payload["contact_id"] = str(omnichannel_contact_id)
    return DomainEvent(
        name=BOOKING_CREATED,
        payload=payload,
    )


def make_booking_completed_event(
    booking: Booking,
    *,
    trace_id: str | None = None,
    visit_revenue: Decimal | None = None,
) -> DomainEvent:
    """``visit_revenue`` is deprecated: do not use as financial fact — CRM reads ERP income only (CRM_MONEY_008)."""
    payload: dict[str, str | object | None] = {
        "booking_id": str(booking.id),
        "clinic_id": str(booking.clinic_id),
        "patient_id": str(booking.patient_id),
        "doctor_id": str(booking.doctor_id),
        "service_id": str(booking.service_id),
        "status": booking.status,
        "appointment_date": booking.appointment_date.isoformat(),
        "appointment_time": booking.appointment_time.isoformat(),
        "trace_id": trace_id,
        "dedup_id": str(booking_event_dedup_id(BOOKING_COMPLETED, booking.id)),
    }
    if visit_revenue is not None:
        payload["visit_revenue"] = str(visit_revenue)
    return DomainEvent(
        name=BOOKING_COMPLETED,
        payload=payload,
    )


def make_booking_cancelled_event(booking: Booking, *, trace_id: str | None = None) -> DomainEvent:
    return DomainEvent(
        name=BOOKING_CANCELLED,
        payload={
            "booking_id": str(booking.id),
            "clinic_id": str(booking.clinic_id),
            "patient_id": str(booking.patient_id),
            "doctor_id": str(booking.doctor_id),
            "service_id": str(booking.service_id),
            "status": booking.status,
            "appointment_date": booking.appointment_date.isoformat(),
            "appointment_time": booking.appointment_time.isoformat(),
            "trace_id": trace_id,
            "dedup_id": str(booking_event_dedup_id(BOOKING_CANCELLED, booking.id)),
        },
    )


def make_booking_no_show_event(booking: Booking, *, trace_id: str | None = None) -> DomainEvent:
    return DomainEvent(
        name=BOOKING_NO_SHOW,
        payload={
            "booking_id": str(booking.id),
            "clinic_id": str(booking.clinic_id),
            "patient_id": str(booking.patient_id),
            "doctor_id": str(booking.doctor_id),
            "service_id": str(booking.service_id),
            "status": booking.status,
            "appointment_date": booking.appointment_date.isoformat(),
            "appointment_time": booking.appointment_time.isoformat(),
            "trace_id": trace_id,
            "dedup_id": str(booking_event_dedup_id(BOOKING_NO_SHOW, booking.id)),
        },
    )


def make_payment_success_event(payment: Payment) -> DomainEvent:
    return DomainEvent(
        name=PAYMENT_SUCCESS,
        payload={
            "payment_id": str(payment.id),
            "clinic_id": str(payment.clinic_id),
            "booking_id": str(payment.booking_id),
            "status": payment.status,
            "amount": str(payment.amount),
            "currency": payment.currency,
        },
    )


def make_contact_created_event(
    contact_id: UUID,
    clinic_id: UUID,
    patient_id: UUID | None,
    *,
    trace_id: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
) -> DomainEvent:
    payload: dict[str, str | None] = {
        "contact_id": str(contact_id),
        "clinic_id": str(clinic_id),
        "patient_id": str(patient_id) if patient_id is not None else None,
        "trace_id": trace_id,
    }
    if utm_source is not None:
        payload["utm_source"] = utm_source
    if utm_medium is not None:
        payload["utm_medium"] = utm_medium
    if utm_campaign is not None:
        payload["utm_campaign"] = utm_campaign
    return DomainEvent(
        name=CONTACT_CREATED,
        payload=payload,
    )


def make_lead_stage_changed_event(
    *,
    clinic_id: UUID,
    lead_id: UUID,
    prev_stage_id: UUID,
    target_stage_id: UUID,
    initiated_by_ai: bool,
    reason: str | None,
    trace_id: str | None,
    actor_type: str | None,
    actor_id: UUID | None,
) -> DomainEvent:
    return DomainEvent(
        name=LEAD_STAGE_CHANGED,
        payload={
            "clinic_id": str(clinic_id),
            "lead_id": str(lead_id),
            "prev_stage_id": str(prev_stage_id),
            "target_stage_id": str(target_stage_id),
            "initiated_by_ai": bool(initiated_by_ai),
            "reason": (reason or "")[:500] if reason else None,
            "trace_id": trace_id,
            "actor_type": actor_type,
            "actor_id": str(actor_id) if actor_id else None,
        },
    )

