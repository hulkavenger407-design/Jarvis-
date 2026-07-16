import asyncio
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from event_bus.bus import EventBus

from kernel.di import DIContainer
from kernel.statemanager import StateManager

from .interfaces import Task, Trigger


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
