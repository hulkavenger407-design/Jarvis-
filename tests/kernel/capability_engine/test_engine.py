import asyncio
from collections.abc import AsyncGenerator

import pytest
from event_bus.bus import EventBus
from event_bus.models import Event
from kernel.agent_runtime import (
    AgentContext,
    AgentHandle,
    AgentHealth,
    AgentMetrics,
    AgentPriority,
    AgentState,
)
from kernel.capability_engine import (
    CapabilityContext,
    CapabilityEngine,
    CapabilityExecutionState,
    CapabilityExecutor,
    CapabilityMiddleware,
    CapabilityRequest,
    CapabilityResolver,
    CapabilityResult,
    CapabilityResultStatus,
)
from kernel.capability_registry import CapabilityRegistry
from kernel.di import DIContainer
from kernel.provider_registry import ProviderRegistry
from kernel.statemanager import StateCategory, StateManager
from kernel.task_scheduler import TaskScheduler


class MockExecutor(CapabilityExecutor):
    def __init__(self, succeed: bool = True, sleep: float = 0.0, raises: bool = False) -> None:
        self.succeed = succeed
        self.sleep = sleep
        self.raises = raises
        self.executed = False

    async def execute(self, context: CapabilityContext) -> CapabilityResult:
        if self.sleep > 0:
            await asyncio.sleep(self.sleep)

        if context.is_cancelled.is_set():
            raise asyncio.CancelledError()

        self.executed = True

        if self.raises:
            raise Exception("Mock Exception")

        if self.succeed:
            return CapabilityResult(status=CapabilityResultStatus.SUCCESS, data="success_data")
        return CapabilityResult(
            status=CapabilityResultStatus.ERROR, error=Exception("Mock Failure")
        )


class MockResolver(CapabilityResolver):
    def __init__(self, mapping: dict[str, CapabilityExecutor]) -> None:
        self.mapping = mapping

    async def resolve(self, capability_name: str) -> CapabilityExecutor:
        if capability_name in self.mapping:
            return self.mapping[capability_name]
        raise Exception("Not found")


class MockMiddleware(CapabilityMiddleware):
    def __init__(self) -> None:
        self.before_called = 0
        self.after_called = 0

    async def before_execute(self, context: CapabilityContext) -> None:
        self.before_called += 1

    async def after_execute(
        self, context: CapabilityContext, result: CapabilityResult
    ) -> CapabilityResult:
        self.after_called += 1
        return result


class MockAgentRuntime:
    def __init__(self, allowed_capabilities: list[str]) -> None:
        self.allowed = allowed_capabilities

    async def get_agent(self, agent_id: str) -> AgentHandle:
        ctx = AgentContext(
            agent_id=agent_id,
            metadata={},
            capabilities=self.allowed,
            di=None,  # type: ignore
            state_manager=None,  # type: ignore
            event_bus=None,  # type: ignore
            provider_registry=None,  # type: ignore
            capability_registry=None,  # type: ignore
        )
        return AgentHandle(
            id=agent_id,
            name="mock",
            state=AgentState.IDLE,
            priority=AgentPriority.NORMAL,
            health=AgentHealth(is_healthy=True, state=AgentState.IDLE),
            metrics=AgentMetrics(),
            context=ctx,
        )


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
async def scheduler(bus: EventBus) -> AsyncGenerator[TaskScheduler, None]:
    di = DIContainer()
    state = StateManager(bus)
    sch = TaskScheduler(di, bus, state, worker_count=2)
    await sch.initialize()
    await sch.start()
    yield sch
    await sch.stop()


@pytest.fixture
async def engine(bus: EventBus, scheduler: TaskScheduler) -> AsyncGenerator[CapabilityEngine, None]:
    di = DIContainer()
    state = StateManager(bus)
    cap = CapabilityRegistry(bus)
    prov = ProviderRegistry()
    agent_rt = MockAgentRuntime(["test.capability", "test.slow", "test.fail", "test.error", "test.cap"])

    eng = CapabilityEngine(
        di=di,
        bus=bus,
        state=state,
        scheduler=scheduler,
        agent_runtime=agent_rt,  # type: ignore
        cap_registry=cap,
        prov_registry=prov,
    )

    await eng.initialize()
    await eng.start()
    yield eng
    await eng.shutdown()


@pytest.mark.asyncio
async def test_successful_execution(engine: CapabilityEngine, bus: EventBus) -> None:
    executor = MockExecutor()
    engine.add_resolver(MockResolver({"test.capability": executor}))

    events = []

    async def sub(e: Event) -> None:
        events.append(e.type)

    bus.subscribe("capability.execution.requested", sub)
    bus.subscribe("capability.execution.authorized", sub)
    bus.subscribe("capability.execution.started", sub)
    bus.subscribe("capability.execution.completed", sub)
    bus.subscribe("capability.execution.finished", sub)

    req = CapabilityRequest(capability_name="test.capability", agent_id="agent-01", arguments={})

    exec_id = await engine.submit(req)
    await asyncio.sleep(0.2)

    assert executor.executed is True
    assert engine._metrics.execution_count == 1
    assert engine._metrics.success_count == 1
    assert engine._metrics.failure_count == 0

    assert "capability.execution.requested" in events
    assert "capability.execution.authorized" in events
    assert "capability.execution.started" in events
    assert "capability.execution.completed" in events
    assert "capability.execution.finished" in events

    # Verify StateManager integration
    state = engine._state
    saved = await state.get_state(StateCategory.CAPABILITY, exec_id)
    assert saved is not None
    assert saved["state"] == CapabilityExecutionState.COMPLETED.value


