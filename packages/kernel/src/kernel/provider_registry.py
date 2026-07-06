"""
Provider Registry Subsystem.

The hardware/service abstraction layer mapping abstract interfaces
to their concrete injected implementations.
"""

from collections.abc import Sequence
from typing import Any

from .capability_registry import Capability, CapabilityRegistry
from .di import DependencyInjectionError, DIContainer
from .lifecycle import HealthReport, KernelSubsystem


class ProviderRegistryError(Exception):
    """Raised when a provider cannot be registered or resolved."""

    pass


class ProviderRegistry(KernelSubsystem):
    """
    Manages the mapping of abstract Protocol interfaces to concrete providers.
    Provides strict abstraction from underlying technologies.
    """

    def __init__(
        self, di_container: DIContainer, capability_registry: CapabilityRegistry | None = None
    ) -> None:
        """
        Initializes the Provider Registry.

        Args:
            di_container: The central Dependency Injection container for the Kernel.
            capability_registry: The registry for exposing provider capabilities.
        """
        self._di = di_container
        self._cap_registry = capability_registry
        # Dictionary mapping: Interface -> { "name": instance }
        self._providers: dict[Any, dict[str, Any]] = {}
        # Dictionary mapping: Interface -> "name_of_default_provider"
        self._defaults: dict[Any, str] = {}

    @property
    def name(self) -> str:
        return "provider_registry"

    @property
    def dependencies(self) -> list[str]:
        return ["di_container", "capability_registry"]

    async def initialize(self) -> None:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health(self) -> HealthReport:
        return HealthReport(is_healthy=True)

    def ready(self) -> bool:
        return True

    async def register_provider(
        self, interface: Any, name: str, provider: Any, set_as_default: bool = False
    ) -> None:
        """
        Registers a concrete provider implementation for a specific interface.

        Args:
            interface: The abstract Protocol (e.g., LLMProvider).
            name: A unique string identifier for this provider (e.g., "ollama").
            provider: The concrete instance.
            set_as_default: If True, this provider will be bound to the DI container natively.
        """
        if interface not in self._providers:
            self._providers[interface] = {}

        if name in self._providers[interface]:
            raise ProviderRegistryError(
                f"Provider '{name}' is already registered for interface {interface.__name__}."
            )

        self._providers[interface][name] = provider

        # If the provider exposes capabilities, register them dynamically
        if self._cap_registry and hasattr(provider, "provided_capabilities"):
            for cap_name in provider.provided_capabilities:
                try:
                    cap = Capability(
                        name=cap_name,
                        version="1.0.0",  # Default if provider doesn't specify
                        provider_name=name,
                        description=f"Auto-registered capability from provider {name}",
                    )
                    await self._cap_registry.register_capability(cap)
                except Exception:
                    pass

        # If it's the first provider for this interface, or explicitly requested, set as default
        if set_as_default or interface not in self._defaults:
            self._defaults[interface] = name
            # Bind the default directly into the DI container
            # (Note: di_container.register_singleton raises an error if already registered,
            # so we bypass or clear it. To keep DI clean, we use a factory.
            # if we implement a DI overwrite, but DI doesn't currently support overwrite.
            # We will handle this by injecting a factory into DI that queries this registry.)

            # To avoid tightly coupling or hacking the DI container, we tell the DI container
            # that whenever `interface` is requested, it should ask the Registry for the default.

            def default_factory() -> Any:
                return self.get_provider(interface)

            try:
                self._di.register_factory(interface, default_factory)
            except DependencyInjectionError:
                # If it's already registered in the DI container (perhaps by a previous default),
                # we let the existing factory continue to pull from `get_provider`.
                pass

    def get_provider(self, interface: Any, name: str | None = None) -> Any:
        """
        Retrieves a provider for the given interface.

        Args:
            interface: The abstract Protocol.
            name: The specific provider name to retrieve. If None, returns the default.

        Returns:
            The concrete provider instance.

        Raises:
            ProviderRegistryError: If the interface or specific provider is not found.
        """
        if interface not in self._providers:
            raise ProviderRegistryError(
                f"No providers registered for interface {interface.__name__}."
            )

        target_name = name or self._defaults.get(interface)
        if not target_name:
            raise ProviderRegistryError(f"No default provider configured for {interface.__name__}.")

        provider = self._providers[interface].get(target_name)
        if provider is None:
            raise ProviderRegistryError(
                f"Provider '{target_name}' not found for interface {interface.__name__}."
            )

        return provider

    def get_all_providers(self, interface: Any) -> Sequence[str]:
        """
        Returns a list of all registered provider names for a given interface.
        """
        if interface not in self._providers:
            return []
        return list(self._providers[interface].keys())
