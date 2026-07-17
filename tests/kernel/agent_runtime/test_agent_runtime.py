import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from event_bus.bus import EventBus
from event_bus.models import Event
from kernel.agent_runtime import (
    Agent,
    AgentContext,
    AgentFactory,
    AgentResult,
    AgentRuntime,
    AgentRuntimeError,
    AgentState,
)
from kernel.capability_registry import CapabilityRegistry
from kernel.di import DIContainer
from kernel.provider_registry import ProviderRegistry
from kernel.statemanager import StateCategory, StateManager
from kernel.task_scheduler import TaskScheduler


class MockAgent(Agent):
    def __init__(
        self, id_str: str, name_str: str, succeed: bool = True, sleep: float = 0.0
    ) -> None:
        self._id = id_str
        self._name = name_str
        self.succeed = succeed
        self.sleep = sleep
        self.initialized = False
        self.cleaned_up = False
        self.executions = 0

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    async def initialize(self, context: AgentContext) -> None:
        self.initialized = True

    async def step(self, context: AgentContext) -> AgentResult:
        if self.sleep > 0:
            await asyncio.sleep(self.sleep)

        if context.is_cancelled.is_set():
            raise asyncio.CancelledError()

        self.executions += 1

        if self.succeed:
            return AgentResult(success=True)
        else:
            raise Exception("Forced Agent Failure")

    async def cleanup(self) -> None:
        self.cleaned_up = True


class MockAgentFactory(AgentFactory):
    async def create(self, name: str, config: dict[str, Any]) -> Agent:
        return MockAgent(
            id_str=config.get("id", "agent-factory-01"),
            name_str=name,
            succeed=config.get("succeed", True),
            sleep=config.get("sleep", 0.0),
        )


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
async def scheduler(bus: EventBus) -> AsyncGenerator[TaskScheduler, None]:
    di = DIContainer()
    from typing import cast

    from kernel.interfaces import IEventBus
    state = StateManager(cast(IEventBus, bus))
    sch = TaskScheduler(di, bus, state, worker_count=2)
    await sch.initialize()
    await sch.start()
    yield sch
    await sch.stop()


@pytest.fixture
async def runtime(bus: EventBus, scheduler: TaskScheduler) -> AsyncGenerator[AgentRuntime, None]:
    di = DIContainer()
    from typing import cast

    from kernel.interfaces import IEventBus
    state = StateManager(cast(IEventBus, bus))
    prov = ProviderRegistry()
    cap = CapabilityRegistry(prov)
    prov = ProviderRegistry()

    rt = AgentRuntime(
        di=di, bus=bus, state=state, scheduler=scheduler, cap_registry=cap, prov_registry=prov
    )

    await rt.initialize()
    await rt.start()
    yield rt
    await rt.shutdown()


@pytest.mark.asyncio
async def test_agent_registration_and_lifecycle(runtime: AgentRuntime) -> None:
    agent = MockAgent("agent-01", "TestAgent")
    runtime.register_agent_sync(agent)
    handle = runtime.get_agent(agent.id)

    assert handle.id == "agent-01"
    assert handle.state == AgentState.CREATED

    await agent.initialize(handle.context)
    handle.state = AgentState.INITIALIZED

    await runtime.start_agent("agent-01")
    handle = runtime.get_agent("agent-01")
    assert handle.state == AgentState.IDLE

    await runtime.suspend_agent("agent-01")
    handle = runtime.get_agent("agent-01")
    assert handle.state == AgentState.SUSPENDED

    await runtime.resume_agent("agent-01")
    handle = runtime.get_agent("agent-01")
    assert handle.state == AgentState.IDLE

    await runtime.unregister_agent("agent-01")
    assert getattr(agent, "cleaned_up", False) is True

    with pytest.raises(AgentRuntimeError):
        runtime.get_agent("agent-01")


@pytest.mark.asyncio
async def test_agent_execution_success(runtime: AgentRuntime, bus: EventBus) -> None:
    agent = MockAgent("agent-02", "ExecAgent", sleep=0.1)
    runtime.register_agent_sync(agent)

    # Needs to be initialized/idle to run
    handle = runtime.get_agent("agent-02")
    handle.state = AgentState.IDLE

    events = []

    async def sub(e: Event) -> None:
        events.append(e.type)

    bus.subscribe("domain.agent.*", sub)

    await runtime.execute_agent("agent-02")
    await asyncio.sleep(0.5)

    assert agent.executions == 1
    assert handle.metrics.total_executions == 1
    assert handle.metrics.total_failures == 0
    assert handle.state == AgentState.IDLE

    assert "domain.agent.running" in events
    assert "domain.agent.completed" in events


