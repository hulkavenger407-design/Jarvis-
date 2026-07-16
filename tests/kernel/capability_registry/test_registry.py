import asyncio
import logging
from typing import Any
import pytest
from kernel.capability_registry import (
    CapabilityRegistry,
    IProviderRegistry,
    ICapability,
    ILifecycleCapability,
    CapabilityDescriptor,
    CapabilityMetadata,
    CapabilityVersion,
    CapabilityState,
    CapabilityDuplicateError,
    CapabilityNotFoundError,
    CapabilityRegistryError,
    CapabilityValidationError,
    ProviderNotFoundError,
)

class MockProviderRegistry(IProviderRegistry):
    def __init__(self):
        self.providers = {}

    def get_provider(self, interface: Any, provider_id: str | None = None) -> Any:
        if (interface, provider_id) not in self.providers:
            raise Exception("Provider not found")
        return self.providers[(interface, provider_id)]

class DummyInterface:
    pass

class MockCapability(ICapability):
    def __init__(self, descriptor: CapabilityDescriptor):
        self._descriptor = descriptor

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return self._descriptor

class MockLifecycleCapability(MockCapability, ILifecycleCapability):
    def __init__(self, descriptor: CapabilityDescriptor, fail_init=False, fail_shutdown=False):
        super().__init__(descriptor)
        self.initialized = False
        self.shutdown_called = False
        self.fail_init = fail_init
        self.fail_shutdown = fail_shutdown

    async def initialize(self) -> None:
        if self.fail_init:
            raise ValueError("Init failed")
        self.initialized = True

    async def shutdown(self) -> None:
        if self.fail_shutdown:
            raise ValueError("Shutdown failed")
        self.shutdown_called = True


@pytest.fixture
def mock_provider_registry():
    registry = MockProviderRegistry()
    registry.providers[(DummyInterface, "provider1")] = "dummy_provider"
    return registry

@pytest.fixture
def capability_registry(mock_provider_registry):
    return CapabilityRegistry(mock_provider_registry, logger=logging.getLogger("test"))

@pytest.fixture
def dummy_descriptor():
    return CapabilityDescriptor(
        id="cap1",
        name="Capability 1",
        version=CapabilityVersion(1, 0, 0),
        provider_id="provider1",
        interface=DummyInterface,
        metadata=CapabilityMetadata(description="Test")
    )


@pytest.mark.asyncio
async def test_register_and_get_capability(capability_registry, dummy_descriptor):
    cap = MockCapability(dummy_descriptor)
    await capability_registry.register_capability(cap)

    handle = await capability_registry.get_capability("cap1")
    assert handle is not None
    assert handle.descriptor == dummy_descriptor
    assert handle.state == CapabilityState.HEALTHY
    assert handle.implementation == cap

@pytest.mark.asyncio
async def test_duplicate_registration(capability_registry, dummy_descriptor):
    cap = MockCapability(dummy_descriptor)
    await capability_registry.register_capability(cap)

    with pytest.raises(CapabilityDuplicateError):
        await capability_registry.register_capability(cap)

@pytest.mark.asyncio
async def test_validation_errors(capability_registry):
    # Not implementing ICapability
    with pytest.raises(CapabilityValidationError):
        await capability_registry.register_capability(object()) # type: ignore

    # Missing descriptor fields
    class BadCap(ICapability):
        @property
        def descriptor(self):
            return CapabilityDescriptor(id="", name="", version=CapabilityVersion(1,0,0), provider_id="provider1", interface=DummyInterface, metadata=CapabilityMetadata(""))

    with pytest.raises(CapabilityValidationError):
        await capability_registry.register_capability(BadCap())

@pytest.mark.asyncio
async def test_provider_not_found(capability_registry, dummy_descriptor):
    desc = CapabilityDescriptor(
        id="cap2",
        name="Capability 2",
        version=CapabilityVersion(1, 0, 0),
        provider_id="missing_provider",
        interface=DummyInterface,
        metadata=CapabilityMetadata(description="Test")
    )
    cap = MockCapability(desc)

    with pytest.raises(ProviderNotFoundError):
        await capability_registry.register_capability(cap)

