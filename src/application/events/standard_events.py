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


def make_booking_created_event(booking: Booking) -> DomainEvent:
    return DomainEvent(
        name=BOOKING_CREATED,
        payload={
            "booking_id": str(booking.id),
            "clinic_id": str(booking.clinic_id),
            "patient_id": str(booking.patient_id),
            "doctor_id": str(booking.doctor_id),
            "service_id": str(booking.service_id),
            "status": booking.status,
            "appointment_date": booking.appointment_date.isoformat(),
            "appointment_time": booking.appointment_time.isoformat(),
        },
    )


def make_booking_completed_event(booking: Booking) -> DomainEvent:
    return DomainEvent(
        name=BOOKING_COMPLETED,
        payload={
            "booking_id": str(booking.id),
            "clinic_id": str(booking.clinic_id),
            "patient_id": str(booking.patient_id),
            "doctor_id": str(booking.doctor_id),
            "service_id": str(booking.service_id),
            "status": booking.status,
            "appointment_date": booking.appointment_date.isoformat(),
            "appointment_time": booking.appointment_time.isoformat(),
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


def make_contact_created_event(contact_id: UUID, clinic_id: UUID, patient_id: UUID | None) -> DomainEvent:
    return DomainEvent(
        name=CONTACT_CREATED,
        payload={
            "contact_id": str(contact_id),
            "clinic_id": str(clinic_id),
            "patient_id": str(patient_id) if patient_id is not None else None,
        },
    )

