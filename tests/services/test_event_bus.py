from __future__ import annotations

from typing import List
from unittest.mock import MagicMock

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


async def _event_bus_stub_failing_handler(_event: DomainEvent) -> None:
    raise RuntimeError("handler failed")


@pytest.mark.asyncio
async def test_event_bus_isolates_failing_handlers():
    """A failing subscriber must not block subsequent handlers on the same event."""
    bus = EventBus()
    called: list[str] = []

    async def first_ok(_event: DomainEvent) -> None:
        called.append("first")

    async def last_ok(_event: DomainEvent) -> None:
        called.append("last")

    bus.subscribe("BookingCompleted", first_ok)
    bus.subscribe("BookingCompleted", _event_bus_stub_failing_handler)
    bus.subscribe("BookingCompleted", last_ok)

    event = DomainEvent(name="BookingCompleted", payload={})
    await bus.publish(event)

    assert called == ["first", "last"]


@pytest.mark.asyncio
async def test_event_bus_handler_failure_increments_metric(monkeypatch):
    mock_counter = MagicMock()
    mock_labeled = MagicMock()
    mock_counter.labels.return_value = mock_labeled
    monkeypatch.setattr(
        "src.application.events.event_bus.domain_event_handler_failures_total",
        mock_counter,
    )

    bus = EventBus()
    bus.subscribe("BookingCompleted", _event_bus_stub_failing_handler)
    await bus.publish(DomainEvent(name="BookingCompleted", payload={}))

    mock_counter.labels.assert_called_once()
    kwargs = mock_counter.labels.call_args.kwargs
    assert kwargs["event_name"] == "BookingCompleted"
    assert kwargs["handler"].endswith("_event_bus_stub_failing_handler")
    mock_labeled.inc.assert_called_once()

