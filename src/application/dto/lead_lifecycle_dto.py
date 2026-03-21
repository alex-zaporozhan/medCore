"""Typed CRM lifecycle event payloads (ARCH_DEV_CRM_EVENTS_007 §3.1).

Stage resolution for transitions lives in:
- ``LeadStageSemanticsService`` (semantic → stage_id and stage → semantic),
- ``LeadStageStateMachine`` (allowed semantic transitions, used inside ``LeadService``).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

# Short names for logs / metrics (low-cardinality)
LIFECYCLE_EVENT_CONTACT_CREATED = "contact_created"
LIFECYCLE_EVENT_BOOKING_CREATED = "booking_created"
LIFECYCLE_EVENT_VISIT_COMPLETED = "visit_completed"
LIFECYCLE_EVENT_BOOKING_CANCELLED = "booking_cancelled"
LIFECYCLE_EVENT_NO_SHOW = "no_show"
LIFECYCLE_EVENT_STALE = "stale"


@dataclass(frozen=True)
class LeadEventContactCreated:
    clinic_id: UUID
    contact_id: UUID
    patient_id: UUID | None = None
    trace_id: str | None = None
    source: str = "omnichannel"
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None


@dataclass(frozen=True)
class LeadEventBookingCreated:
    clinic_id: UUID
    booking_id: UUID
    patient_id: UUID
    contact_id: UUID | None = None
    trace_id: str | None = None
    source: str = "booking"


@dataclass(frozen=True)
class LeadEventVisitCompleted:
    """Booking visit completed (facade sets Booking.status → completed).

    ``visit_revenue`` is legacy payload from BOOKING_COMPLETED events; CRM refreshes
    ``LeadCard.actual_value`` from ERP income rows instead (CRM_MONEY_008).
    """

    clinic_id: UUID
    booking_id: UUID
    trace_id: str | None = None
    source: str = "booking"
    visit_revenue: Decimal | None = None


@dataclass(frozen=True)
class LeadEventBookingCancelled:
    clinic_id: UUID
    booking_id: UUID
    trace_id: str | None = None
    source: str = "booking"


@dataclass(frozen=True)
class LeadEventNoShow:
    clinic_id: UUID
    booking_id: UUID
    trace_id: str | None = None
    source: str = "booking"


@dataclass(frozen=True)
class LeadEventStale:
    clinic_id: UUID
    lead_id: UUID
    trace_id: str | None = None
    source: str = "system"
