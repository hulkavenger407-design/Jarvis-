import asyncio
import datetime
from collections.abc import AsyncGenerator

import pytest
from event_bus.bus import EventBus
from event_bus.models import Event
from kernel.di import DIContainer
from kernel.state_manager import StateManager
from kernel.task_scheduler import (
    CronTrigger,
    IntervalTrigger,
    OneShotTrigger,
    RetryPolicy,
    Task,
    TaskContext,
    TaskPriority,
    TaskResult,
    TaskScheduler,
)


class DummyTask(Task):
    def __init__(self, succeed: bool = True, sleep: float = 0.0) -> None:
        self.succeed = succeed
        self.sleep = sleep
        self.executions = 0
        self.context: TaskContext | None = None

    async def execute(self, context: TaskContext) -> TaskResult:
        self.executions += 1
        self.context = context
        if self.sleep > 0:
            await asyncio.sleep(self.sleep)
        if self.succeed:
            return TaskResult(success=True)
        return TaskResult(success=False, error=Exception("Failed"))


@pytest.fixture
def di() -> DIContainer:
    return DIContainer()


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def state(bus: EventBus) -> StateManager:
    return StateManager(bus)


@pytest.fixture
async def scheduler(
    di: DIContainer, bus: EventBus, state: StateManager
) -> AsyncGenerator[TaskScheduler, None]:
    scheduler = TaskScheduler(di, bus, state, worker_count=2)
    await scheduler.initialize()
    await scheduler.start()
    yield scheduler
    await scheduler.stop()


@pytest.mark.asyncio
async def test_simple_task_execution(scheduler: TaskScheduler) -> None:
    task = DummyTask()
    task_id = await scheduler.submit(task)

    # Wait for execution
    await asyncio.sleep(0.1)

    assert task.executions == 1
    assert task.context is not None
    assert task.context.task_id == task_id


@pytest.mark.asyncio
async def test_priority_ordering(scheduler: TaskScheduler) -> None:
    # Pause scheduler to fill queue
    scheduler.pause()

    order = []

    class TrackedTask(Task):
        def __init__(self, name: str) -> None:
            self.name = name

        async def execute(self, ctx: TaskContext) -> TaskResult:
            order.append(self.name)
            return TaskResult(success=True)

    await scheduler.submit(TrackedTask("low"), priority=TaskPriority.LOW)
    await scheduler.submit(TrackedTask("critical"), priority=TaskPriority.CRITICAL)
    await scheduler.submit(TrackedTask("high"), priority=TaskPriority.HIGH)

    # Resume and allow execution
    scheduler.resume()
    await asyncio.sleep(0.1)

    assert order == ["critical", "high", "low"]


@pytest.mark.asyncio
async def test_dependency_graph(scheduler: TaskScheduler) -> None:
    t_a = DummyTask()
    t_b = DummyTask()

    id_a = await scheduler.submit(t_a)
    await scheduler.submit(t_b, dependencies=[id_a])

    await asyncio.sleep(0.2)

    assert t_a.executions == 1
    assert t_b.executions == 1


@pytest.mark.asyncio
async def test_retry_and_dlq(scheduler: TaskScheduler) -> None:
    task = DummyTask(succeed=False)

    # Fast retry policy
    policy = RetryPolicy(max_attempts=3, backoff_strategy="linear", base_delay_seconds=0.01)

    task_id = await scheduler.submit(task, retry_policy=policy)

    # Wait enough time for 3 total attempts
    await asyncio.sleep(0.2)

    assert task.executions == 3
    assert len(scheduler._dlq) == 1
    assert task_id in scheduler._dlq


@pytest.mark.asyncio
async def test_timeout_cancellation(scheduler: TaskScheduler) -> None:
    task = DummyTask(sleep=1.0)
    # Timeout before sleep finishes
    await scheduler.submit(task, timeout_seconds=0.1, retry_policy=RetryPolicy(max_attempts=1))

    await asyncio.sleep(0.3)

    assert task.executions == 1  # First attempt fired
    assert len(scheduler._dlq) == 1  # Failed due to timeout


@pytest.mark.asyncio
async def test_triggers_and_events(scheduler: TaskScheduler, bus: EventBus) -> None:
    events = []

    async def capture(e: Event) -> None:
        events.append(e.type)

    bus.subscribe("task.*", capture)

    task = DummyTask()
    # Execute immediately
    await scheduler.submit(task, trigger=OneShotTrigger())

    await asyncio.sleep(0.1)

    assert "task.created.completed" in events
    assert "task.execution.started" in events
    assert "task.execution.completed" in events


@pytest.mark.asyncio
async def test_interval_trigger(scheduler: TaskScheduler) -> None:
    task = DummyTask()
    # 0.1s interval
    await scheduler.submit(task, trigger=IntervalTrigger(0.1))

    await asyncio.sleep(0.35)  # Should run at 0, 0.1, 0.2, 0.3

    assert task.executions >= 3


@pytest.mark.asyncio
async def test_cron_trigger(scheduler: TaskScheduler) -> None:
    task = DummyTask()
    trigger = CronTrigger("* * * * *")  # Every minute

    now = datetime.datetime.now(datetime.UTC)
    next_time = trigger.next_execution(now)
    assert next_time is not None
    assert next_time > now

    # Check that manual firing doesn't break
    await scheduler.submit(task, trigger=trigger)
