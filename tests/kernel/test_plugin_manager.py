import pytest
from event_bus.bus import EventBus
from kernel.di import DIContainer, Lifetime
from kernel.plugin_manager import PluginManager
from plugin_sdk.base import PluginLoadError, PluginMetadata, PluginProtocol, PluginState


class DummyPlugin(PluginProtocol):
    metadata = PluginMetadata(name="dummy", version="1.0", dependencies=[])

    def __init__(self) -> None:
        self.init_called = False
        self.start_called = False
        self.stop_called = False
        self.shutdown_called = False

    async def initialize(self) -> None: self.init_called = True
    async def start(self) -> None: self.start_called = True
    async def stop(self) -> None: self.stop_called = True
    async def shutdown(self) -> None: self.shutdown_called = True


class DependentPlugin(PluginProtocol):
    metadata = PluginMetadata(name="dependent", version="1.0", dependencies=["dummy"])

    def __init__(self) -> None:
        pass

    async def initialize(self) -> None: pass
    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    async def shutdown(self) -> None: pass


class CircularA(PluginProtocol):
    metadata = PluginMetadata("A", "1", dependencies=["B"])
    def __init__(self) -> None: pass
    async def initialize(self) -> None: pass
    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    async def shutdown(self) -> None: pass

class CircularB(PluginProtocol):
    metadata = PluginMetadata("B", "1", dependencies=["A"])
    def __init__(self) -> None: pass
    async def initialize(self) -> None: pass
    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    async def shutdown(self) -> None: pass


class FailingPlugin(PluginProtocol):
    metadata = PluginMetadata("failer", "1.0")
    def __init__(self) -> None: pass
    async def initialize(self) -> None: raise ValueError("Init failed")
    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    async def shutdown(self) -> None: pass


@pytest.fixture
def manager() -> PluginManager:
    di = DIContainer()

    # We must register the classes with the DI container so PluginManager can resolve them!
    di.register(DummyPlugin, lambda: DummyPlugin(), Lifetime.TRANSIENT)
    di.register(DependentPlugin, lambda: DependentPlugin(), Lifetime.TRANSIENT)
    di.register(CircularA, lambda: CircularA(), Lifetime.TRANSIENT)
    di.register(CircularB, lambda: CircularB(), Lifetime.TRANSIENT)
    di.register(FailingPlugin, lambda: FailingPlugin(), Lifetime.TRANSIENT)

    bus = EventBus()
    return PluginManager(di, bus)


@pytest.mark.asyncio
async def test_discover_and_load(manager: PluginManager) -> None:
    manager.discover_plugins([DummyPlugin])

    states = manager.list_plugins()
    assert states["dummy"] == PluginState.UNLOADED

    await manager.load_plugin("dummy")
    assert manager.list_plugins()["dummy"] == PluginState.LOADED

    plugin = manager.get_plugin("dummy")
    assert isinstance(plugin, DummyPlugin)


@pytest.mark.asyncio
async def test_full_lifecycle(manager: PluginManager) -> None:
    manager.discover_plugins([DummyPlugin])
    await manager.load_plugin("dummy")
    await manager.initialize_plugin("dummy")
    await manager.start_plugin("dummy")

    assert manager.list_plugins()["dummy"] == PluginState.RUNNING

    plugin = manager.get_plugin("dummy")
    assert isinstance(plugin, DummyPlugin)
    assert plugin.init_called and plugin.start_called

    await manager.stop_plugin("dummy")
    assert plugin.stop_called
    assert manager.list_plugins()["dummy"] == PluginState.STOPPED

    await manager.unload_plugin("dummy")
    assert plugin.shutdown_called
    assert manager.list_plugins()["dummy"] == PluginState.UNLOADED
    assert manager.get_plugin("dummy") is None


@pytest.mark.asyncio
async def test_missing_dependencies(manager: PluginManager) -> None:
    # We discover DependentPlugin, but not DummyPlugin
    manager.discover_plugins([DependentPlugin])

    with pytest.raises(PluginLoadError, match="Missing dependency"):
        await manager.load_plugin("dependent")


@pytest.mark.asyncio
async def test_circular_dependencies(manager: PluginManager) -> None:
    manager.discover_plugins([CircularA, CircularB])

    with pytest.raises(PluginLoadError, match="Circular dependency detected"):
        await manager.load_plugin("A")


@pytest.mark.asyncio
async def test_dependency_loading_order(manager: PluginManager) -> None:
    manager.discover_plugins([DummyPlugin, DependentPlugin])

    # Trigger load on the dependent plugin
    await manager.load_plugin("dependent")

    # It should have automatically loaded the dependency first
    states = manager.list_plugins()
    assert states["dummy"] == PluginState.LOADED
    assert states["dependent"] == PluginState.LOADED


@pytest.mark.asyncio
async def test_error_isolation(manager: PluginManager) -> None:
    manager.discover_plugins([FailingPlugin])

    await manager.load_plugin("failer")

    # Initialization will fail, but the kernel loop should not crash the caller
    # (The error is logged and the event bus is notified, but exception is swallowed)
    await manager.initialize_plugin("failer")

    assert manager.list_plugins()["failer"] == PluginState.FAILED


@pytest.mark.asyncio
async def test_reload(manager: PluginManager) -> None:
    manager.discover_plugins([DummyPlugin])
    await manager.load_plugin("dummy")
    await manager.initialize_plugin("dummy")
    await manager.start_plugin("dummy")

    await manager.reload_plugin("dummy")

    # Reload unloads and restarts the plugin, so it should be back in RUNNING state
    assert manager.list_plugins()["dummy"] == PluginState.RUNNING

@pytest.mark.asyncio
async def test_duplicate_plugins(manager: PluginManager) -> None:
    # Attempting to discover the same class twice should not crash,
    # and the state should remain stable.
    manager.discover_plugins([DummyPlugin, DummyPlugin])

    states = manager.list_plugins()
    assert len(states) == 1
    assert states["dummy"] == PluginState.UNLOADED
