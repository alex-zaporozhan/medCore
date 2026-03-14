import logging

from .event_bus import EventBus
from .standard_events import BOOKING_CREATED, PAYMENT_SUCCESS
from .domain_event import DomainEvent


logger = logging.getLogger(__name__)


async def handle_marketing_on_booking_created(event: DomainEvent) -> None:
    logger.info(
        "[MarketingAttribution] BookingCreated received",
        extra={"event_name": event.name, "payload": event.payload},
    )


async def handle_marketing_on_payment_success(event: DomainEvent) -> None:
    logger.info(
        "[MarketingAttribution] PaymentSuccess received",
        extra={"event_name": event.name, "payload": event.payload},
    )


def register_marketing_event_handlers(event_bus: EventBus) -> None:
    event_bus.subscribe(BOOKING_CREATED, handle_marketing_on_booking_created)
    event_bus.subscribe(PAYMENT_SUCCESS, handle_marketing_on_payment_success)

