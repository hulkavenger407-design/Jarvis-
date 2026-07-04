from typing import Protocol, cast

import pytest
from kernel.di import CircularDependencyError, DependencyInjectionError, DIContainer, Lifetime


class DummyInterface(Protocol):
    def get_value(self) -> str: ...


class DummyImpl:
    def get_value(self) -> str:
        return "singleton"


class DummyFactoryImpl:
    def __init__(self) -> None:
        self.counter = 0

    def get_value(self) -> str:
        self.counter += 1
        return f"factory_{self.counter}"


@pytest.fixture
def container() -> DIContainer:
    return DIContainer()


def test_register_and_resolve_singleton(container: DIContainer) -> None:
    impl = DummyImpl()
    container.register_singleton(DummyInterface, impl)

    resolved = container.resolve(DummyInterface)
    assert resolved is impl
    assert resolved.get_value() == "singleton"

    # Resolving again should return the exact same instance
    resolved_again = container.resolve(DummyInterface)
    assert resolved_again is impl


def test_register_and_resolve_lazy_singleton(container: DIContainer) -> None:
    container.register(DummyInterface, lambda: DummyFactoryImpl(), Lifetime.SINGLETON)

    resolved1 = container.resolve(DummyInterface)
    assert resolved1.get_value() == "factory_1"

    # Resolving again should return the exactly same cached instance
    resolved2 = container.resolve(DummyInterface)
    assert resolved1 is resolved2
    assert resolved2.get_value() == "factory_2" # State persists


def test_register_and_resolve_factory(container: DIContainer) -> None:
    def factory() -> DummyInterface:
        return DummyFactoryImpl()

    container.register_factory(DummyInterface, factory)

    resolved1 = container.resolve(DummyInterface)
    assert resolved1.get_value() == "factory_1"

    # Resolving again should return a new instance from the factory
    resolved2 = container.resolve(DummyInterface)
    assert resolved1 is not resolved2
    assert resolved2.get_value() == "factory_1" # fresh counter


def test_resolve_unregistered_interface(container: DIContainer) -> None:
    with pytest.raises(DependencyInjectionError, match="is not registered in the DI Container"):
        container.resolve(DummyInterface)


def test_register_duplicate_interface(container: DIContainer) -> None:
    container.register_singleton(DummyInterface, DummyImpl())

    with pytest.raises(DependencyInjectionError, match="is already registered"):
        container.register_singleton(DummyInterface, DummyImpl())

    with pytest.raises(DependencyInjectionError, match="is already registered"):
        container.register_factory(DummyInterface, lambda: DummyImpl())


def test_circular_dependency(container: DIContainer) -> None:
    class InterfaceA(Protocol): ...
    class InterfaceB(Protocol): ...

    def factory_a() -> InterfaceA:
        return cast(InterfaceA, container.resolve(InterfaceB))

    def factory_b() -> InterfaceB:
        return cast(InterfaceB, container.resolve(InterfaceA))

    container.register(InterfaceA, factory_a, Lifetime.TRANSIENT)
    container.register(InterfaceB, factory_b, Lifetime.TRANSIENT)

    with pytest.raises(CircularDependencyError, match="Circular dependency detected"):
        container.resolve(InterfaceA)


def test_scoped_resolution_stub(container: DIContainer) -> None:
    container.register(DummyInterface, lambda: DummyImpl(), Lifetime.SCOPED)

    with pytest.raises(DependencyInjectionError, match="without a scope_id"):
        container.resolve(DummyInterface)

    resolved = container.resolve(DummyInterface, scope_id="session_123")
    assert isinstance(resolved, DummyImpl)


def test_clear_container(container: DIContainer) -> None:
    container.register_singleton(DummyInterface, DummyImpl())
    container.clear()

    with pytest.raises(DependencyInjectionError):
        container.resolve(DummyInterface)
