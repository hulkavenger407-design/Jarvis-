"""
Capability Registry Subsystem.

Manages the registration and discovery of capabilities provided by plugins
and providers across the Chhaya Kernel ecosystem.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from event_bus.bus import EventBus
from event_bus.models import Event

from .lifecycle import HealthReport, KernelSubsystem


class CapabilityRegistryError(Exception):
    """Raised when a capability cannot be registered or resolved."""

    pass


@dataclass(frozen=True)
class Capability:
    """
    Represents a specific, versioned capability provided by a plugin or provider.
    """

    name: str
    version: str
    description: str = ""
    provider_name: str = "core"
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry(KernelSubsystem):
    """
    Manages the mapping of abstract capabilities across the ecosystem.
    Acts as a bridge so plugins can declare what they offer to the wider OS.
    """

    def __init__(self, event_bus: EventBus, logger: logging.Logger | None = None) -> None:
        self._bus = event_bus
        self._logger = logger or logging.getLogger("chhaya.capability_registry")
        self._capabilities: dict[str, Capability] = {}

    @property
    def name(self) -> str:
        return "capability_registry"

    @property
    def dependencies(self) -> list[str]:
        return ["event_bus"]

    async def initialize(self) -> None:
        """Called by the LifecycleManager."""
        self._logger.info("Capability Registry initialized.")

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def shutdown(self) -> None:
        self._capabilities.clear()

    async def health(self) -> HealthReport:
        return HealthReport(is_healthy=True, details={"count": str(len(self._capabilities))})

    def ready(self) -> bool:
        return True

    async def register_capability(self, capability: Capability) -> None:
        """
        Registers a new capability.

        Args:
            capability: The Capability object to register.

        Raises:
            CapabilityRegistryError: If the capability name is already registered.
        """
        if capability.name in self._capabilities:
            raise CapabilityRegistryError(
                f"Capability '{capability.name}' is already registered by "
                f"'{self._capabilities[capability.name].provider_name}'."
            )

        await self._bus.publish(
            Event(type="capability.register.started", payload={"capability": capability.name})
        )

        self._capabilities[capability.name] = capability

        await self._bus.publish(
            Event(type="capability.register.completed", payload={"capability": capability.name})
        )
        self._logger.debug(f"Registered capability '{capability.name}' v{capability.version}.")

    async def unregister_capability(self, name: str) -> None:
        """
        Unregisters an existing capability.

        Args:
            name: The name of the capability to remove.
        """
        if name not in self._capabilities:
            self._logger.warning(f"Attempted to unregister unknown capability '{name}'.")
            return

        del self._capabilities[name]

        await self._bus.publish(
            Event(type="capability.unregister.completed", payload={"capability": name})
        )
        self._logger.debug(f"Unregistered capability '{name}'.")

    def get_capability(self, name: str) -> Capability | None:
        """Retrieves a specific capability by name."""
        return self._capabilities.get(name)

    def list_capabilities(self) -> list[Capability]:
        """Returns a list of all currently registered capabilities."""
        return list(self._capabilities.values())

    def has_capability(self, name: str) -> bool:
        """Checks if a capability exists."""
        return name in self._capabilities
