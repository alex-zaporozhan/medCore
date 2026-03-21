import logging
from collections import defaultdict
from typing import Awaitable, Callable, Dict, List

from src.core.metrics import domain_event_handler_failures_total

from .domain_event import DomainEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[DomainEvent], Awaitable[None]]


def _handler_metric_label(handler: EventHandler) -> str:
    fn = getattr(handler, "__func__", handler)
    mod = getattr(fn, "__module__", "") or ""
    qual = getattr(fn, "__qualname__", None) or getattr(handler, "__name__", "unknown")
    return f"{mod}.{qual}" if mod else str(qual)


class EventBus:
    """Simple in-process async event bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)

    def subscribe(self, name: str, handler: EventHandler) -> None:
        """Subscribe handler to a specific event name."""
        self._subscribers[name].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Publish event to all subscribed handlers.

        Each handler runs in isolation: an exception in one handler does not
        prevent others from running. Failures are logged and counted in
        ``domain_event_handler_failures_total``.
        """
        handlers = list(self._subscribers.get(event.name, []))
        for handler in handlers:
            label = _handler_metric_label(handler)
            try:
                await handler(event)
            except Exception:
                domain_event_handler_failures_total.labels(
                    event_name=event.name,
                    handler=label,
                ).inc()
                logger.exception(
                    "Domain event handler failed event_name=%s handler=%s",
                    event.name,
                    label,
                )

    def clear_subscribers(self) -> None:
        """Clear all subscribers (useful for tests)."""
        self._subscribers.clear()


# Simple global instance for application use.
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Accessor for global EventBus instance."""
    return event_bus

