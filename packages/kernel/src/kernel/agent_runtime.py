"""
Agent Runtime (Agent Manager) Subsystem.

Provides the isolated environment, state machine, lifecycle management,
and concurrency orchestration for executing independent AI agents.
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

from kernel.capability_registry import CapabilityRegistry
from kernel.di import DIContainer
from kernel.lifecycle import HealthReport, KernelSubsystem
from kernel.provider_registry import ProviderRegistry
from kernel.state_manager import StateCategory, StateManager
from kernel.task_scheduler import Task, TaskContext, TaskPriority, TaskScheduler


class AgentState(Enum):
    CREATED = "created"
    INITIALIZED = "initialized"
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    AWAITING_INPUT = "awaiting_input"
    SLEEPING = "sleeping"
    SUSPENDED = "suspended"
    FAULTED = "faulted"
    TERMINATED = "terminated"


class AgentPriority(Enum):
    BACKGROUND = 0
    NORMAL = 1
    HIGH = 2
    REALTIME = 3


class AgentRuntimeError(Exception):
    """Raised when an error occurs within the Agent Runtime."""


@dataclass
class AgentHealth:
    is_healthy: bool
    state: AgentState
    last_error: Exception | None = None
    last_ping: datetime.datetime | None = None


@dataclass
class AgentMetrics:
    total_executions: int = 0
    total_failures: int = 0
    total_time_ms: float = 0.0
    capabilities_used: dict[str, int] = field(default_factory=dict)
    tokens_consumed: int = 0


@dataclass
class AgentContext:
    agent_id: str
    metadata: dict[str, Any]
    capabilities: list[str]  # List of allowed capability names
    di: DIContainer
    state_manager: StateManager
    event_bus: EventBus
    provider_registry: ProviderRegistry
    capability_registry: CapabilityRegistry

    # Execution bounds
    memory_limit_mb: int = 512
    max_history_turns: int = 100
    timeout_seconds: float = 300.0

    is_cancelled: asyncio.Event = field(default_factory=asyncio.Event)


@dataclass
class AgentResult:
    success: bool
    data: Any = None
    error: Exception | None = None


@dataclass
class AgentExecution:
    execution_id: str
    agent_id: str
    started_at: datetime.datetime
    finished_at: datetime.datetime | None = None
    result: AgentResult | None = None
    task_id: str | None = None


@dataclass
class AgentHandle:
    id: str
    name: str
    state: AgentState
    priority: AgentPriority
    health: AgentHealth
    metrics: AgentMetrics
    context: AgentContext


class Agent(Protocol):
    """The core interface an agent implementation must fulfill."""

    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...

    async def initialize(self, context: AgentContext) -> None:
        """Sets up the agent resources."""
        ...

    async def step(self, context: AgentContext) -> AgentResult:
        """Executes a single step of the agent's logic."""
        ...

    async def cleanup(self) -> None:
        """Cleans up agent resources."""
        ...


class AgentFactory(Protocol):
    """Factory interface for instantiating agents dynamically."""

    async def create(self, name: str, config: dict[str, Any]) -> Agent: ...


class AgentRepository(Protocol):
    """Storage interface for persisting agent handles and state across reboots."""

    async def save(self, handle: AgentHandle) -> None: ...
    async def load(self, agent_id: str) -> AgentHandle | None: ...
    async def list_all(self) -> list[AgentHandle]: ...
    async def delete(self, agent_id: str) -> None: ...


class AgentExecutor(Protocol):
    """Abstraction for how an agent's step is executed."""

    async def execute(self, agent: Agent, context: AgentContext) -> AgentResult: ...


class _AgentTask(Task):
    """Adapter bridging the Agent interface to the TaskScheduler."""

    def __init__(self, agent: Agent, agent_context: AgentContext):
        self.agent = agent
        self.agent_context = agent_context

    async def execute(self, ctx: TaskContext) -> Any:
        # Map task context cancellation to agent context
        self.agent_context.is_cancelled = ctx.is_cancelled

        res = await self.agent.step(self.agent_context)
        if not res.success:
            if res.error:
                raise res.error
            raise Exception("Agent step failed")
        return res


