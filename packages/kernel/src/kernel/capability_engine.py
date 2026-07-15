"""
Capability Execution Engine Subsystem (Subsystem 11).

Orchestrates the secure, asynchronous execution of tools and capabilities.
Provides a strict middleware pipeline, permission validation, timeout
enforcement, and provider resolution.
"""

import asyncio
import datetime
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from event_bus.bus import EventBus
from event_bus.models import Event

from kernel.agent_runtime import AgentContext, AgentRuntime
from kernel.capability_registry import CapabilityRegistry
from kernel.di import DIContainer
from kernel.lifecycle import HealthReport, KernelSubsystem
from kernel.provider_registry import ProviderRegistry
from kernel.statemanager import StateCategory, StateManager
from kernel.task_scheduler import Task, TaskContext, TaskPriority, TaskScheduler


class CapabilityExecutionState(Enum):
    PENDING = "pending"
    AUTHORIZING = "authorizing"
    RESOLVING = "resolving"
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class CapabilityPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class CapabilityPermission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class CapabilityResultStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"


class CapabilityExecutionError(Exception):
    """Raised when a capability execution fails in the engine pipeline."""

    pass


@dataclass
class CapabilityHealth:
    is_healthy: bool
    details: dict[str, str] = field(default_factory=dict)


@dataclass
class CapabilityMetrics:
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    timeout_count: int = 0
    total_latency_ms: float = 0.0
    average_latency_ms: float = 0.0
    maximum_latency_ms: float = 0.0
    provider_usage: dict[str, int] = field(default_factory=dict)
    capability_usage: dict[str, int] = field(default_factory=dict)


@dataclass
class CapabilityRequest:
    capability_name: str
    agent_id: str
    arguments: dict[str, Any]
    priority: CapabilityPriority = CapabilityPriority.NORMAL
    timeout_seconds: float = 60.0
    max_retries: int = 0


@dataclass
class CapabilityResult:
    status: CapabilityResultStatus
    data: Any = None
    error: Exception | None = None
    latency_ms: float = 0.0


@dataclass
class CapabilityContext:
    request_id: str
    request: CapabilityRequest
    agent_context: AgentContext | None = None
    resolved_provider: str | None = None
    started_at: datetime.datetime | None = None
    is_cancelled: asyncio.Event = field(default_factory=asyncio.Event)
    task_result: CapabilityResult | None = None


@dataclass
class CapabilityExecution:
    execution_id: str
    state: CapabilityExecutionState
    context: CapabilityContext
    result: CapabilityResult | None = None
    task_id: str | None = None
    attempt_count: int = 0
    executor: "CapabilityExecutor | None" = None


@dataclass
class CapabilityHandle:
    execution_id: str
    status_task: asyncio.Task[Any] | None = None


# Protocols
class CapabilityExecutor(Protocol):
    """Protocol for the physical execution of a capability."""

    async def execute(self, context: CapabilityContext) -> CapabilityResult: ...


class CapabilityResolver(Protocol):
    """Protocol for resolving the capability name to an executor."""

    async def resolve(self, capability_name: str) -> CapabilityExecutor: ...


class CapabilityAuthorizer(Protocol):
    """Protocol for validating permissions."""

    async def authorize(self, context: CapabilityContext) -> bool: ...


class CapabilityMiddleware(Protocol):
    """Middleware pipeline hooks."""

    async def before_execute(self, context: CapabilityContext) -> None: ...
    async def after_execute(
        self, context: CapabilityContext, result: CapabilityResult
    ) -> CapabilityResult: ...


class CapabilityPipeline(Protocol):
    """Protocol for the composed execution pipeline."""

    def add_middleware(self, middleware: CapabilityMiddleware) -> None: ...
    async def run(
        self, context: CapabilityContext, executor: CapabilityExecutor
    ) -> CapabilityResult: ...


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


