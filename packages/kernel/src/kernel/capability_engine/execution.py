import asyncio
import datetime
from typing import Any

from kernel.capability_engine.errors import CapabilityExecutionError
from kernel.capability_engine.interfaces import (
    CapabilityExecutor,
    CapabilityMiddleware,
    CapabilityPipeline,
)
from kernel.capability_engine.models import (
    CapabilityContext,
    CapabilityResult,
    CapabilityResultStatus,
)
from kernel.task_scheduler import Task, TaskContext


class DefaultPipeline(CapabilityPipeline):
    def __init__(self) -> None:
        self._middlewares: list[CapabilityMiddleware] = []

    def add_middleware(self, middleware: CapabilityMiddleware) -> None:
        self._middlewares.append(middleware)

    async def run(
        self, context: CapabilityContext, executor: CapabilityExecutor
    ) -> CapabilityResult:
        for mw in self._middlewares:
            await mw.before_execute(context)

        result = await executor.execute(context)

        for mw in reversed(self._middlewares):
            result = await mw.after_execute(context, result)

        return result


class _CapabilityTask(Task):
    """Adapter bridging CapabilityExecution to the TaskScheduler."""

    def __init__(
        self, context: CapabilityContext, executor: CapabilityExecutor, pipeline: CapabilityPipeline
    ):
        self._ctx = context
        self._executor = executor
        self._pipeline = pipeline

    async def execute(self, ctx: TaskContext) -> Any:
        if self._ctx.is_cancelled.is_set():
            raise asyncio.CancelledError()

        # Tie the scheduler cancellation to our context
        async def _sync_cancel() -> None:
            await ctx.is_cancelled.wait()
            self._ctx.is_cancelled.set()

        sync_task = asyncio.create_task(_sync_cancel())

        try:
            start_time = datetime.datetime.now(datetime.UTC)
            res = await self._pipeline.run(self._ctx, self._executor)
            end_time = datetime.datetime.now(datetime.UTC)
            res.latency_ms = (end_time - start_time).total_seconds() * 1000
            self._ctx.task_result = res

            if res.status == CapabilityResultStatus.ERROR:
                if res.error:
                    raise res.error
                raise CapabilityExecutionError("Execution failed")
            return res
        except asyncio.CancelledError:
            # Re-raise to let the scheduler handle cancellation cleanly
            raise
        except Exception as e:
            self._ctx.task_result = CapabilityResult(status=CapabilityResultStatus.ERROR, error=e)
            raise
        finally:
            sync_task.cancel()
