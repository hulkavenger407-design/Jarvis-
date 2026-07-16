"""
Provider Registry Subsystem.
"""

import threading
from typing import Any

from kernel.lifecycle import HealthReport, KernelSubsystem

from .errors import (
    ProviderDuplicateError,
    ProviderNotFoundError,
    ProviderRegistryError,
    ProviderValidationError,
)
from .interfaces import ILifecycleProvider, IProvider
from .models import ProviderMetadata


class ProviderRegistry(KernelSubsystem):
    """
    Manages the mapping of abstract Protocol interfaces to concrete providers.
    Provides strict abstraction from underlying technologies.
    """

    def __init__(self) -> None:
        """
        Initializes the Provider Registry.
        """
        self._is_ready = False
        # Dictionary mapping: Interface -> { provider_id -> provider_instance }
        self._providers: dict[Any, dict[str, Any]] = {}
        # Global dictionary of metadata mapping: provider_id -> ProviderMetadata
        self._metadata: dict[str, ProviderMetadata] = {}
        # Dictionary mapping: Interface -> default_provider_id
        self._defaults: dict[Any, str] = {}
        self._lock = threading.RLock()

    async def register_provider(
        self, interface: Any, provider: Any, set_as_default: bool = False
    ) -> None:
        """
        Registers a concrete provider implementation for a specific interface.

        Args:
            interface: The abstract Protocol (e.g., LLMProvider).
            provider: The concrete instance.
            set_as_default: If True, this provider will be the default for the given interface.

        Raises:
            ProviderValidationError: If the provider doesn't implement the required interface
                                     or doesn't expose valid ProviderMetadata.
            ProviderDuplicateError: If a provider with the same ID is already registered for the interface.
        """
        # Validation: Verify provider implements IProvider to get metadata
        if not isinstance(provider, IProvider):
            raise ProviderValidationError(
                "Provider does not implement the IProvider interface (missing valid metadata property)."
            )

        try:
            metadata = provider.metadata
        except Exception as e:
            raise ProviderValidationError(f"Failed to access provider metadata: {e}")

        if not isinstance(metadata, ProviderMetadata):
            raise ProviderValidationError("Provider metadata is not a valid ProviderMetadata instance.")

        if not metadata.id or not metadata.name:
            raise ProviderValidationError("Provider metadata must include an 'id' and 'name'.")

        # Basic Protocol verification - we check if it is instance of the interface if the interface is runtime checkable
        # Since not all protocols might be runtime_checkable, we try to use isinstance and fallback/ignore gracefully
        try:
            if hasattr(interface, "_is_runtime_protocol") and interface._is_runtime_protocol:
                if not isinstance(provider, interface):
                    raise ProviderValidationError(f"Provider does not implement the {interface.__name__} protocol.")
            elif hasattr(interface, "__class__") and getattr(interface, "_is_protocol", False):
                # Fallback for Python versions where runtime_checkable behavior varies
                if not isinstance(provider, interface):
                    raise ProviderValidationError(f"Provider does not implement the {interface.__name__} protocol.")
        except TypeError:
            # If the interface isn't a runtime_checkable protocol, isinstance raises TypeError.
            # We skip strict validation in this case to allow standard types or non-runtime protocols.
            pass

        provider_id = metadata.id

        with self._lock:
            if interface not in self._providers:
                self._providers[interface] = {}

            if provider_id in self._providers[interface]:
                raise ProviderDuplicateError(
                    f"Provider '{provider_id}' is already registered for interface {interface.__name__}."
                )

            # Keep a global mapping of ID to metadata just in case (though it's tied to the instance)
            # A single provider instance might implement multiple interfaces, which is fine.
            self._metadata[provider_id] = metadata
            self._providers[interface][provider_id] = provider

            # Initialize provider if it supports lifecycle hooks
            if isinstance(provider, ILifecycleProvider):
                try:
                    await provider.initialize()
                except Exception as e:
                    # If initialization fails, we must rollback the registration
                    del self._providers[interface][provider_id]
                    # We only remove from global metadata if it's not registered under any other interface
                    if not any(provider_id in self._providers[iface] for iface in self._providers):
                        del self._metadata[provider_id]
                    raise ProviderRegistryError(f"Provider initialization failed: {e}")

            # If it's the first provider for this interface, or explicitly requested, set as default
            if set_as_default or interface not in self._defaults:
                self._defaults[interface] = provider_id

    def get_provider(self, interface: Any, provider_id: str | None = None) -> Any:
        """
        Retrieves a provider for the given interface.

        Args:
            interface: The abstract Protocol.
            provider_id: The specific provider ID to retrieve. If None, returns the default.

        Returns:
            The concrete provider instance.

        Raises:
            ProviderNotFoundError: If the interface or specific provider is not found.
        """
        with self._lock:
            if interface not in self._providers:
                raise ProviderNotFoundError(
                    f"No providers registered for interface {getattr(interface, '__name__', interface)}."
                )

            target_id = provider_id or self._defaults.get(interface)
            if not target_id:
                raise ProviderNotFoundError(f"No default provider configured for {getattr(interface, '__name__', interface)}.")

            provider = self._providers[interface].get(target_id)
            if provider is None:
                raise ProviderNotFoundError(
                    f"Provider '{target_id}' not found for interface {getattr(interface, '__name__', interface)}."
                )

            return provider

    def get_all_providers(self, interface: Any) -> list[Any]:
        """
        Returns a list of all registered provider instances for a given interface.
        """
        with self._lock:
            if interface not in self._providers:
                return []
            return list(self._providers[interface].values())

    async def unregister_provider(self, interface: Any, provider_id: str) -> None:
        """
        Safely unregisters a provider.

        Args:
            interface: The abstract Protocol.
            provider_id: The ID of the provider to unregister.

        Raises:
            ProviderNotFoundError: If the provider is not registered.
            ProviderRegistryError: If the provider fails to shutdown cleanly.
        """
        with self._lock:
            if interface not in self._providers or provider_id not in self._providers[interface]:
                raise ProviderNotFoundError(f"Provider '{provider_id}' is not registered for interface {getattr(interface, '__name__', interface)}.")

            provider = self._providers[interface][provider_id]

        # Call shutdown outside the lock to prevent deadlocks if shutdown is long-running
        shutdown_error = None
        if isinstance(provider, ILifecycleProvider):
            try:
                await provider.shutdown()
            except Exception as e:
                shutdown_error = e

        with self._lock:
            # Check again inside lock just in case it was modified
            if provider_id in self._providers.get(interface, {}):
                del self._providers[interface][provider_id]

                # Cleanup defaults if needed
                if self._defaults.get(interface) == provider_id:
                    if self._providers[interface]:
                        # Pick a new default arbitrarily
                        self._defaults[interface] = next(iter(self._providers[interface].keys()))
                    else:
                        del self._defaults[interface]
                        del self._providers[interface]

                # Remove from global metadata if not registered under any other interface
                if not any(provider_id in self._providers[iface] for iface in self._providers):
                    if provider_id in self._metadata:
                        del self._metadata[provider_id]

        if shutdown_error:
            raise ProviderRegistryError(f"Provider shutdown failed: {shutdown_error}")


    @property
    def name(self) -> str:
        return "provider_registry"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def initialize(self) -> None:
        pass

    async def start(self) -> None:
        self._is_ready = True

    async def stop(self) -> None:
        self._is_ready = False

    async def shutdown(self) -> None:
        # Shutdown all active providers
        with self._lock:
            # We can't await inside lock easily, so let's get them
            interfaces_copy = list(self._providers.keys())

        for interface in interfaces_copy:
            with self._lock:
                provider_ids = list(self._providers.get(interface, {}).keys())

            for pid in provider_ids:
                try:
                    await self.unregister_provider(interface, pid)
                except Exception:
                    pass

    async def health(self) -> HealthReport:
        return HealthReport(is_healthy=True, details={"providers": str(len(self._metadata))})

    def ready(self) -> bool:
        return self._is_ready