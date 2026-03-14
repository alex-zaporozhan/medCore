from collections import defaultdict
from typing import Awaitable, Callable, Dict, List

from .domain_event import DomainEvent


EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """Simple in-process async event bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)

    def subscribe(self, name: str, handler: EventHandler) -> None:
        """Subscribe handler to a specific event name."""
        self._subscribers[name].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Publish event to all subscribed handlers."""
        handlers = list(self._subscribers.get(event.name, []))
        for handler in handlers:
            await handler(event)

    def clear_subscribers(self) -> None:
        """Clear all subscribers (useful for tests)."""
        self._subscribers.clear()


# Simple global instance for application use.
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Accessor for global EventBus instance."""
    return event_bus

