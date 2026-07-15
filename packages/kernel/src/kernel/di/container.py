"""
Dependency Injection Container.

Provides a lightweight, type-safe Dependency Injection (DI) container for the
Chhaya Kernel. Supports registering different lifecycles (Singleton, Transient, Scoped).
"""

from collections.abc import Callable
from typing import Any, TypeVar

from .errors import (
    CircularDependencyError,
    DependencyInjectionError,
    ResolutionError,
    ServiceNotFoundError,
)
from .lifetime import Lifetime

T = TypeVar("T")


class Scope:
    """
    A resolution scope for Scoped dependencies.
    """

    def __init__(self, container: "DIContainer") -> None:
        self._container = container
        self._instances: dict[Any, Any] = {}
        self._disposed = False

    def resolve(self, interface: Any) -> Any:
        """
        Resolves a dependency within this scope.
        """
        if self._disposed:
            raise ResolutionError("Cannot resolve from disposed scope.")

        return self._container._resolve_with_scope(interface, self)

    def dispose(self) -> None:
        """Disposes the scope and its instances."""
        self._instances.clear()
        self._disposed = True

    def __enter__(self) -> "Scope":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.dispose()


class DIContainer:
    """
    A lightweight Dependency Injection Container.
    """

    def __init__(self) -> None:
        self._singletons: dict[Any, Any] = {}
        self._transients: dict[Any, Callable[[], Any]] = {}
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

    def resolve(self, interface: Any) -> Any:
        """
        Resolves and returns an instance for the given interface.
        If the interface is registered as scoped, it raises ResolutionError unless called via Scope.

        Args:
            interface: The type or protocol to resolve.

        Returns:
            An instance matching the requested interface.

        Raises:
            ServiceNotFoundError: If the interface is not registered.
            CircularDependencyError: If a resolution loop is detected.
            ResolutionError: If attempting to resolve a SCOPED dependency without a scope.
        """
        return self._resolve_with_scope(interface, None)

    def _resolve_with_scope(self, interface: Any, scope: Scope | None) -> Any:
        """Internal resolution logic handling scoping."""
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

            # 4. Check Scoped
            if interface in self._scoped_factories:
                if scope is None:
                    raise ResolutionError(
                        f"Cannot resolve scoped {interface.__name__} without scope."
                    )

                if interface not in scope._instances:
                    scope._instances[interface] = self._scoped_factories[interface]()

                return scope._instances[interface]

            raise ServiceNotFoundError(
                f"Interface {interface.__name__} is not registered in the DI Container."
            )
        finally:
            # Clean up the resolution stack regardless of success or failure
            self._resolution_stack.remove(interface)

    def begin_scope(self) -> Scope:
        """
        Creates a new scope for resolving SCOPED dependencies.
        """
        return Scope(self)

    def clear(self) -> None:
        """Clears all registered dependencies. Useful for testing."""
        self._singletons.clear()
        self._transients.clear()
        self._scoped_factories.clear()
        self._resolution_stack.clear()
