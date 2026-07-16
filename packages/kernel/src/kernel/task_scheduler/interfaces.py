import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ScheduledTask, TaskContext, TaskResult


class Task:
    async def execute(self, context: "TaskContext") -> "TaskResult":
        raise NotImplementedError()


class Trigger:
    def next_execution(self, last_run: datetime.datetime | None = None) -> datetime.datetime | None:
        raise NotImplementedError()


class TaskQueue:
    async def push(self, task: "ScheduledTask") -> None:
        raise NotImplementedError()

    async def pop(self) -> "ScheduledTask":
        raise NotImplementedError()


class TaskExecutor:
    async def execute(
        self, scheduled_task: "ScheduledTask", context: "TaskContext"
    ) -> "TaskResult":
        raise NotImplementedError()
