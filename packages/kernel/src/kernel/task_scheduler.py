"""
Task Scheduler Subsystem.

Provides distributed-ready background task scheduling, retries,
dead letter queues (DLQ), priorities, and cron jobs.
"""

import asyncio
import datetime
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from croniter import croniter
from event_bus.bus import EventBus
from event_bus.models import Event

from kernel.di import DIContainer
from kernel.lifecycle import HealthReport, KernelSubsystem
from kernel.state_manager import StateManager


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_strategy: str = "exponential"
    base_delay_seconds: float = 1.0


@dataclass
class TaskContext:
    task_id: str
    attempt: int
    di: DIContainer
    bus: EventBus
    state: StateManager
    is_cancelled: asyncio.Event


@dataclass
class TaskResult:
    success: bool
    data: Any = None
    error: Exception | None = None


class Task:
    async def execute(self, context: TaskContext) -> TaskResult:
        raise NotImplementedError()


class Trigger:
    def next_execution(self, last_run: datetime.datetime | None = None) -> datetime.datetime | None:
        raise NotImplementedError()


class OneShotTrigger(Trigger):
    def next_execution(self, last_run: datetime.datetime | None = None) -> datetime.datetime | None:
        return None if last_run else datetime.datetime.now(datetime.UTC)


class IntervalTrigger(Trigger):
    def __init__(self, interval_seconds: float):
        self.interval = datetime.timedelta(seconds=interval_seconds)

    def next_execution(self, last_run: datetime.datetime | None = None) -> datetime.datetime | None:
        now = datetime.datetime.now(datetime.UTC)
        if not last_run:
            return now
        # strictly interval from now if not running for a while, or from last_run?
        return now + self.interval


class CronTrigger(Trigger):
    def __init__(self, cron_expr: str):
        self.cron_expr = cron_expr

    def next_execution(self, last_run: datetime.datetime | None = None) -> datetime.datetime | None:
        now = datetime.datetime.now(datetime.UTC)
        base = last_run or now
        iter = croniter(self.cron_expr, base)
        return iter.get_next(datetime.datetime)


class TaskSchedulerError(Exception):
    pass


@dataclass
class ScheduledTask:
    id: str
    task: Task
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskState = TaskState.PENDING
    trigger: Trigger | None = None
    retry_policy: RetryPolicy | None = None
    dependencies: list[str] = field(default_factory=list)
    timeout_seconds: float = 3600.0

    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    next_run_time: datetime.datetime | None = None
    last_run_time: datetime.datetime | None = None
    attempt_count: int = 0

    def __lt__(self, other: "ScheduledTask") -> bool:
        # Higher priority runs first
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        # Earlier next_run_time runs first
        t1 = self.next_run_time or self.created_at
        t2 = other.next_run_time or other.created_at
        return t1 < t2


class TaskQueue:
    async def push(self, task: ScheduledTask) -> None:
        raise NotImplementedError()

    async def pop(self) -> ScheduledTask:
        raise NotImplementedError()


class TaskExecutor:
    async def execute(self, scheduled_task: ScheduledTask, context: TaskContext) -> TaskResult:
        raise NotImplementedError()


class DefaultTaskExecutor(TaskExecutor):
    async def execute(self, scheduled_task: ScheduledTask, context: TaskContext) -> TaskResult:
        try:
            result = await asyncio.wait_for(
                scheduled_task.task.execute(context), timeout=scheduled_task.timeout_seconds
            )
            if not isinstance(result, TaskResult):
                return TaskResult(success=True, data=result)
            return result
        except TimeoutError:
            return TaskResult(success=False, error=TaskSchedulerError("Task timed out"))
        except TimeoutError:
            return TaskResult(success=False, error=TaskSchedulerError("Task timed out"))
        except Exception as e:
            return TaskResult(success=False, error=e)


class InMemoryTaskQueue(TaskQueue):
    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[ScheduledTask] = asyncio.PriorityQueue()
        self._items: dict[str, ScheduledTask] = {}

    async def push(self, task: ScheduledTask) -> None:
        self._items[task.id] = task
        await self._queue.put(task)

    async def pop(self) -> ScheduledTask:
        while True:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                if task.id in self._items:
                    del self._items[task.id]
                    return task
                self._queue.task_done()
            except Exception as e:
                if isinstance(e, TimeoutError) or type(e).__name__ == "TimeoutError":
                    raise TimeoutError()
                raise