class AgentRuntime(KernelSubsystem):
    """
    Manages the lifecycle, isolation, and execution of autonomous agents.
    """

    def __init__(
        self,
        di: DIContainer,
        bus: EventBus,
        state: StateManager,
        scheduler: TaskScheduler,
        cap_registry: CapabilityRegistry,
        prov_registry: ProviderRegistry,
    ):
        self._di = di
        self._bus = bus
        self._state = state
        self._scheduler = scheduler
        self._cap_registry = cap_registry
        self._prov_registry = prov_registry

        self._logger = logging.getLogger("chhaya.agent_runtime")

        # In-memory tracking
        self._agents: dict[str, Agent] = {}
        self._handles: dict[str, AgentHandle] = {}
        self._active_executions: dict[str, AgentExecution] = {}  # Keyed by execution_id
        self._task_to_exec: dict[str, str] = {}  # Maps task_id to execution_id
        self._factories: dict[str, AgentFactory] = {}

        self._is_running = False

    @property
    def name(self) -> str:
        return "agent_runtime"

    @property
    def dependencies(self) -> list[str]:
        return [
            "event_bus",
            "state_manager",
            "task_scheduler",
            "capability_registry",
            "provider_registry",
        ]

    def ready(self) -> bool:
        return self._is_running

    async def health(self) -> HealthReport:
        faulted: int = sum(1 for h in self._handles.values() if h.state == AgentState.FAULTED)
        running: int = sum(
            1 for h in self._handles.values() if h.state in (AgentState.THINKING, AgentState.ACTING)
        )

        details = {
            "total_agents": str(len(self._handles)),
            "faulted_agents": str(faulted),
            "running_agents": str(running),
        }
        return HealthReport(is_healthy=(faulted == 0 or self._is_running), details=details)

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
        # Gracefully stop all agents
        for handle in self._handles.values():
            if handle.state not in (AgentState.TERMINATED, AgentState.FAULTED):
                await self.suspend_agent(handle.id)

    async def shutdown(self) -> None:
        await self.stop()
        # Clean up remaining resources
        for aid, agent in list(self._agents.items()):
            try:
                await agent.cleanup()
            except Exception as e:
                self._logger.error(f"Error cleaning up agent {aid}: {e}")
        self._agents.clear()
        self._handles.clear()

    # Factory Registration
    def register_factory(self, name: str, factory: AgentFactory) -> None:
        self._factories[name] = factory

    def unregister_factory(self, name: str) -> None:
        if name in self._factories:
            del self._factories[name]

    # Lifecycle Methods
    def register_agent(self, agent: Agent, config: dict[str, Any] | None = None) -> AgentHandle:
        if agent.id in self._agents:
            raise AgentRuntimeError(f"Agent {agent.id} already registered.")

        ctx = AgentContext(
            agent_id=agent.id,
            metadata=config or {},
            capabilities=config.get("capabilities", []) if config else [],
            di=self._di,
            state_manager=self._state,
            event_bus=self._bus,
            provider_registry=self._prov_registry,
            capability_registry=self._cap_registry,
        )

        handle = AgentHandle(
            id=agent.id,
            name=agent.name,
            state=AgentState.CREATED,
            priority=AgentPriority.NORMAL,
            health=AgentHealth(is_healthy=True, state=AgentState.CREATED),
            metrics=AgentMetrics(),
            context=ctx,
        )

        self._agents[agent.id] = agent
        self._handles[agent.id] = handle
        return handle

    def unregister_agent(self, agent_id: str) -> None:
        if agent_id in self._handles:
            handle = self._handles[agent_id]
            if handle.state not in (AgentState.TERMINATED, AgentState.FAULTED, AgentState.CREATED):
                raise AgentRuntimeError(
                    f"Cannot unregister agent {agent_id} while in state {handle.state}."
                )
            del self._handles[agent_id]
            del self._agents[agent_id]

    async def create_agent(self, factory_name: str, config: dict[str, Any]) -> str:
        if factory_name not in self._factories:
            raise AgentRuntimeError(f"No factory registered for '{factory_name}'.")

        agent = await self._factories[factory_name].create(
            name=config.get("name", "agent"), config=config
        )
        handle = self.register_agent(agent, config)
        await self._transition(handle, AgentState.CREATED)
        await self._bus.publish(Event(type="domain.agent.created", payload={"agent_id": handle.id}))

        try:
            await agent.initialize(handle.context)
            await self._transition(handle, AgentState.INITIALIZED)
        except Exception as e:
            handle.health.is_healthy = False
            handle.health.last_error = e
            await self._transition(handle, AgentState.FAULTED)
            raise AgentRuntimeError(f"Failed to initialize agent: {e}") from e

        return handle.id

    async def destroy_agent(self, agent_id: str) -> None:
        handle = self._get_handle(agent_id)
        if handle.state not in (
            AgentState.TERMINATED,
            AgentState.FAULTED,
            AgentState.CREATED,
            AgentState.INITIALIZED,
            AgentState.SUSPENDED,
        ):
            # Must cancel first if it's running
            await self.cancel_agent(agent_id)

        agent = self._agents[agent_id]
        try:
            await agent.cleanup()
        except Exception as e:
            self._logger.warning(f"Agent {agent_id} cleanup failed: {e}")

        await self._transition(handle, AgentState.TERMINATED)
        self.unregister_agent(agent_id)

        await self._bus.publish(
            Event(type="domain.agent.destroyed", payload={"agent_id": agent_id})
        )

    async def start_agent(self, agent_id: str) -> None:
        handle = self._get_handle(agent_id)
        if handle.state not in (AgentState.INITIALIZED, AgentState.IDLE):
            raise AgentRuntimeError(f"Cannot start agent from state {handle.state}")

        await self._transition(handle, AgentState.IDLE)
        await self._bus.publish(Event(type="domain.agent.started", payload={"agent_id": agent_id}))

    async def stop_agent(self, agent_id: str) -> None:
        handle = self._get_handle(agent_id)
        if handle.state in (AgentState.TERMINATED, AgentState.FAULTED):
            return

        if handle.state in (AgentState.THINKING, AgentState.ACTING):
            await self.cancel_agent(agent_id)

        await self._transition(handle, AgentState.INITIALIZED)
        await self._bus.publish(Event(type="domain.agent.stopped", payload={"agent_id": agent_id}))

    async def suspend_agent(self, agent_id: str) -> None:
        handle = self._get_handle(agent_id)
        if handle.state in (AgentState.TERMINATED, AgentState.FAULTED, AgentState.SUSPENDED):
            return

        if handle.state in (AgentState.THINKING, AgentState.ACTING):
            await self.cancel_agent(agent_id)

        await self._transition(handle, AgentState.SUSPENDED)
        await self._bus.publish(
            Event(type="domain.agent.suspended", payload={"agent_id": agent_id})
        )

    async def resume_agent(self, agent_id: str) -> None:
        handle = self._get_handle(agent_id)
        if handle.state != AgentState.SUSPENDED:
            raise AgentRuntimeError(f"Cannot resume agent from state {handle.state}")

        await self._transition(handle, AgentState.IDLE)
        await self._bus.publish(Event(type="domain.agent.resumed", payload={"agent_id": agent_id}))

    async def restart_agent(self, agent_id: str) -> None:
        await self.stop_agent(agent_id)
        agent = self._agents[agent_id]
        handle = self._handles[agent_id]

        try:
            await agent.cleanup()
            await agent.initialize(handle.context)
            handle.health.is_healthy = True
            handle.health.last_error = None
            await self._transition(handle, AgentState.INITIALIZED)
            await self.start_agent(agent_id)
        except Exception as e:
            handle.health.is_healthy = False
            handle.health.last_error = e
            await self._transition(handle, AgentState.FAULTED)
            raise AgentRuntimeError(f"Failed to restart agent: {e}") from e

    async def execute_agent(self, agent_id: str) -> str:
        """
        Submits the agent's step to the TaskScheduler for asynchronous execution.
        Returns the Execution ID.
        """
        handle = self._get_handle(agent_id)
        if handle.state not in (AgentState.IDLE, AgentState.AWAITING_INPUT, AgentState.SLEEPING):
            raise AgentRuntimeError(f"Cannot execute agent in state {handle.state}")

        agent = self._agents[agent_id]

        # Map AgentPriority to TaskPriority
        tp = TaskPriority.NORMAL
        if handle.priority == AgentPriority.BACKGROUND:
            tp = TaskPriority.LOW
        elif handle.priority == AgentPriority.HIGH:
            tp = TaskPriority.HIGH
        elif handle.priority == AgentPriority.REALTIME:
            tp = TaskPriority.CRITICAL

        task = _AgentTask(agent, handle.context)

        # Submit to scheduler
        task_id = await self._scheduler.submit(
            task=task, priority=tp, timeout_seconds=handle.context.timeout_seconds
        )

        exec_id = str(uuid.uuid4())
        execution = AgentExecution(
            execution_id=exec_id,
            agent_id=agent_id,
            started_at=datetime.datetime.now(datetime.UTC),
            task_id=task_id,
        )
        self._active_executions[exec_id] = execution
        self._task_to_exec[task_id] = exec_id

        await self._transition(handle, AgentState.ACTING)
        await self._bus.publish(
            Event(
                type="domain.agent.running", payload={"agent_id": agent_id, "execution_id": exec_id}
            )
        )

        # In a real async loop, we'd hook into TaskScheduler's completed event.
        # For this design, we expose a sync path to await the result if needed, or rely on events.
        # Let's attach a fire-and-forget monitor for this execution.

        return exec_id

    async def cancel_agent(self, agent_id: str) -> None:
        handle = self._get_handle(agent_id)
        handle.context.is_cancelled.set()

        has_active_execution = False
        # Find active execution efficiently
        for exec_id, exec_obj in list(self._active_executions.items()):
            if exec_obj.agent_id == agent_id:
                has_active_execution = True
                if exec_obj.task_id:
                    await self._scheduler.cancel(exec_obj.task_id)
                break

        # Only transition and publish here if there was NO active execution.
        # If there is one, TaskScheduler will emit `task.execution.cancelled`,
        # which triggers `_handle_task_result` to transition and publish.
        if not has_active_execution:
            await self._transition(handle, AgentState.IDLE)
            await self._bus.publish(
                Event(type="domain.agent.cancelled", payload={"agent_id": agent_id})
            )

    def get_agent(self, agent_id: str) -> AgentHandle:
        return self._get_handle(agent_id)

    def list_agents(self) -> list[AgentHandle]:
        return list(self._handles.values())

    async def _on_task_completed(self, e: Event) -> None:
        task_id = e.payload.get("task_id")
        await self._handle_task_result(task_id, AgentResult(success=True), "domain.agent.completed")

    async def _on_task_failed(self, e: Event) -> None:
        task_id = e.payload.get("task_id")
        # task.execution.failed provides an error payload but we might not have it directly.
        # Let's assume a generic error.
        await self._handle_task_result(
            task_id,
            AgentResult(success=False, error=Exception("Task Failed")),
            "domain.agent.failed",
        )

    async def _on_task_cancelled(self, e: Event) -> None:
        task_id = e.payload.get("task_id")
        await self._handle_task_result(
            task_id,
            AgentResult(success=False, error=Exception("Task Cancelled")),
            "domain.agent.cancelled",
            is_cancelled=True,
        )

    async def _handle_task_result(
        self, task_id: str | None, result: AgentResult, event_type: str, is_cancelled: bool = False
    ) -> None:
        if not task_id or task_id not in self._task_to_exec:
            return

        exec_id = self._task_to_exec[task_id]
        target_exec = self._active_executions.get(exec_id)

        if not target_exec:
            return

        # Clean up tracking dicts to prevent memory leaks
        del self._active_executions[exec_id]
        del self._task_to_exec[task_id]

        handle = self._get_handle(target_exec.agent_id)

        target_exec.finished_at = datetime.datetime.now(datetime.UTC)
        target_exec.result = result

        # Update metrics
        handle.metrics.total_executions += 1
        duration = (target_exec.finished_at - target_exec.started_at).total_seconds() * 1000
        handle.metrics.total_time_ms += duration

        # Do not overwrite state if agent is already terminated, suspended, or faulted
        if handle.state in (
            AgentState.TERMINATED,
            AgentState.FAULTED,
            AgentState.SUSPENDED,
            AgentState.IDLE,
            AgentState.INITIALIZED,
        ):
            # Don't revert to IDLE/FAULTED if it was deliberately changed mid-flight.
            # E.g. cancel_agent sets to IDLE, suspend_agent sets to SUSPENDED.
            pass
        else:
            if is_cancelled:
                await self._transition(handle, AgentState.IDLE)
            elif result.success:
                await self._transition(handle, AgentState.IDLE)
            else:
                handle.metrics.total_failures += 1
                handle.health.is_healthy = False
                handle.health.last_error = result.error
                await self._transition(handle, AgentState.FAULTED)

        # Emit completion
        payload = {"agent_id": handle.id, "execution_id": target_exec.execution_id}
        if not result.success and not is_cancelled:
            payload["error"] = str(result.error)

        await self._bus.publish(Event(type=event_type, payload=payload))

    def _get_handle(self, agent_id: str) -> AgentHandle:
        if agent_id not in self._handles:
            raise AgentRuntimeError(f"Agent {agent_id} not found.")
        return self._handles[agent_id]

    async def _transition(self, handle: AgentHandle, new_state: AgentState) -> None:
        old_state = handle.state
        handle.state = new_state
        handle.health.state = new_state

        # StateManager Integration: Persist core agent state
        try:
            await self._state.set_state(
                StateCategory.AGENT,
                handle.id,
                {
                    "id": handle.id,
                    "name": handle.name,
                    "state": new_state.value,
                    "priority": handle.priority.value,
                    "health": handle.health.is_healthy,
                    "metrics": {
                        "executions": handle.metrics.total_executions,
                        "failures": handle.metrics.total_failures,
                    },
                },
            )
        except Exception as e:
            self._logger.error(f"Failed to persist agent {handle.id} state: {e}")

        await self._bus.publish(
            Event(
                type="domain.agent.state_changed",
                payload={
                    "agent_id": handle.id,
                    "old_state": old_state.value,
                    "new_state": new_state.value,
                },
            )
        )