@pytest.mark.asyncio
async def test_agent_execution_failure(runtime: AgentRuntime, bus: EventBus) -> None:
    agent = MockAgent("agent-03", "FailAgent", succeed=False, sleep=0.1)
    runtime.register_agent_sync(agent)

    handle = runtime.get_agent("agent-03")
    handle.state = AgentState.IDLE

    events = []

    async def sub(e: Event) -> None:
        events.append(e.type)

    bus.subscribe("domain.agent.failed", sub)

    await runtime.execute_agent("agent-03")
    await asyncio.sleep(0.5)

    assert handle.metrics.total_failures == 1
    assert handle.state == AgentState.FAULTED
    assert handle.health.is_healthy is False
    assert "domain.agent.failed" in events


@pytest.mark.asyncio
async def test_agent_cancellation(runtime: AgentRuntime) -> None:
    agent = MockAgent("agent-04", "SlowAgent", sleep=0.5)
    runtime.register_agent_sync(agent)
    handle = runtime.get_agent("agent-04")
    handle.state = AgentState.IDLE

    await runtime.execute_agent("agent-04")

    await asyncio.sleep(0.1)  # Running but sleeping
    handle = runtime.get_agent("agent-04")
    assert handle.state == AgentState.ACTING

    await runtime.cancel_agent("agent-04")
    await asyncio.sleep(0.1)

    handle = runtime.get_agent("agent-04")
    assert handle.state == AgentState.IDLE
    assert handle.context.is_cancelled.is_set()


@pytest.mark.asyncio
async def test_factory_creation(runtime: AgentRuntime) -> None:
    factory = MockAgentFactory()
    runtime.register_factory("mock", factory)

    aid = await runtime.create_agent("mock", {"id": "agent-05", "name": "CreatedAgent"})

    assert aid == "agent-05"
    handle = runtime.get_agent("agent-05")
    assert handle.state == AgentState.INITIALIZED

    agent = runtime._agents["agent-05"]
    assert getattr(agent, "initialized", False) is True

    # Clean up
    await runtime.unregister_agent("agent-05")


@pytest.mark.asyncio
async def test_restart_recovery(runtime: AgentRuntime) -> None:
    agent = MockAgent("agent-06", "RestartAgent")
    runtime.register_agent_sync(agent)
    handle = runtime.get_agent("agent-06")
    handle.state = AgentState.FAULTED
    handle.health.is_healthy = False

    await runtime.restart_agent("agent-06")

    assert getattr(agent, "cleaned_up", False) is True
    assert getattr(agent, "initialized", False) is True

    handle = runtime.get_agent("agent-06")
    assert handle.state == AgentState.IDLE
    assert handle.health.is_healthy is True


@pytest.mark.asyncio
async def test_concurrent_execution(runtime: AgentRuntime) -> None:
    # Register 10 agents
    ids = []
    for i in range(10):
        aid = f"agent-conc-{i}"
        agent = MockAgent(aid, f"Agent-{i}", sleep=0.05)
        runtime.register_agent_sync(agent)
        handle = runtime.get_agent(aid)
        handle.state = AgentState.IDLE
        ids.append(aid)

    # Fire them all at once
    for aid in ids:
        await runtime.execute_agent(aid)

    # Wait for scheduler to chew through them (2 workers = 5 batches of 0.05s = 0.25s)
    await asyncio.sleep(1.0)

    for aid in ids:
        handle = runtime.get_agent(aid)
        assert handle.metrics.total_executions == 1
        assert handle.state == AgentState.IDLE


@pytest.mark.asyncio
async def test_agent_state_persistence(runtime: AgentRuntime) -> None:
    state = runtime._state
    agent = MockAgent("agent-10", "PersistAgent")
    handle = runtime.register_agent_sync(agent)
    await runtime._transition(handle, AgentState.IDLE)

    # Check if state manager saved it
    saved = await state.get_state(StateCategory.AGENT, "agent-10")
    assert saved is not None
    assert saved["id"] == "agent-10"
    assert saved["state"] == "idle"
