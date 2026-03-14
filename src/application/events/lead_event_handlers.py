import logging
from decimal import Decimal
from uuid import UUID

from .event_bus import EventBus
from .standard_events import (
    BOOKING_COMPLETED,
    BOOKING_CREATED,
    CONTACT_CREATED,
    PAYMENT_SUCCESS,
)
from .domain_event import DomainEvent
from src.application.services.lead_service import LeadService
from src.infrastructure.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


def _uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    from uuid import UUID as _UUID

    try:
        return _UUID(value)
    except Exception:
        return None


async def handle_lead_on_contact_created(event: DomainEvent) -> None:
    """Create lead when new omnichannel contact is created (if patient is not linked)."""
    clinic_id = _uuid(event.payload.get("clinic_id"))
    contact_id = _uuid(event.payload.get("contact_id"))
    patient_id = _uuid(event.payload.get("patient_id"))

    if not clinic_id or not contact_id or patient_id is not None:
        return

    async with AsyncSessionLocal() as session:
        service = LeadService(session)

        existing = await service.repository.find_open_lead_for_contact_or_patient(
            clinic_id=clinic_id,
            omnichannel_contact_id=contact_id,
            patient_id=None,
        )
        if existing:
            return

        title = f"Новый лид из чата ({contact_id})"
        source = "omnichannel"

        lead = await service.create_lead_from_contact(
            clinic_id=clinic_id,
            omnichannel_contact_id=contact_id,
            patient_id=None,
            title=title,
            source=source,
            estimated_value=None,
        )


async def handle_lead_on_booking_created(event: DomainEvent) -> None:
    """Attach booking to existing lead and optionally move stage."""
    clinic_id = _uuid(event.payload.get("clinic_id"))
    booking_id = _uuid(event.payload.get("booking_id"))
    patient_id = _uuid(event.payload.get("patient_id"))

    if not clinic_id or not booking_id or not patient_id:
        return

    async with AsyncSessionLocal() as session:
        service = LeadService(session)
        lead = await service.repository.find_open_lead_for_contact_or_patient(
            clinic_id=clinic_id,
            omnichannel_contact_id=None,
            patient_id=patient_id,
        )
        if not lead:
            return

        await service.attach_booking(
            clinic_id=clinic_id,
            lead_id=lead.id,
            booking_id=booking_id,
            new_stage_id=None,
            new_estimated_value=None,
        )


async def handle_lead_on_payment_success(event: DomainEvent) -> None:
    """Update lead actual_value when payment succeeds."""
    clinic_id = _uuid(event.payload.get("clinic_id"))
    booking_id = _uuid(event.payload.get("booking_id"))
    amount_raw = event.payload.get("amount")

    if not clinic_id or not booking_id or amount_raw is None:
        return

    try:
        amount = Decimal(str(amount_raw))
    except Exception:
        logger.warning(
            "[CRM] Invalid payment amount in PaymentSuccess",
            extra={"payload": event.payload},
        )
        return

    async with AsyncSessionLocal() as session:
        service = LeadService(session)
        lead = await service.repository.get_lead_by_primary_booking_id(
            clinic_id=clinic_id, booking_id=booking_id
        )
        if not lead:
            return

        await service.apply_payment_to_lead(
            clinic_id=clinic_id,
            lead_id=lead.id,
            amount=amount,
            new_stage_id=None,
        )


async def handle_lead_on_booking_completed(event: DomainEvent) -> None:
    """Mark lead as success when booking is completed."""
    clinic_id = _uuid(event.payload.get("clinic_id"))
    booking_id = _uuid(event.payload.get("booking_id"))

    if not clinic_id or not booking_id:
        return

    async with AsyncSessionLocal() as session:
        service = LeadService(session)
        lead = await service.repository.get_lead_by_primary_booking_id(
            clinic_id=clinic_id, booking_id=booking_id
        )
        if not lead:
            return

        await service.close_lead_as_success(
            clinic_id=clinic_id,
            lead_id=lead.id,
            success_stage_id=lead.stage_id,
            actual_value=None,
        )


def register_lead_event_handlers(event_bus: EventBus) -> None:
    """Register CRM lead handlers on global EventBus."""
    event_bus.subscribe(CONTACT_CREATED, handle_lead_on_contact_created)
    event_bus.subscribe(BOOKING_CREATED, handle_lead_on_booking_created)
    event_bus.subscribe(BOOKING_COMPLETED, handle_lead_on_booking_completed)
    event_bus.subscribe(PAYMENT_SUCCESS, handle_lead_on_payment_success)