class TaskScheduler(KernelSubsystem):
    @property
    def name(self) -> str:
        return "task_scheduler"

    @property
    def dependencies(self) -> list[str]:
        return []

    def ready(self) -> bool:
        return self._is_running

    async def health(self) -> HealthReport:
        return HealthReport(is_healthy=True, details={"status": "ok"})

    async def shutdown(self) -> None:
        await self.stop()

    def __init__(self, di: DIContainer, bus: EventBus, state: StateManager, worker_count: int = 4):
        self._di = di
        self._bus = bus
        self._state = state
        self._worker_count = worker_count
        self._logger = logging.getLogger("chhaya.scheduler")
        self._queue = InMemoryTaskQueue()

        self._is_running = False
        self._is_paused = False
        self._workers: list[asyncio.Task[Any]] = []

        self._active_tasks: dict[str, ScheduledTask] = {}
        self._waiting: dict[str, ScheduledTask] = {}
        self._completed: set[str] = set()
        self._cancelled: set[str] = set()
        self._dlq: dict[str, ScheduledTask] = {}

        self._cancellation_events: dict[str, asyncio.Event] = {}

    async def initialize(self) -> None:
        pass

    async def start(self) -> None:
        self._is_running = True
        self._is_paused = False
        for i in range(self._worker_count):
            w = asyncio.create_task(self._worker_loop(i))
            self._workers.append(w)
        self._promoter = asyncio.create_task(self._promotion_loop())

    async def stop(self) -> None:
        self._is_running = False
        if hasattr(self, "_promoter"):
            self._promoter.cancel()
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

    def pause(self) -> None:
        self._is_paused = True

    def resume(self) -> None:
        self._is_paused = False

    async def submit(
        self,
        task: Task,
        priority: TaskPriority = TaskPriority.NORMAL,
        trigger: Trigger | None = None,
        retry_policy: RetryPolicy | None = None,
        dependencies: list[str] | None = None,
        timeout_seconds: float = 3600.0,
    ) -> str:
        tid = str(uuid.uuid4())
        scheduled = ScheduledTask(
            id=tid,
            task=task,
            priority=priority,
            trigger=trigger or OneShotTrigger(),
            retry_policy=retry_policy,
            dependencies=dependencies or [],
            timeout_seconds=timeout_seconds,
        )
        scheduled.next_run_time = (
            scheduled.trigger.next_execution(None) if scheduled.trigger else None
        )

        if scheduled.dependencies:
            self._waiting[tid] = scheduled
        else:
            await self._queue.push(scheduled)

        await self._bus.publish(Event(type="task.created.completed", payload={"task_id": tid}))
        return tid

    async def cancel(self, task_id: str) -> None:
        self._cancelled.add(task_id)
        if task_id in self._cancellation_events:
            self._cancellation_events[task_id].set()
        await self._bus.publish(
            Event(type="task.execution.cancelled", payload={"task_id": task_id})
        )

    async def _promotion_loop(self) -> None:
        while self._is_running:
            try:
                if self._is_paused:
                    await asyncio.sleep(0.05)
                    continue

                promoted = []
                for tid, task in list(self._waiting.items()):
                    if all(dep in self._completed for dep in task.dependencies):
                        task.status = TaskState.PENDING
                        promoted.append(task)
                        del self._waiting[tid]

                for task in promoted:
                    await self._queue.push(task)

            except Exception as e:
                self._logger.error(f"Error in promotion loop: {e}")

            await asyncio.sleep(0.05)

    async def _worker_loop(self, worker_id: int) -> None:
        executor = DefaultTaskExecutor()
        while self._is_running:
            if self._is_paused:
                await asyncio.sleep(0.05)
                continue

            try:
                scheduled = await self._queue.pop()
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            if scheduled.id in self._cancelled:
                continue

            now = datetime.datetime.now(datetime.UTC)
            if scheduled.next_run_time and scheduled.next_run_time > now:
                await self._queue.push(scheduled)
                await asyncio.sleep(0.05)
                continue

            scheduled.status = TaskState.RUNNING
            self._active_tasks[scheduled.id] = scheduled
            cancel_event = asyncio.Event()
            self._cancellation_events[scheduled.id] = cancel_event

            await self._bus.publish(
                Event(type="task.execution.started", payload={"task_id": scheduled.id})
            )

            ctx = TaskContext(
                task_id=scheduled.id,
                attempt=scheduled.attempt_count + 1,
                di=self._di,
                bus=self._bus,
                state=self._state,
                is_cancelled=cancel_event,
            )

            result = await executor.execute(scheduled, ctx)

            del self._active_tasks[scheduled.id]
            del self._cancellation_events[scheduled.id]

            if scheduled.id in self._cancelled:
                continue

            scheduled.attempt_count += 1
            scheduled.last_run_time = datetime.datetime.now(datetime.UTC)

            if result.success:
                scheduled.status = TaskState.COMPLETED
                self._completed.add(scheduled.id)
                await self._bus.publish(
                    Event(type="task.execution.completed", payload={"task_id": scheduled.id})
                )

                if scheduled.trigger:
                    next_time = scheduled.trigger.next_execution(scheduled.last_run_time)
                    if next_time:
                        scheduled.next_run_time = next_time
                        scheduled.status = TaskState.PENDING
                        scheduled.attempt_count = 0
                        await self._queue.push(scheduled)
            else:
                retry_allowed = False
                if scheduled.retry_policy:
                    # attempt_count incremented above. If max_attempts=3, attempt is 1
                    # It means we can retry if attempt_count < max_attempts.
                    if scheduled.attempt_count < scheduled.retry_policy.max_attempts:
                        retry_allowed = True

                if retry_allowed:
                    # calculate backoff
                    policy = scheduled.retry_policy
                    if policy and policy.backoff_strategy == "linear":
                        delay = (
                            policy.base_delay_seconds * scheduled.attempt_count if policy else 0.0
                        )
                    else:  # exponential
                        delay = (
                            policy.base_delay_seconds * (2 ** (scheduled.attempt_count - 1))
                            if policy
                            else 0.0
                        )

                    scheduled.next_run_time = datetime.datetime.now(
                        datetime.UTC
                    ) + datetime.timedelta(seconds=delay)
                    scheduled.status = TaskState.PENDING
                    await self._queue.push(scheduled)
                else:
                    scheduled.status = TaskState.FAILED
                    self._dlq[scheduled.id] = scheduled
                    await self._bus.publish(
                        Event(type="task.execution.failed", payload={"task_id": scheduled.id})
                    )
