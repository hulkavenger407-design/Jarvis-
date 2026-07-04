"""
Plugin Manager Subsystem.

Manages the lifecycle, dependencies, and state of third-party plugins.
Does not execute plugin logic directly, but rather integrates them
with the DI Container and Event Bus.
"""
import logging

from event_bus.bus import EventBus
from event_bus.models import Event
from plugin_sdk.base import PluginLoadError, PluginProtocol, PluginState

from .di import DIContainer


class PluginManager:
    """
    Manages discovery, loading, and lifecycles of Chhaya Plugins.
    """

    def __init__(
        self,
        di_container: DIContainer,
        event_bus: EventBus,
        logger: logging.Logger | None = None
    ) -> None:
        self._di = di_container
        self._bus = event_bus
        self._logger = logger or logging.getLogger("chhaya.plugin_manager")

        # Internal state tracking
        self._plugins: dict[str, PluginProtocol] = {}
        self._plugin_states: dict[str, PluginState] = {}

        # In a real dynamic environment, this would hold available classes found via importlib
        # For this Phase 1 architectural implementation, we allow injecting classes directly
        self._discovered_classes: dict[str, type[PluginProtocol]] = {}

    def discover_plugins(self, plugin_classes: list[type[PluginProtocol]]) -> None:
        """
        Simulates discovering plugins from the file system by registering their class definitions.
        """
        for cls in plugin_classes:
            try:
                name = cls.metadata.name
                self._discovered_classes[name] = cls
                self._plugin_states[name] = PluginState.UNLOADED
            except Exception as e:
                self._logger.error(f"Failed to discover plugin class {cls.__name__}: {e}")

    async def load_plugin(self, name: str) -> None:
        """Instantiates a plugin and maps its dependencies."""
        if name not in self._discovered_classes:
            raise PluginLoadError(f"Plugin '{name}' not found in discovered plugins.")

        if self._plugin_states.get(name) not in (PluginState.UNLOADED, PluginState.FAILED):
            self._logger.warning(f"Plugin '{name}' is already loaded.")
            return

        cls = self._discovered_classes[name]

        # 1. Validate dependencies recursively to catch circular deps early
        self._validate_dependencies(cls)

        # 2. Load dependencies in order
        for dep in cls.metadata.dependencies:
            dep_state = self._plugin_states.get(dep)
            if dep_state == PluginState.UNLOADED or dep_state == PluginState.FAILED:
                await self.load_plugin(dep)
            elif dep_state not in (
                PluginState.LOADED,
                PluginState.INITIALIZED,
                PluginState.RUNNING,
                PluginState.STOPPED,
            ):
                raise PluginLoadError(
                    f"Dependency '{dep}' of '{name}' is in an invalid state: {dep_state}"
                )

        await self._bus.publish(Event(type="plugin.load.started", payload={"plugin": name}))
        self._plugin_states[name] = PluginState.LOADED

        try:
            # 3. Instantiate via DI Container. Fulfills the "dependencies only through DI" rule.
            instance = self._di.resolve(cls)
            self._plugins[name] = instance

            await self._bus.publish(
                Event(type="plugin.load.completed", payload={"plugin": name})
            )
        except Exception as e:
            self._plugin_states[name] = PluginState.FAILED
            await self._bus.publish(
                Event(type="plugin.load.failed", payload={"plugin": name, "error": str(e)})
            )
            raise PluginLoadError(f"Failed to load plugin {name}: {e}") from e

    async def initialize_plugin(self, name: str) -> None:
        """Calls the plugin's initialize method."""
        await self._transition_state(
            name,
            PluginState.LOADED,
            PluginState.INITIALIZED,
            "initialize",
            "plugin.initialize.started",
            "plugin.initialize.completed"
        )

    async def start_plugin(self, name: str) -> None:
        """Calls the plugin's start method."""
        await self._transition_state(
            name,
            PluginState.INITIALIZED,
            PluginState.RUNNING,
            "start",
            "plugin.start.started",
            "plugin.start.completed"
        )

    async def stop_plugin(self, name: str) -> None:
        """Calls the plugin's stop method."""
        if self._plugin_states.get(name) != PluginState.RUNNING:
            return

        await self._transition_state(
            name,
            PluginState.RUNNING,
            PluginState.STOPPED,
            "stop",
            "plugin.stop.started",
            "plugin.stop.completed"
        )

    async def unload_plugin(self, name: str) -> None:
        """Shuts down and unloads a plugin."""
        state = self._plugin_states.get(name)
        valid_states = (
            PluginState.STOPPED,
            PluginState.FAILED,
            PluginState.INITIALIZED,
            PluginState.LOADED
        )
        if state not in valid_states:
            # Try to gracefully stop it first if it's running
            if state == PluginState.RUNNING:
                await self.stop_plugin(name)

        await self._bus.publish(Event(type="plugin.unload.started", payload={"plugin": name}))

        try:
            if name in self._plugins:
                await self._plugins[name].shutdown()
                del self._plugins[name]

            self._plugin_states[name] = PluginState.UNLOADED
            await self._bus.publish(
                Event(type="plugin.unload.completed", payload={"plugin": name})
            )
        except Exception as e:
            self._plugin_states[name] = PluginState.FAILED
            self._logger.error(f"Failed to cleanly unload plugin {name}: {e}")
            await self._bus.publish(
                Event(type="plugin.unload.failed", payload={"plugin": name, "error": str(e)})
            )

    async def reload_plugin(self, name: str) -> None:
        """Unloads, then re-loads, initializes, and starts a plugin."""
        await self.unload_plugin(name)
        await self.load_plugin(name)
        await self.initialize_plugin(name)
        await self.start_plugin(name)

    def list_plugins(self) -> dict[str, PluginState]:
        """Returns a snapshot of all discovered plugins and their states."""
        return dict(self._plugin_states)

    def get_plugin(self, name: str) -> PluginProtocol | None:
        """Returns the active plugin instance, if loaded."""
        return self._plugins.get(name)

    # --- Internal Utilities ---

    def _validate_dependencies(self, cls: type[PluginProtocol]) -> None:
        """
        Validates that all required dependencies are present in the discovered classes.
        Does a DFS to detect circular dependencies among the discovered graph.
        """
        name = cls.metadata.name

        for dep in cls.metadata.dependencies:
            if dep not in self._discovered_classes:
                raise PluginLoadError(f"Missing dependency: '{dep}' required by '{name}'")

        # Detect circular dependencies using a recursive DFS
        visited = set()
        path: list[str] = []

        def dfs(current_node: str) -> None:
            if current_node in path:
                cycle = " -> ".join(path + [current_node])
                raise PluginLoadError(f"Circular dependency detected: {cycle}")
            if current_node in visited:
                return

            path.append(current_node)

            # Get dependencies for this node
            if current_node in self._discovered_classes:
                node_cls = self._discovered_classes[current_node]
                for d in node_cls.metadata.dependencies:
                    dfs(d)

            path.pop()
            visited.add(current_node)

        dfs(name)

    async def _transition_state(
        self,
        name: str,
        expected_state: PluginState,
        target_state: PluginState,
        method_name: str,
        start_event: str,
        complete_event: str
    ) -> None:
        """Generic state machine transition executing a plugin method securely."""
        if name not in self._plugins:
            raise PluginLoadError(f"Plugin '{name}' is not loaded.")

        current_state = self._plugin_states.get(name)
        if current_state != expected_state:
            cs_val = current_state.value if current_state else 'unknown'
            raise PluginLoadError(
                f"Cannot {method_name} plugin '{name}'. "
                f"Expected state {expected_state.value}, but is {cs_val}."
            )

        await self._bus.publish(Event(type=start_event, payload={"plugin": name}))

        try:
            plugin = self._plugins[name]
            method = getattr(plugin, method_name)
            await method()
            self._plugin_states[name] = target_state
            await self._bus.publish(Event(type=complete_event, payload={"plugin": name}))
        except Exception as e:
            self._plugin_states[name] = PluginState.FAILED
            self._logger.error(f"Plugin '{name}' failed during {method_name}(): {e}")

            # Map start_event "plugin.initialize.started" -> "plugin.initialize.failed"
            fail_event = start_event.replace(".started", ".failed")
            await self._bus.publish(
                Event(type=fail_event, payload={"plugin": name, "error": str(e)})
            )
            # Error isolation: we catch and log, but do not crash the kernel manager loop
