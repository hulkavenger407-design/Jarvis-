"""
Dependency Injection Container.

Provides a lightweight, type-safe Dependency Injection (DI) container for the
Chhaya Kernel. Supports registering singletons and factories.
"""
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

class DependencyInjectionError(Exception):
    """Raised when a dependency cannot be resolved or is improperly registered."""
    pass


class DIContainer:
    """
    A lightweight Dependency Injection Container.
    """

    def __init__(self) -> None:
        self._singletons: dict[type[Any], Any] = {}
        self._factories: dict[type[Any], Callable[[], Any]] = {}

    def register_singleton(self, interface: Any, instance: T) -> None:
        """
        Registers an instance as a singleton for the given interface.

        Args:
            interface: The type or protocol to register under.
            instance: The concrete instance to return when requested.
        """
        if interface in self._singletons or interface in self._factories:
            raise DependencyInjectionError(f"Interface {interface.__name__} is already registered.")
        self._singletons[interface] = instance

    def register_factory(self, interface: Any, factory: Callable[[], T]) -> None:
        """
        Registers a factory function that will be called each time the dependency is requested.

        Args:
            interface: The type or protocol to register under.
            factory: A callable that returns an instance of the interface.
        """
        if interface in self._singletons or interface in self._factories:
            raise DependencyInjectionError(f"Interface {interface.__name__} is already registered.")
        self._factories[interface] = factory

    def resolve(self, interface: Any) -> Any:
        """
        Resolves and returns an instance for the given interface.

        Args:
            interface: The type or protocol to resolve.

        Returns:
            An instance matching the requested interface.

        Raises:
            DependencyInjectionError: If the interface is not registered.
        """
        if interface in self._singletons:
            return self._singletons[interface]

        if interface in self._factories:
            return self._factories[interface]()

        raise DependencyInjectionError(
            f"Interface {interface.__name__} is not registered in the DI Container."
        )

    def clear(self) -> None:
        """Clears all registered dependencies. Useful for testing."""
        self._singletons.clear()
        self._factories.clear()
