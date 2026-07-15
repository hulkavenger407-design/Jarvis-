"""
Tests for the Event Bus subsystem.
"""
import pytest
from kernel.eventbus.bus import EventBus
from kernel.eventbus.models import Event, EventValidationError


@pytest.fixture
def bus() -> EventBus:
    return EventBus()

@pytest.mark.asyncio
async def test_publish_subscribe(bus: EventBus) -> None:
    received_events = []

    async def handler(event: Event) -> None:
        received_events.append(event)

    bus.subscribe("test.action.started", handler)

    event = Event(type="test.action.started", payload={"key": "value"})
    await bus.publish(event)

    assert len(received_events) == 1
    assert received_events[0] == event

@pytest.mark.asyncio
async def test_unsubscribe(bus: EventBus) -> None:
    received_events = []

    async def handler(event: Event) -> None:
        received_events.append(event)

    bus.subscribe("test.action.started", handler)
    bus.unsubscribe("test.action.started", handler)

    event = Event(type="test.action.started", payload={"key": "value"})
    await bus.publish(event)

    assert len(received_events) == 0

@pytest.mark.asyncio
async def test_multiple_subscribers(bus: EventBus) -> None:
    calls = []

    async def handler1(event: Event) -> None:
        calls.append("handler1")

    async def handler2(event: Event) -> None:
        calls.append("handler2")

    bus.subscribe("test.action.started", handler1)
    bus.subscribe("test.action.started", handler2)

    event = Event(type="test.action.started")
    await bus.publish(event)

    assert len(calls) == 2
    assert "handler1" in calls
    assert "handler2" in calls

@pytest.mark.asyncio
async def test_event_ordering(bus: EventBus) -> None:
    calls = []

    async def handler1(event: Event) -> None:
        calls.append("handler1")

    async def handler2(event: Event) -> None:
        calls.append("handler2")

    bus.subscribe("test.action.started", handler1)
    bus.subscribe("test.action.started", handler2)

    event = Event(type="test.action.started")
    await bus.publish(event)

    # Asserting FIFO order based on subscription registration order
    assert calls == ["handler1", "handler2"]

@pytest.mark.asyncio
async def test_exception_isolation(bus: EventBus) -> None:
    calls = []

    async def failing_handler(event: Event) -> None:
        calls.append("failing")
        raise ValueError("Oops!")

    async def succeeding_handler(event: Event) -> None:
        calls.append("succeeding")

    bus.subscribe("test.action.started", failing_handler)
    bus.subscribe("test.action.started", succeeding_handler)

    event = Event(type="test.action.started")
    # This should not raise an error to the caller and should continue execution
    await bus.publish(event)

    assert calls == ["failing", "succeeding"]

def test_invalid_event_type() -> None:
    with pytest.raises(EventValidationError):
        Event(type="invalid_event_type_without_dots")

@pytest.mark.asyncio
async def test_event_cancellation(bus: EventBus) -> None:
    calls = []

    async def cancel_handler(event: Event) -> None:
        calls.append("canceling")
        event.cancel()

    async def after_handler(event: Event) -> None:
        calls.append("after")

    bus.subscribe("test.action.started", cancel_handler)
    bus.subscribe("test.action.started", after_handler)

    event = Event(type="test.action.started")
    await bus.publish(event)

    # the after_handler should not be called because event was cancelled
    assert calls == ["canceling"]
