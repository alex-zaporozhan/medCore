from __future__ import annotations

import asyncio
from typing import List

import pytest

from src.application.events.domain_event import DomainEvent
from src.application.events.event_bus import EventBus


@pytest.mark.asyncio
async def test_event_bus_single_handler_called():
    bus = EventBus()
    received: List[DomainEvent] = []

    async def handler(event: DomainEvent) -> None:
        received.append(event)

    bus.subscribe("BookingCreated", handler)

    event = DomainEvent(name="BookingCreated", payload={"foo": "bar"})
    await bus.publish(event)

    assert len(received) == 1
    assert received[0].name == "BookingCreated"
    assert received[0].payload == {"foo": "bar"}


@pytest.mark.asyncio
async def test_event_bus_multiple_handlers_called():
    bus = EventBus()
    called = []

    async def h1(event: DomainEvent) -> None:
        called.append(("h1", event.name))

    async def h2(event: DomainEvent) -> None:
        called.append(("h2", event.name))

    bus.subscribe("PaymentSuccess", h1)
    bus.subscribe("PaymentSuccess", h2)

    event = DomainEvent(name="PaymentSuccess", payload={})
    await bus.publish(event)

    assert ("h1", "PaymentSuccess") in called
    assert ("h2", "PaymentSuccess") in called
    assert len(called) == 2


@pytest.mark.asyncio
async def test_event_bus_many_events_and_subscribers():
    bus = EventBus()
    received: list[str] = []

    async def h1(event: DomainEvent) -> None:
        received.append(f"h1:{event.name}")

    async def h2(event: DomainEvent) -> None:
        received.append(f"h2:{event.name}")

    bus.subscribe("BookingCreated", h1)
    bus.subscribe("BookingCreated", h2)

    # Publish a burst of events and ensure all handlers are called for each.
    total_events = 50
    for i in range(total_events):
        event = DomainEvent(name="BookingCreated", payload={"i": i})
        await bus.publish(event)

    assert len(received) == total_events * 2
    assert all(name.startswith(("h1:", "h2:")) for name in received)


@pytest.mark.asyncio
async def test_event_bus_does_not_swallow_exceptions():
    bus = EventBus()
    called: list[str] = []

    async def good_handler(event: DomainEvent) -> None:
        called.append("good")

    async def failing_handler(event: DomainEvent) -> None:
        raise RuntimeError("handler failed")

    bus.subscribe("BookingCompleted", good_handler)
    bus.subscribe("BookingCompleted", failing_handler)

    event = DomainEvent(name="BookingCompleted", payload={})

    with pytest.raises(RuntimeError):
        await bus.publish(event)

    # Even если один из хендлеров упал, остальные вызовы до исключения уже произошли.
    assert "good" in called

