import pytest
from event_bus.bus import EventBus
from event_bus.models import Event
from kernel.di import DIContainer
from kernel.lifecycle import (
    HealthReport,
    KernelState,
    LifecycleError,
    LifecycleManager,
)


class MockSubsystem:
    def __init__(self, name: str, deps: list[str]) -> None:
        self._name = name
        self._deps = deps
        self.log: list[str] = []
        self.fail_on_init = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def dependencies(self) -> list[str]:
        return self._deps

    async def initialize(self) -> None:
        if self.fail_on_init:
            raise ValueError("Init Boom")
        self.log.append("init")

    async def start(self) -> None:
        self.log.append("start")

    async def stop(self) -> None:
        self.log.append("stop")

    async def shutdown(self) -> None:
        self.log.append("shutdown")

    async def health(self) -> HealthReport:
        return HealthReport(True)

    def ready(self) -> bool:
        return True


@pytest.fixture
def manager() -> LifecycleManager:
    di = DIContainer()
    bus = EventBus()
    return LifecycleManager(di, bus)


def test_topological_sort(manager: LifecycleManager) -> None:
    # C depends on B, B depends on A
    a = MockSubsystem("A", [])
    b = MockSubsystem("B", ["A"])
    c = MockSubsystem("C", ["B"])

    # Register out of order
    manager.register_subsystem(c)
    manager.register_subsystem(a)
    manager.register_subsystem(b)

    manager._sort_dependencies()
    names = [sub.name for sub in manager._ordered_subsystems]
    assert names == ["A", "B", "C"]


def test_circular_dependency(manager: LifecycleManager) -> None:
    a = MockSubsystem("A", ["B"])
    b = MockSubsystem("B", ["A"])

    manager.register_subsystem(a)
    manager.register_subsystem(b)

    with pytest.raises(LifecycleError, match="Circular dependency"):
        manager._sort_dependencies()


@pytest.mark.asyncio
async def test_boot_sequence(manager: LifecycleManager) -> None:
    a = MockSubsystem("A", [])
    b = MockSubsystem("B", ["A"])

    manager.register_subsystem(a)
    manager.register_subsystem(b)

    await manager.boot()

    assert manager.state == KernelState.RUNNING
    # A should init then B should init, then A should start, then B should start
    assert a.log == ["init", "start"]
    assert b.log == ["init", "start"]


@pytest.mark.asyncio
async def test_shutdown_sequence(manager: LifecycleManager) -> None:
    a = MockSubsystem("A", [])
    b = MockSubsystem("B", ["A"])

    manager.register_subsystem(a)
    manager.register_subsystem(b)

    await manager.boot()
    await manager.shutdown()

    assert manager.state == KernelState.SHUTDOWN
    # Shutdown happens in reverse topological order, so B then A
    assert b.log == ["init", "start", "stop", "shutdown"]
    assert a.log == ["init", "start", "stop", "shutdown"]


@pytest.mark.asyncio
async def test_failure_recovery(manager: LifecycleManager) -> None:
    a = MockSubsystem("A", [])
    b = MockSubsystem("B", ["A"])
    b.fail_on_init = True

    manager.register_subsystem(a)
    manager.register_subsystem(b)

    with pytest.raises(LifecycleError, match="Boot failed"):
        await manager.boot()

    assert manager.state == KernelState.CRASHED

    # A succeeded init, B failed init.
    # The recovery sequence should immediately stop/shutdown A to prevent hanging resources.
    assert a.log == ["init", "stop", "shutdown"]


@pytest.mark.asyncio
async def test_health_reporting(manager: LifecycleManager) -> None:
    a = MockSubsystem("A", [])
    manager.register_subsystem(a)
    manager._sort_dependencies()

    report = await manager.get_health()
    assert "A" in report
    assert report["A"].is_healthy is True


@pytest.mark.asyncio
async def test_event_publishing() -> None:
    di = DIContainer()
    bus = EventBus()

    events_seen = []

    async def capture(e: Event) -> None:
        events_seen.append(e.type)

    bus.subscribe("system.state.*", capture)

    manager = LifecycleManager(di, bus)
    await manager.boot()
    await manager.shutdown()

    assert events_seen == [
        "system.state.initializing",
        "system.state.starting",
        "system.state.running",
        "system.state.stopping",
        "system.state.shutdown",
    ]