@pytest.mark.asyncio
async def test_authorization_failure(engine: CapabilityEngine) -> None:
    executor = MockExecutor()
    engine.add_resolver(MockResolver({"unauthorized.cap": executor}))

    req = CapabilityRequest(capability_name="unauthorized.cap", agent_id="agent-01", arguments={})

    await engine.submit(req)
    await asyncio.sleep(0.2)

    assert executor.executed is False
    assert engine._metrics.failure_count == 1


@pytest.mark.asyncio
async def test_middleware_pipeline(engine: CapabilityEngine) -> None:
    executor = MockExecutor()
    engine.add_resolver(MockResolver({"test.capability": executor}))

    mw = MockMiddleware()
    engine.add_middleware(mw)

    req = CapabilityRequest(capability_name="test.capability", agent_id="agent-01", arguments={})

    await engine.submit(req)
    await asyncio.sleep(0.2)

    assert mw.before_called == 1
    assert mw.after_called == 1


@pytest.mark.asyncio
async def test_retries(engine: CapabilityEngine, bus: EventBus) -> None:
    executor = MockExecutor(succeed=False)
    engine.add_resolver(MockResolver({"test.fail": executor}))

    events = []

    async def sub(e: Event) -> None:
        events.append(e.type)

    bus.subscribe("capability.execution.retry", sub)

    req = CapabilityRequest(
        capability_name="test.fail", agent_id="agent-01", arguments={}, max_retries=2
    )

    await engine.submit(req)
    await asyncio.sleep(0.5)

    assert engine._metrics.retry_count == 2
    assert engine._metrics.failure_count == 1
    assert "capability.execution.retry" in events


@pytest.mark.asyncio
async def test_timeout_enforcement(engine: CapabilityEngine, bus: EventBus) -> None:
    executor = MockExecutor(sleep=1.0)
    engine.add_resolver(MockResolver({"test.slow": executor}))

    events = []

    async def sub(e: Event) -> None:
        events.append(e.type)

    bus.subscribe("capability.execution.timeout", sub)

    req = CapabilityRequest(
        capability_name="test.slow", agent_id="agent-01", arguments={}, timeout_seconds=0.1
    )

    await engine.submit(req)
    await asyncio.sleep(0.4)

    assert engine._metrics.timeout_count == 1
    assert "capability.execution.timeout" in events


@pytest.mark.asyncio
async def test_cancellation(engine: CapabilityEngine, bus: EventBus) -> None:
    executor = MockExecutor(sleep=1.0)
    engine.add_resolver(MockResolver({"test.slow": executor}))

    events = []

    async def sub(e: Event) -> None:
        events.append(e.type)

    bus.subscribe("capability.execution.cancelled", sub)

    req = CapabilityRequest(capability_name="test.slow", agent_id="agent-01", arguments={})

    exec_id = await engine.submit(req)
    await asyncio.sleep(0.1)  # Running

    await engine.cancel(exec_id)
    await asyncio.sleep(0.1)

    assert "capability.execution.cancelled" in events


@pytest.mark.asyncio
async def test_executor_raw_exception(engine: CapabilityEngine) -> None:
    executor = MockExecutor(raises=True)
    engine.add_resolver(MockResolver({"test.error": executor}))

    req = CapabilityRequest(capability_name="test.error", agent_id="agent-01", arguments={})

    await engine.submit(req)
    await asyncio.sleep(0.2)

    assert engine._metrics.failure_count == 1

@pytest.mark.asyncio
async def test_icapability_engine_invoke_success(engine: CapabilityEngine):
    executor = MockExecutor(succeed=True)
    engine.add_resolver(MockResolver({"test.cap": executor}))

    result = await engine.invoke("test.cap", {"agent_id": "agent-01"}, {"arg1": "val1"})
    assert result == "success_data"
    assert executor.executed is True

@pytest.mark.asyncio
async def test_icapability_engine_invoke_failure(engine: CapabilityEngine):
    executor = MockExecutor(succeed=False)
    engine.add_resolver(MockResolver({"test.fail": executor}))

    with pytest.raises(Exception, match="Mock Failure"):
        await engine.invoke("test.fail", {"agent_id": "agent-01"}, {"arg1": "val1"})

@pytest.mark.asyncio
async def test_icapability_engine_get_status(engine: CapabilityEngine):
    executor = MockExecutor(succeed=True)
    engine.add_resolver(MockResolver({"test.cap": executor}))

    req = CapabilityRequest(capability_name="test.cap", agent_id="agent-01", arguments={})
    exec_id = await engine.submit(req)

    await asyncio.sleep(0.1)

    status = await engine.get_status(exec_id)
    assert status == CapabilityExecutionState.COMPLETED.value