@pytest.mark.asyncio
async def test_lifecycle_success(capability_registry, dummy_descriptor):
    cap = MockLifecycleCapability(dummy_descriptor)
    await capability_registry.register_capability(cap)

    assert cap.initialized is True

    await capability_registry.unregister_capability("cap1")
    assert cap.shutdown_called is True

    handle = await capability_registry.get_capability("cap1")
    assert handle is None

@pytest.mark.asyncio
async def test_lifecycle_init_failure(capability_registry, dummy_descriptor):
    cap = MockLifecycleCapability(dummy_descriptor, fail_init=True)

    with pytest.raises(CapabilityRegistryError, match="Failed to initialize capability"):
        await capability_registry.register_capability(cap)

    handle = await capability_registry.get_capability("cap1")
    assert handle is None # Rolled back

@pytest.mark.asyncio
async def test_lifecycle_shutdown_failure(capability_registry, dummy_descriptor):
    cap = MockLifecycleCapability(dummy_descriptor, fail_shutdown=True)
    await capability_registry.register_capability(cap)

    with pytest.raises(CapabilityRegistryError, match="Capability shutdown failed"):
        await capability_registry.unregister_capability("cap1")

    # Should still be removed even if shutdown fails
    handle = await capability_registry.get_capability("cap1")
    assert handle is None

@pytest.mark.asyncio
async def test_get_all_and_find(capability_registry, mock_provider_registry):
    mock_provider_registry.providers[(DummyInterface, "provider2")] = "dummy"

    desc1 = CapabilityDescriptor(id="cap1", name="C1", version=CapabilityVersion(1,0,0), provider_id="provider1", interface=DummyInterface, metadata=CapabilityMetadata("", tags=["a"]))
    desc2 = CapabilityDescriptor(id="cap2", name="C2", version=CapabilityVersion(1,0,0), provider_id="provider1", interface=DummyInterface, metadata=CapabilityMetadata("", tags=["b"]))
    desc3 = CapabilityDescriptor(id="cap3", name="C3", version=CapabilityVersion(1,0,0), provider_id="provider2", interface=DummyInterface, metadata=CapabilityMetadata("", tags=["a"]))

    await capability_registry.register_capability(MockCapability(desc1))
    await capability_registry.register_capability(MockCapability(desc2))
    await capability_registry.register_capability(MockCapability(desc3))

    all_caps = await capability_registry.get_all_capabilities()
    assert len(all_caps) == 3

    prov1_caps = await capability_registry.find_by_provider("provider1")
    assert len(prov1_caps) == 2

    tag_a_caps = await capability_registry.find_by_tag("a")
    assert len(tag_a_caps) == 2

@pytest.mark.asyncio
async def test_concurrent_registration(capability_registry, dummy_descriptor):
    async def register_task(i):
        desc = CapabilityDescriptor(
            id=f"cap{i}",
            name=f"Capability {i}",
            version=CapabilityVersion(1, 0, 0),
            provider_id="provider1",
            interface=DummyInterface,
            metadata=CapabilityMetadata(description="Test")
        )
        cap = MockCapability(desc)
        await capability_registry.register_capability(cap)

    await asyncio.gather(*(register_task(i) for i in range(10)))

    all_caps = await capability_registry.get_all_capabilities()
    assert len(all_caps) == 10

@pytest.mark.asyncio
async def test_registry_lifecycle(capability_registry, dummy_descriptor):
    await capability_registry.start()
    assert capability_registry.ready() is True

    cap = MockLifecycleCapability(dummy_descriptor)
    await capability_registry.register_capability(cap)

    await capability_registry.shutdown()

    assert cap.shutdown_called is True
    assert len(await capability_registry.get_all_capabilities()) == 0
