"""
Capability Registry Subsystem.

Manages the registration and discovery of capabilities provided by plugins
and providers across the Chhaya Kernel ecosystem.
"""

import asyncio
import logging
from typing import Any, Protocol

from ..lifecycle import HealthReport, KernelSubsystem
from .errors import (
    CapabilityDuplicateError,
    CapabilityNotFoundError,
    CapabilityRegistryError,
    CapabilityValidationError,
    ProviderNotFoundError,
)
from .interfaces import ICapability, ILifecycleCapability
from .models import CapabilityHandle, CapabilityState, CapabilityVersion


class IProviderRegistry(Protocol):
    """
    Frozen Provider Registry interface protocol required by CapabilityRegistry.
    """
    def get_provider(self, interface: Any, provider_id: str | None = None) -> Any:
        ...


class CapabilityRegistry(KernelSubsystem):
    """
    Manages the mapping of abstract capabilities across the ecosystem.
    Acts as a bridge so plugins can declare what they offer to the wider OS.
    """

    def __init__(
        self, provider_registry: IProviderRegistry, logger: logging.Logger | None = None
    ) -> None:
        """
        Initializes the Capability Registry.

        Args:
            provider_registry: The provider registry instance (interface).
            logger: Optional logger instance.
        """
        self._provider_registry = provider_registry
        self._logger = logger or logging.getLogger("chhaya.capability_registry")
        self._capabilities: dict[str, CapabilityHandle] = {}
        self._lock = asyncio.Lock()
        self._is_ready = False

    @property
    def name(self) -> str:
        return "capability_registry"

    @property
    def dependencies(self) -> list[str]:
        return ["provider_registry"]

    async def initialize(self) -> None:
        """Called by the LifecycleManager."""
        self._logger.info("Capability Registry initialized.")

    async def start(self) -> None:
        self._is_ready = True

    async def stop(self) -> None:
        self._is_ready = False

    async def shutdown(self) -> None:
        async with self._lock:
            # We must gracefully shutdown all capabilities
            for handle in self._capabilities.values():
                if isinstance(handle.implementation, ILifecycleCapability):
                    try:
                        await handle.implementation.shutdown()
                    except Exception as e:
                        self._logger.error(
                            f"Error shutting down capability {handle.descriptor.id}: {e}"
                        )
            self._capabilities.clear()

    async def health(self) -> HealthReport:
        async with self._lock:
            return HealthReport(is_healthy=True, details={"count": str(len(self._capabilities))})

    def ready(self) -> bool:
        return self._is_ready

    async def register_capability(self, capability: ICapability) -> None:
        """
        Registers a new capability asynchronously.

        Args:
            capability: The concrete capability instance implementing ICapability.

        Raises:
            CapabilityDuplicateError: If a capability with the same ID is already registered.
            CapabilityValidationError: If the capability is missing required fields or metadata.
            ProviderNotFoundError: If the associated provider does not exist.
            CapabilityRegistryError: If initialization fails.
        """
        if not isinstance(capability, ICapability):
            raise CapabilityValidationError(
                "Capability does not implement the ICapability interface."
            )

        descriptor = capability.descriptor

        if not descriptor:
            raise CapabilityValidationError("Capability must provide a descriptor.")

        if not descriptor.id or not descriptor.name:
            raise CapabilityValidationError("Capability descriptor must have an 'id' and 'name'.")

        if not descriptor.version or not isinstance(descriptor.version, CapabilityVersion):
            raise CapabilityValidationError("Capability descriptor must have a valid 'version'.")

        if not descriptor.provider_id:
            raise CapabilityValidationError("Capability descriptor must have a 'provider_id'.")

        if not descriptor.interface:
            raise CapabilityValidationError("Capability descriptor must have an 'interface'.")

        # Validate Provider existence using frozen ProviderRegistry interface
        try:
            # Check if the provider is registered for the given interface.
            self._provider_registry.get_provider(descriptor.interface, descriptor.provider_id)
        except Exception as e:
            # Assuming provider registry raises an exception if not found, we translate it here.
            interface_name = getattr(descriptor.interface, '__name__', descriptor.interface)
            raise ProviderNotFoundError(
                f"Provider '{descriptor.provider_id}' for interface {interface_name} not found: {e}"
            )

        async with self._lock:
            if descriptor.id in self._capabilities:
                raise CapabilityDuplicateError(
                    f"Capability with ID '{descriptor.id}' is already registered."
                )

            handle = CapabilityHandle(descriptor=descriptor, implementation=capability)
            handle.state = CapabilityState.INITIALIZING
            self._capabilities[descriptor.id] = handle

        # Initialize capability if it supports lifecycle hooks
        # This is done outside the registry lock to avoid deadlocks
        if isinstance(capability, ILifecycleCapability):
            try:
                await capability.initialize()
            except Exception as e:
                # Rollback registration
                async with self._lock:
                    if descriptor.id in self._capabilities:
                        del self._capabilities[descriptor.id]
                raise CapabilityRegistryError(
                    f"Failed to initialize capability '{descriptor.id}': {e}"
                )

        async with self._lock:
            # We check if it is still there in case something happened
            if descriptor.id in self._capabilities:
                self._capabilities[descriptor.id].state = CapabilityState.HEALTHY
                self._logger.debug(
                    f"Registered capability '{descriptor.id}' v{descriptor.version}."
                )

    async def unregister_capability(self, capability_id: str) -> None:
        """
        Unregisters an existing capability asynchronously.

        Args:
            capability_id: The ID of the capability to remove.

        Raises:
            CapabilityNotFoundError: If the capability is not registered.
            CapabilityRegistryError: If shutdown fails.
        """
        async with self._lock:
            if capability_id not in self._capabilities:
                raise CapabilityNotFoundError(f"Capability '{capability_id}' not found.")
            handle = self._capabilities[capability_id]

        # Call shutdown outside the lock to prevent deadlocks
        shutdown_error = None
        if isinstance(handle.implementation, ILifecycleCapability):
            try:
                await handle.implementation.shutdown()
            except Exception as e:
                shutdown_error = e
                # Even if shutdown fails, we should still remove it, but we raise an error.

        async with self._lock:
            if capability_id in self._capabilities:
                del self._capabilities[capability_id]
                self._logger.debug(f"Unregistered capability '{capability_id}'.")

        if shutdown_error:
            raise CapabilityRegistryError(f"Capability shutdown failed: {shutdown_error}")

    async def get_capability(self, capability_id: str) -> CapabilityHandle | None:
        """Retrieves a specific capability handle by ID."""
        async with self._lock:
            return self._capabilities.get(capability_id)

    async def get_all_capabilities(self) -> list[CapabilityHandle]:
        """Returns a list of all currently registered capabilities."""
        async with self._lock:
            return list(self._capabilities.values())

    async def find_by_provider(self, provider_id: str) -> list[CapabilityHandle]:
        """Finds all capabilities registered under a specific provider ID."""
        async with self._lock:
            return [
                handle
                for handle in self._capabilities.values()
                if handle.descriptor.provider_id == provider_id
            ]

    async def find_by_tag(self, tag: str) -> list[CapabilityHandle]:
        """Finds all capabilities containing a specific tag in their metadata."""
        async with self._lock:
            return [
                handle
                for handle in self._capabilities.values()
                if tag in handle.descriptor.metadata.tags
            ]
