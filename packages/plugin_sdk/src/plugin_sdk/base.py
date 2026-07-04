"""
Plugin SDK Models

Defines the core protocols, metadata structures, and states required
to build and manage Chhaya Kernel plugins.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Protocol


class PluginLoadError(Exception):
    """Raised when a plugin fails to load, initialize, or resolve dependencies."""
    pass


class PluginState(Enum):
    """Represents the lifecycle state of a Plugin within the Manager."""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True)
class PluginMetadata:
    """
    Manifest data exposed by a plugin to describe its identity,
    dependencies, and capabilities to the PluginManager.
    """
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    provided_capabilities: list[str] = field(default_factory=list)


class PluginProtocol(Protocol):
    """
    The interface all Chhaya plugins must implement.
    Plugins are instantiated by the PluginManager via the DI Container.
    """

    # Using a ClassVar avoids instantiating the class just to read metadata
    metadata: ClassVar[PluginMetadata]

    async def initialize(self) -> None:
        """
        Called after the plugin is loaded and dependencies are resolved.
        Use this to register providers and hook into the event bus.
        """
        ...

    async def start(self) -> None:
        """
        Called when the kernel starts the plugin.
        Use this to begin background tasks or establish external connections.
        """
        ...

    async def stop(self) -> None:
        """
        Called when the kernel halts the plugin.
        Use this to pause execution or gracefully drop connections.
        """
        ...

    async def shutdown(self) -> None:
        """
        Called before the plugin is unloaded.
        Use this to perform final cleanup and unregister from the DI/EventBus.
        """
        ...
