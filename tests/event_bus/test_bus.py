from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from event_bus.bus import EventBus
from event_bus.models import Event


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.mark.asyncio
async def test_exact_topic_subscription(bus: EventBus) -> None:
    received = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe("test.event.requested", handler)

    e1 = Event(type="test.event.requested")
    e2 = Event(type="other.event.completed")

    await bus.publish(e1)
    await bus.publish(e2)

    assert len(received) == 1
    assert received[0] is e1


@pytest.mark.asyncio
async def test_wildcard_subscription(bus: EventBus) -> None:
    received = []

    async def handler(event: Event) -> None:
        received.append(event.type)

    bus.subscribe("agent.*", handler)
    bus.subscribe("*.completed", handler)

    await bus.publish(Event(type="agent.task.started"))
    await bus.publish(Event(type="tool.execute.completed"))
    await bus.publish(Event(type="system.boot.started")) # Should not match

    assert len(received) == 2
    assert "agent.task.started" in received
    assert "tool.execute.completed" in received


@pytest.mark.asyncio
async def test_priority_sorting(bus: EventBus) -> None:
    order = []

    async def handler_1(e: Event) -> None: order.append(1)
    async def handler_2(e: Event) -> None: order.append(2)
    async def handler_3(e: Event) -> None: order.append(3)

    bus.subscribe("test.action.status", handler_3, priority=300)
    bus.subscribe("test.action.status", handler_1, priority=10)
    bus.subscribe("test.action.status", handler_2, priority=50)

    await bus.publish(Event(type="test.action.status"))

    assert order == [1, 2, 3]


@pytest.mark.asyncio
async def test_sync_handler_support(bus: EventBus) -> None:
    received = False

    def sync_handler(event: Event) -> None:
        nonlocal received
        received = True

    bus.subscribe("test.sync.completed", sync_handler)
    await bus.publish(Event(type="test.sync.completed"))

    assert received is True


@pytest.mark.asyncio
async def test_graceful_error_isolation(bus: EventBus) -> None:
    order = []

    async def failing_handler(e: Event) -> None:
        order.append("fail")
        raise ValueError("Boom!")

    async def success_handler(e: Event) -> None:
        order.append("success")

    bus.subscribe("test.action.status", failing_handler, priority=10)
    bus.subscribe("test.action.status", success_handler, priority=20)

    # This should not raise an exception to the caller
    await bus.publish(Event(type="test.action.status"))

    # Both should run despite the first failing
    assert order == ["fail", "success"]


@pytest.mark.asyncio
async def test_event_cancellation(bus: EventBus) -> None:
    order = []

    async def cancelling_handler(e: Event) -> None:
        order.append("cancel")
        e.cancel()

    async def next_handler(e: Event) -> None:
        order.append("next")

    bus.subscribe("test.action.status", cancelling_handler, priority=10)
    bus.subscribe("test.action.status", next_handler, priority=20)

    await bus.publish(Event(type="test.action.status"))

    # 'next' should never be appended because the event was cancelled
    assert order == ["cancel"]


@pytest.mark.asyncio
async def test_middleware_pipeline(bus: EventBus) -> None:
    trace = []

    async def my_middleware(e: Event, next_call: Callable[[Event], Awaitable[None]]) -> None:
        trace.append("mid_before")
        await next_call(e)
        trace.append("mid_after")

    # Mypy limitation with Protocol matching async functions, so we ignore it here
    bus.use(my_middleware)  # type: ignore

    async def handler(e: Event) -> None:
        trace.append("handler")

    bus.subscribe("test.action.status", handler)

    await bus.publish(Event(type="test.action.status"))

    assert trace == ["mid_before", "handler", "mid_after"]

def test_event_type_validation() -> None:
    from event_bus.models import EventValidationError

    # Valid
    Event(type="domain.action.status")

    # Invalid (missing status)
    with pytest.raises(EventValidationError, match="Must follow DOMAIN.ACTION.STATUS"):
        Event(type="domain.action")

    # Invalid (too many parts)
    with pytest.raises(EventValidationError, match="Must follow DOMAIN.ACTION.STATUS"):
        Event(type="domain.action.status.extra")

    # Invalid characters
    with pytest.raises(EventValidationError, match="Must follow DOMAIN.ACTION.STATUS"):
        Event(type="domain.action-1.status")

@pytest.mark.asyncio
async def test_unsubscribe_exact(bus: EventBus) -> None:
    received = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe("test.action.status", handler)
    await bus.publish(Event(type="test.action.status"))
    assert len(received) == 1

    bus.unsubscribe("test.action.status", handler)
    await bus.publish(Event(type="test.action.status"))
    assert len(received) == 1  # Should not increase


@pytest.mark.asyncio
async def test_unsubscribe_wildcard(bus: EventBus) -> None:
    received = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe("agent.*.started", handler)
    await bus.publish(Event(type="agent.task.started"))
    assert len(received) == 1

    bus.unsubscribe("agent.*.started", handler)
    await bus.publish(Event(type="agent.task.started"))
    assert len(received) == 1  # Should not increase



class HookTestBus(EventBus):
    def __init__(self, trace_list: list[str]) -> None:
        super().__init__()
        self.trace_list = trace_list

    def before_publish(self, event: Event) -> None:
        self.trace_list.append("before_publish")

    def after_publish(self, event: Event) -> None:
        self.trace_list.append("after_publish")

    def before_handler(self, event: Event, handler: Any) -> None:
        self.trace_list.append("before_handler")

    def after_handler(self, event: Event, handler: Any) -> None:
        self.trace_list.append("after_handler")

@pytest.mark.asyncio
async def test_lifecycle_hooks() -> None:
    hooks_fired: list[str] = []
    bus = HookTestBus(hooks_fired)

    async def handler(event: Event) -> None:
        hooks_fired.append("handler")

    bus.subscribe("test.lifecycle.hook", handler)
    await bus.publish(Event(type="test.lifecycle.hook"))

    assert hooks_fired == [
        "before_publish",
        "before_handler",
        "handler",
        "after_handler",
        "after_publish"
    ]
