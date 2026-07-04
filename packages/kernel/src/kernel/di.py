"""
Dependency Injection Container.

Provides a lightweight, type-safe Dependency Injection (DI) container for the
Chhaya Kernel. Supports registering different lifecycles (Singleton, Transient, Scoped).
"""
import enum
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class DependencyInjectionError(Exception):
    """Raised when a dependency cannot be resolved or is improperly registered."""
    pass


class CircularDependencyError(DependencyInjectionError):
    """Raised when a circular dependency is detected during resolution."""
    pass


class Lifetime(enum.Enum):
    """Defines the lifetime of a registered dependency."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"  # Replaces 'factory' naming for clarity
    SCOPED = "scoped"


class DIContainer:
    """
    A lightweight Dependency Injection Container.
    """

    def __init__(self) -> None:
        self._singletons: dict[Any, Any] = {}
        self._transients: dict[Any, Callable[[], Any]] = {}
        # Scoped resolutions are stubbed for future implementation.
        # They will likely require a scope dictionary: dict[str, dict[Any, Any]]
        self._scoped_factories: dict[Any, Callable[[], Any]] = {}

        # Track resolution paths to detect circular dependencies
        self._resolution_stack: set[Any] = set()

    def register(
        self, interface: Any, factory: Callable[[], T], lifetime: Lifetime = Lifetime.TRANSIENT
    ) -> None:
        """
        Registers a factory function under a specific lifetime.

        Args:
            interface: The type or protocol to register under.
            factory: A callable that returns an instance of the interface.
            lifetime: The Lifetime scope (SINGLETON, TRANSIENT, SCOPED).
        """
        self._check_not_registered(interface)

        if lifetime == Lifetime.SINGLETON:
            # We delay instantiation of singletons until first resolution (lazy)
            self._transients[interface] = factory
            # Mark it so we know to cache it later
            self._singletons[interface] = None
        elif lifetime == Lifetime.TRANSIENT:
            self._transients[interface] = factory
        elif lifetime == Lifetime.SCOPED:
            self._scoped_factories[interface] = factory

    def register_singleton(self, interface: Any, instance: T) -> None:
        """
        Helper method to register a pre-instantiated singleton.
        """
        self._check_not_registered(interface)
        self._singletons[interface] = instance

    def register_factory(self, interface: Any, factory: Callable[[], T]) -> None:
        """
        Helper method for backwards compatibility. Registers as TRANSIENT.
        """
        self.register(interface, factory, Lifetime.TRANSIENT)

    def _check_not_registered(self, interface: Any) -> None:
        if (
            interface in self._singletons
            or interface in self._transients
            or interface in self._scoped_factories
        ):
            raise DependencyInjectionError(f"Interface {interface.__name__} is already registered.")

    def resolve(self, interface: Any, scope_id: str | None = None) -> Any:
        """
        Resolves and returns an instance for the given interface.

        Args:
            interface: The type or protocol to resolve.
            scope_id: Optional ID for resolving SCOPED lifecycles.

        Returns:
            An instance matching the requested interface.

        Raises:
            DependencyInjectionError: If the interface is not registered.
            CircularDependencyError: If a resolution loop is detected.
        """
        # 1. Circular dependency check
        if interface in self._resolution_stack:
            raise CircularDependencyError(
                f"Circular dependency detected resolving: {interface.__name__}"
            )

        self._resolution_stack.add(interface)

        try:
            # 2. Check Singletons
            if interface in self._singletons:
                instance = self._singletons[interface]
                # If it's a lazy singleton (registered via factory), instantiate it now
                if instance is None:
                    factory = self._transients[interface]
                    instance = factory()
                    self._singletons[interface] = instance
                return instance

            # 3. Check Transients
            if interface in self._transients:
                return self._transients[interface]()

            # 4. Check Scoped (Stubbed)
            if interface in self._scoped_factories:
                if not scope_id:
                    raise DependencyInjectionError(
                        f"Cannot resolve scoped dependency {interface.__name__} without a scope_id."
                    )
                # TODO: Implement full scope caching dictionary mapping scope_id -> instances.
                # For now, just generate it like a transient to fulfill the interface contract.
                return self._scoped_factories[interface]()

            raise DependencyInjectionError(
                f"Interface {interface.__name__} is not registered in the DI Container."
            )
        finally:
            # Clean up the resolution stack regardless of success or failure
            self._resolution_stack.remove(interface)

    def clear(self) -> None:
        """Clears all registered dependencies. Useful for testing."""
        self._singletons.clear()
        self._transients.clear()
        self._scoped_factories.clear()
        self._resolution_stack.clear()
