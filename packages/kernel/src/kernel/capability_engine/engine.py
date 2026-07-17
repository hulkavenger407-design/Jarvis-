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
from typing import Any

from event_bus.bus import EventBus
from event_bus.models import Event

from kernel.agent_runtime import AgentRuntime
from kernel.capability_engine.errors import CapabilityExecutionError
from kernel.capability_engine.execution import DefaultPipeline, _CapabilityTask
from kernel.capability_engine.interfaces import (
    CapabilityExecutor,
    CapabilityMiddleware,
    CapabilityResolver,
)
from kernel.capability_engine.models import (
    CapabilityContext,
    CapabilityExecution,
    CapabilityExecutionState,
    CapabilityMetrics,
    CapabilityPriority,
    CapabilityRequest,
    CapabilityResult,
    CapabilityResultStatus,
)
from kernel.capability_engine.permissions import CapabilityAuthorizer
from kernel.capability_registry import CapabilityRegistry
from kernel.di import DIContainer
from kernel.interfaces import ICapabilityEngine
from kernel.lifecycle import HealthReport, KernelSubsystem
from kernel.provider_registry import ProviderRegistry
from kernel.statemanager import StateCategory, StateManager
from kernel.task_scheduler import TaskPriority, TaskScheduler


class CapabilityEngine(KernelSubsystem, ICapabilityEngine):
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

    # ICapabilityEngine (Frozen Interface)
    async def invoke(
        self, capability_id: str, security_context: Any, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Implementation of frozen ICapabilityEngine interface.
        Maps the capability execution to the internal submit and waits for the result.
        """
        agent_id = "anonymous"
        if isinstance(security_context, dict):
            agent_id = security_context.get("agent_id", "anonymous")

        request = CapabilityRequest(
            capability_name=capability_id,
            agent_id=agent_id,
            arguments=payload
        )

        exec_id = await self.submit(request)

        # Wait for the execution to finish
        execution = self._active_executions.get(exec_id)
        if not execution:
            raise CapabilityExecutionError(f"Failed to submit execution for {capability_id}")

        while execution.state not in {
            CapabilityExecutionState.COMPLETED,
            CapabilityExecutionState.FAILED,
            CapabilityExecutionState.CANCELLED,
            CapabilityExecutionState.TIMEOUT,
        }:
            await asyncio.sleep(0.1)

        if not execution or not execution.result:
            raise CapabilityExecutionError("Execution completed with no result")

        if execution.result.status == CapabilityResultStatus.ERROR:
            if execution.result.error:
                raise execution.result.error
            raise CapabilityExecutionError("Execution failed")

        return execution.result.data if execution.result.data is not None else {}

    async def get_status(self, execution_id: str) -> str:
        """
        Implementation of frozen ICapabilityEngine interface.
        Returns the string value of the execution state.
        """
        execution = await self.get_execution(execution_id)
        if execution:
            return execution.state.value

        # Fallback to querying state manager for persisted state if not in memory.
        try:
            persisted = await self._state.get_state(StateCategory.CAPABILITY, execution_id)
            if persisted and "state" in persisted:
                return str(persisted["state"])
        except Exception:
            pass

        return "unknown"

    # Core Execution (Backward Compatibility)
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
                handle = await self._agent_runtime.get_agent(execution.context.request.agent_id)
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
                        version="1.0",
                        payload={
                            "execution_id": execution.execution_id,
                            "provider": execution.context.resolved_provider,
                        },
                        id=str(uuid.uuid4()),
                        timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
                        source="capability_engine",
                        session_id=None
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
                    version="1.0",
                    payload={"execution_id": execution.execution_id},
                    id=str(uuid.uuid4()),
                    timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
                    source="capability_engine",
                    session_id=None
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
                version="1.0",
                payload={"execution_id": execution.execution_id},
                id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
                source="capability_engine",
                session_id=None
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
                version="1.0",
                payload={"execution_id": execution.execution_id},
                id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
                source="capability_engine",
                session_id=None
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
                version="1.0",
                payload={"execution_id": execution.execution_id},
                id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
                source="capability_engine",
                session_id=None
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
            await self._bus.publish(
                Event(
                    type=event_type,
                    version="1.0",
                    payload=payload,
                    id=str(uuid.uuid4()),
                    timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
                    source="capability_engine",
                    session_id=None
                )
            )