class CapabilityEngine(KernelSubsystem):
    def __init__(
        self,
        di: DIContainer,
        bus: EventBus,
        state: StateManager,
        scheduler: TaskScheduler,
        agent_runtime: AgentRuntime,
        cap_registry: CapabilityRegistry,
        prov_registry: ProviderRegistry,
    ):
        self._di = di
        self._bus = bus
        self._state = state
        self._scheduler = scheduler
        self._agent_runtime = agent_runtime
        self._cap_registry = cap_registry
        self._prov_registry = prov_registry

        self._logger = logging.getLogger("chhaya.capability_engine")

        # Bounded tracking map (O(1) lookups)
        self._active_executions: dict[str, CapabilityExecution] = {}
        self._task_to_exec: dict[str, str] = {}

        self._metrics = CapabilityMetrics()
        self._pipeline = DefaultPipeline()
        self._authorizers: list[CapabilityAuthorizer] = []
        self._resolvers: list[CapabilityResolver] = []

        self._is_running = False

    @property
    def name(self) -> str:
        return "capability_engine"

    @property
    def dependencies(self) -> list[str]:
        return [
            "event_bus",
            "state_manager",
            "task_scheduler",
            "agent_runtime",
            "capability_registry",
            "provider_registry",
        ]

    def ready(self) -> bool:
        return self._is_running

    async def health(self) -> HealthReport:
        running = sum(
            1
            for e in self._active_executions.values()
            if e.state == CapabilityExecutionState.EXECUTING
        )
        queued = sum(
            1
            for e in self._active_executions.values()
            if e.state == CapabilityExecutionState.QUEUED
        )

        details = {
            "running_executions": str(running),
            "queued_executions": str(queued),
            "failures": str(self._metrics.failure_count),
            "retries": str(self._metrics.retry_count),
            "timeouts": str(self._metrics.timeout_count),
            "subsystem_status": "running" if self._is_running else "stopped",
        }

        return HealthReport(is_healthy=self._is_running, details=details)

    async def initialize(self) -> None:
        pass

    async def start(self) -> None:
        self._is_running = True
        self._bus.subscribe("task.execution.completed", self._on_task_completed)
        self._bus.subscribe("task.execution.failed", self._on_task_failed)
        self._bus.subscribe("task.execution.cancelled", self._on_task_cancelled)

    async def stop(self) -> None:
        self._is_running = False
        self._bus.unsubscribe("task.execution.completed", self._on_task_completed)
        self._bus.unsubscribe("task.execution.failed", self._on_task_failed)
        self._bus.unsubscribe("task.execution.cancelled", self._on_task_cancelled)

    async def shutdown(self) -> None:
        await self.stop()
        self._active_executions.clear()
        self._task_to_exec.clear()

    # Configuration
    def add_middleware(self, middleware: CapabilityMiddleware) -> None:
        self._pipeline.add_middleware(middleware)

    def add_authorizer(self, authorizer: CapabilityAuthorizer) -> None:
        self._authorizers.append(authorizer)

    def add_resolver(self, resolver: CapabilityResolver) -> None:
        self._resolvers.append(resolver)

    # Core Execution
    async def submit(self, request: CapabilityRequest) -> str:
        if not self._is_running:
            raise CapabilityExecutionError("CapabilityEngine is not running")

        exec_id = str(uuid.uuid4())
        context = CapabilityContext(request_id=exec_id, request=request)

        execution = CapabilityExecution(
            execution_id=exec_id, state=CapabilityExecutionState.PENDING, context=context
        )

        self._active_executions[exec_id] = execution

        # 1. capability.requested
        await self._transition_and_publish(
            execution, CapabilityExecutionState.PENDING, "capability.execution.requested"
        )

        # Fire-and-forget the orchestrator loop
        asyncio.create_task(self._orchestrate_execution(execution))

        return exec_id

    async def get_execution(self, execution_id: str) -> CapabilityExecution | None:
        return self._active_executions.get(execution_id)

    async def cancel(self, execution_id: str) -> None:
        exec_obj = self._active_executions.get(execution_id)
        if not exec_obj:
            return

        exec_obj.context.is_cancelled.set()

        if exec_obj.task_id:
            await self._scheduler.cancel(exec_obj.task_id)
            # state transition will be handled by the bus callback

    # Pipeline Orchestration
    async def _orchestrate_execution(self, execution: CapabilityExecution) -> None:
        try:
            # 1. Authorization
            await self._transition_and_publish(
                execution, CapabilityExecutionState.AUTHORIZING, None
            )

            # Fetch agent context to validate permissions
            try:
                handle = self._agent_runtime.get_agent(execution.context.request.agent_id)
                execution.context.agent_context = handle.context
            except Exception as e:
                raise CapabilityExecutionError(f"Agent validation failed: {e}")

            allowed = (
                execution.context.request.capability_name
                in execution.context.agent_context.capabilities
            )
            if not allowed:
                raise CapabilityExecutionError("Agent not authorized for this capability")

            for auth in self._authorizers:
                if not await auth.authorize(execution.context):
                    raise CapabilityExecutionError("Middleware authorization failed")

            await self._transition_and_publish(
                execution, CapabilityExecutionState.RESOLVING, "capability.execution.authorized"
            )

            # 2. Resolution
            executor: CapabilityExecutor | None = None
            for res in self._resolvers:
                try:
                    executor = await res.resolve(execution.context.request.capability_name)
                    if executor:
                        break
                except Exception:
                    continue

            if not executor:
                raise CapabilityExecutionError(
                    f"Capability '{execution.context.request.capability_name}' not resolved"
                )

            if execution.context.resolved_provider:
                await self._bus.publish(
                    Event(
                        type="capability.provider.selected",
                        payload={
                            "execution_id": execution.execution_id,
                            "provider": execution.context.resolved_provider,
                        },
                    )
                )

            execution.executor = executor
            # Proceed to execution phase
            await self._execute_resolved(execution)

        except Exception as e:
            execution.result = CapabilityResult(status=CapabilityResultStatus.ERROR, error=e)
            await self._handle_failure(execution)

    async def _execute_resolved(self, execution: CapabilityExecution) -> None:
        try:
            executor = execution.executor
            if not executor:
                raise CapabilityExecutionError("No executor bound for execution")

            # 3. Queue to TaskScheduler
            await self._transition_and_publish(execution, CapabilityExecutionState.QUEUED, None)

            tp = TaskPriority.NORMAL
            if execution.context.request.priority == CapabilityPriority.LOW:
                tp = TaskPriority.LOW
            elif execution.context.request.priority == CapabilityPriority.HIGH:
                tp = TaskPriority.HIGH
            elif execution.context.request.priority == CapabilityPriority.CRITICAL:
                tp = TaskPriority.CRITICAL

            task = _CapabilityTask(execution.context, executor, self._pipeline)

            # Cleanup old task_id mapping if this is a retry
            if execution.task_id and execution.task_id in self._task_to_exec:
                del self._task_to_exec[execution.task_id]

            task_id = await self._scheduler.submit(
                task=task,
                priority=tp,
                timeout_seconds=execution.context.request.timeout_seconds,
            )

            execution.task_id = task_id
            self._task_to_exec[task_id] = execution.execution_id

            # 4. Start Event (only emit on first attempt to avoid duplicates)
            if execution.attempt_count == 0:
                execution.context.started_at = datetime.datetime.now(datetime.UTC)
                await self._transition_and_publish(
                    execution, CapabilityExecutionState.EXECUTING, "capability.execution.started"
                )
            else:
                await self._transition_and_publish(
                    execution, CapabilityExecutionState.EXECUTING, None
                )
        except Exception as e:
            # We catch errors during retry submission here
            execution.result = CapabilityResult(status=CapabilityResultStatus.ERROR, error=e)
            await self._transition_and_publish(
                execution, CapabilityExecutionState.FAILED, "capability.execution.failed"
            )
            await self._bus.publish(
                Event(
                    type="capability.execution.finished",
                    payload={"execution_id": execution.execution_id},
                )
            )
            self._cleanup_execution(execution)

    # Event Handlers
    async def _on_task_completed(self, e: Event) -> None:
        task_id = e.payload.get("task_id")
        if not task_id or task_id not in self._task_to_exec:
            return

        exec_id = self._task_to_exec[task_id]
        execution = self._active_executions.get(exec_id)
        if not execution:
            return

        # Resolve success from shared context if set; otherwise, fallback to generic SUCCESS.
        execution.result = execution.context.task_result or CapabilityResult(
            status=CapabilityResultStatus.SUCCESS
        )
        await self._handle_success(execution)

    async def _on_task_failed(self, e: Event) -> None:
        task_id = e.payload.get("task_id")
        if not task_id or task_id not in self._task_to_exec:
            return

        exec_id = self._task_to_exec[task_id]
        execution = self._active_executions.get(exec_id)
        if not execution:
            return

        # Check if it was a timeout
        error_msg = e.payload.get("error", "")
        if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            execution.result = CapabilityResult(
                status=CapabilityResultStatus.ERROR, error=TimeoutError("Capability timed out")
            )
            self._metrics.timeout_count += 1
        else:
            execution.result = CapabilityResult(
                status=CapabilityResultStatus.ERROR, error=Exception(error_msg)
            )

        await self._handle_failure(execution)

    async def _on_task_cancelled(self, e: Event) -> None:
        task_id = e.payload.get("task_id")
        if not task_id or task_id not in self._task_to_exec:
            return

        exec_id = self._task_to_exec[task_id]
        execution = self._active_executions.get(exec_id)
        if not execution:
            return

        execution.result = CapabilityResult(
            status=CapabilityResultStatus.ERROR, error=Exception("Task cancelled explicitly")
        )
        await self._transition_and_publish(
            execution, CapabilityExecutionState.CANCELLED, "capability.execution.cancelled"
        )
        await self._bus.publish(
            Event(
                type="capability.execution.finished",
                payload={"execution_id": execution.execution_id},
            )
        )
        self._cleanup_execution(execution)

    # Resolution Helpers
    async def _handle_success(self, execution: CapabilityExecution) -> None:
        self._metrics.success_count += 1
        self._update_metrics(execution)
        await self._transition_and_publish(
            execution, CapabilityExecutionState.COMPLETED, "capability.execution.completed"
        )
        await self._bus.publish(
            Event(
                type="capability.execution.finished",
                payload={"execution_id": execution.execution_id},
            )
        )
        self._cleanup_execution(execution)

    async def _handle_failure(self, execution: CapabilityExecution) -> None:
        execution.attempt_count += 1
        if execution.attempt_count <= execution.context.request.max_retries:
            self._metrics.retry_count += 1
            # Check if the failure was a timeout
            is_timeout = execution.result and isinstance(execution.result.error, TimeoutError)
            event_type = (
                "capability.execution.timeout" if is_timeout else "capability.execution.retry"
            )
            state = (
                CapabilityExecutionState.TIMEOUT if is_timeout else CapabilityExecutionState.PENDING
            )
            await self._transition_and_publish(execution, state, event_type)
            # Resubmit
            asyncio.create_task(self._execute_resolved(execution))
            return

        is_timeout = execution.result and isinstance(execution.result.error, TimeoutError)
        if is_timeout:
            self._update_metrics(execution)
            await self._transition_and_publish(
                execution, CapabilityExecutionState.TIMEOUT, "capability.execution.timeout"
            )
        else:
            self._metrics.failure_count += 1
            self._update_metrics(execution)
            await self._transition_and_publish(
                execution, CapabilityExecutionState.FAILED, "capability.execution.failed"
            )

        await self._bus.publish(
            Event(
                type="capability.execution.finished",
                payload={"execution_id": execution.execution_id},
            )
        )
        self._cleanup_execution(execution)

    def _update_metrics(self, execution: CapabilityExecution) -> None:
        self._metrics.execution_count += 1
        cap_name = execution.context.request.capability_name
        self._metrics.capability_usage[cap_name] = (
            self._metrics.capability_usage.get(cap_name, 0) + 1
        )

        if execution.context.resolved_provider:
            prov = execution.context.resolved_provider
            self._metrics.provider_usage[prov] = self._metrics.provider_usage.get(prov, 0) + 1

        if execution.result and execution.result.latency_ms > 0:
            lat = execution.result.latency_ms
            self._metrics.total_latency_ms += lat
            self._metrics.maximum_latency_ms = max(self._metrics.maximum_latency_ms, lat)
            self._metrics.average_latency_ms = (
                self._metrics.total_latency_ms / self._metrics.execution_count
            )

    def _cleanup_execution(self, execution: CapabilityExecution) -> None:
        if execution.task_id and execution.task_id in self._task_to_exec:
            del self._task_to_exec[execution.task_id]
        if execution.execution_id in self._active_executions:
            del self._active_executions[execution.execution_id]

    async def _transition_and_publish(
        self,
        execution: CapabilityExecution,
        new_state: CapabilityExecutionState,
        event_type: str | None,
    ) -> None:
        execution.state = new_state

        # Persist state
        try:
            await self._state.set_state(
                StateCategory.CAPABILITY,
                execution.execution_id,
                {
                    "id": execution.execution_id,
                    "state": new_state.value,
                    "capability": execution.context.request.capability_name,
                    "agent_id": execution.context.request.agent_id,
                },
            )
        except Exception as e:
            self._logger.error(f"Failed to persist capability execution state: {e}")

        if event_type:
            payload = {
                "execution_id": execution.execution_id,
                "capability": execution.context.request.capability_name,
            }
            if execution.result and execution.result.error:
                payload["error"] = str(execution.result.error)
            await self._bus.publish(Event(type=event_type, payload=payload))
