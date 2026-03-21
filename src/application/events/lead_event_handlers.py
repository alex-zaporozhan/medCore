import logging
from uuid import UUID

from .event_bus import EventBus
from .standard_events import (
    BOOKING_COMPLETED,
    BOOKING_CREATED,
    BOOKING_CANCELLED,
    BOOKING_NO_SHOW,
    CONTACT_CREATED,
    PAYMENT_SUCCESS,
)
from .domain_event import DomainEvent
from src.application.dto.lead_lifecycle_dto import (
    LeadEventBookingCancelled,
    LeadEventBookingCreated,
    LeadEventContactCreated,
    LeadEventNoShow,
)
from src.application.services.lead_lifecycle_service import LeadLifecycleService
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
        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_contact_created(
            LeadEventContactCreated(
                clinic_id=clinic_id,
                contact_id=contact_id,
                patient_id=None,
                trace_id=event.payload.get("trace_id"),
                source="omnichannel",
                utm_source=event.payload.get("utm_source"),
                utm_medium=event.payload.get("utm_medium"),
                utm_campaign=event.payload.get("utm_campaign"),
            )
        )


async def handle_lead_on_booking_created(event: DomainEvent) -> None:
    """Attach booking to existing lead and optionally move stage."""
    clinic_id = _uuid(event.payload.get("clinic_id"))
    booking_id = _uuid(event.payload.get("booking_id"))
    patient_id = _uuid(event.payload.get("patient_id"))

    if not clinic_id or not booking_id or not patient_id:
        return

    async with AsyncSessionLocal() as session:
        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_booking_created(
            LeadEventBookingCreated(
                clinic_id=clinic_id,
                contact_id=_uuid(event.payload.get("contact_id")),
                patient_id=patient_id,
                booking_id=booking_id,
                trace_id=event.payload.get("trace_id"),
                source="booking",
            )
        )


async def handle_lead_on_payment_success(event: DomainEvent) -> None:
    """Refresh lead ``actual_value`` from ERP after payment (CRM does not add payment deltas locally)."""
    clinic_id = _uuid(event.payload.get("clinic_id"))
    booking_id = _uuid(event.payload.get("booking_id"))

    if not clinic_id or not booking_id:
        return

    async with AsyncSessionLocal() as session:
        from src.application.services.lead_service import LeadService

        service = LeadService(session)
        lead = await service.repository.get_lead_by_any_booking_id(clinic_id=clinic_id, booking_id=booking_id)
        if not lead:
            return

        await service.update_actual_value_from_erp(
            clinic_id=clinic_id,
            lead_id=lead.id,
            trace_id=event.payload.get("trace_id"),
            source="payment_success_event",
            extra_booking_ids=[booking_id],
        )


async def handle_lead_on_booking_completed(event: DomainEvent) -> None:
    """Mark lead as success when booking is completed (visit completed)."""
    clinic_id = _uuid(event.payload.get("clinic_id"))
    booking_id = _uuid(event.payload.get("booking_id"))

    if not clinic_id or not booking_id:
        return

    async with AsyncSessionLocal() as session:
        from src.application.services.crm_attribution_sync_service import CrmAttributionSyncService

        sync = CrmAttributionSyncService(session)
        await sync.on_booking_completed(
            clinic_id=clinic_id,
            booking_id=booking_id,
            trace_id=event.payload.get("trace_id"),
        )


async def handle_lead_on_booking_cancelled(event: DomainEvent) -> None:
    clinic_id = _uuid(event.payload.get("clinic_id"))
    booking_id = _uuid(event.payload.get("booking_id"))
    if not clinic_id or not booking_id:
        return

    async with AsyncSessionLocal() as session:
        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_booking_cancelled(
            LeadEventBookingCancelled(
                clinic_id=clinic_id,
                booking_id=booking_id,
                trace_id=event.payload.get("trace_id"),
                source="booking",
            )
        )


async def handle_lead_on_booking_no_show(event: DomainEvent) -> None:
    clinic_id = _uuid(event.payload.get("clinic_id"))
    booking_id = _uuid(event.payload.get("booking_id"))
    if not clinic_id or not booking_id:
        return

    async with AsyncSessionLocal() as session:
        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_no_show(
            LeadEventNoShow(
                clinic_id=clinic_id,
                booking_id=booking_id,
                trace_id=event.payload.get("trace_id"),
                source="booking",
            )
        )


def register_lead_event_handlers(event_bus: EventBus) -> None:
    """Register CRM lead handlers on global EventBus."""
    event_bus.subscribe(CONTACT_CREATED, handle_lead_on_contact_created)
    event_bus.subscribe(BOOKING_CREATED, handle_lead_on_booking_created)
    event_bus.subscribe(BOOKING_COMPLETED, handle_lead_on_booking_completed)
    event_bus.subscribe(BOOKING_CANCELLED, handle_lead_on_booking_cancelled)
    event_bus.subscribe(BOOKING_NO_SHOW, handle_lead_on_booking_no_show)
    event_bus.subscribe(PAYMENT_SUCCESS, handle_lead_on_payment_success)
