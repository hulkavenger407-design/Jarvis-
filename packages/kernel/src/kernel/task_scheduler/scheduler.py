import asyncio
import datetime
import logging
import uuid
from typing import Any

from event_bus.bus import EventBus
from event_bus.models import Event

from kernel.di import DIContainer
from kernel.lifecycle import HealthReport, KernelSubsystem
from kernel.statemanager import StateManager

from .errors import TaskSchedulerError
from .interfaces import Task, TaskExecutor, TaskQueue, Trigger
from .models import (
    RetryPolicy,
    ScheduledTask,
    TaskContext,
    TaskPriority,
    TaskResult,
    TaskState,
)
from .triggers import OneShotTrigger


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
        except asyncio.CancelledError:
            return TaskResult(success=False, error=Exception("Task cancelled explicitly"))
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
            task = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            if task.id in self._items:
                del self._items[task.id]
                return task
            self._queue.task_done()


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
        self._completed: dict[str, bool] = {}
        self._cancelled: dict[str, bool] = {}
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
        tasks_to_gather = list(self._workers)
        if hasattr(self, "_promoter"):
            tasks_to_gather.append(self._promoter)
        await asyncio.gather(*tasks_to_gather, return_exceptions=True)

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
        self._cancelled[task_id] = True
        if len(self._cancelled) > 10000:
            del self._cancelled[next(iter(self._cancelled))]
        if task_id in self._waiting:
            del self._waiting[task_id]
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
                self._completed[scheduled.id] = True
                if len(self._completed) > 10000:
                    del self._completed[next(iter(self._completed))]
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
                    if len(self._dlq) > 10000:
                        del self._dlq[next(iter(self._dlq))]
                    await self._bus.publish(
                        Event(
                            type="task.execution.failed",
                            payload={
                                "task_id": scheduled.id,
                                "error": str(result.error) if result and result.error else "",
                            },
                        )
                    )
