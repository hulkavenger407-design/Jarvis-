import pytest
from event_bus.bus import EventBus
from event_bus.models import Event
from kernel.capability_registry import Capability, CapabilityRegistry, CapabilityRegistryError


@pytest.fixture
def registry() -> CapabilityRegistry:
    bus = EventBus()
    return CapabilityRegistry(bus)


@pytest.mark.asyncio
async def test_capability_lifecycle(registry: CapabilityRegistry) -> None:
    cap = Capability(
        name="test_capability",
        version="1.0.0",
        description="A test capability",
        provider_name="test_plugin"
    )

    assert not registry.has_capability("test_capability")

    await registry.register_capability(cap)
    assert registry.has_capability("test_capability")

    fetched = registry.get_capability("test_capability")
    assert fetched == cap

    await registry.unregister_capability("test_capability")
    assert not registry.has_capability("test_capability")
    assert registry.get_capability("test_capability") is None


@pytest.mark.asyncio
async def test_duplicate_registration(registry: CapabilityRegistry) -> None:
    cap = Capability(name="core_cap", version="1.0.0")

    await registry.register_capability(cap)

    with pytest.raises(CapabilityRegistryError, match="is already registered"):
        await registry.register_capability(cap)


@pytest.mark.asyncio
async def test_list_capabilities(registry: CapabilityRegistry) -> None:
    cap1 = Capability(name="cap1", version="1.0.0")
    cap2 = Capability(name="cap2", version="1.0.0")

    await registry.register_capability(cap1)
    await registry.register_capability(cap2)

    caps = registry.list_capabilities()
    assert len(caps) == 2
    assert cap1 in caps
    assert cap2 in caps


@pytest.mark.asyncio
async def test_event_publishing() -> None:
    bus = EventBus()
    registry = CapabilityRegistry(bus)

    events_seen = []

    async def capture(e: Event) -> None:
        events_seen.append(e.type)

    bus.subscribe("capability.*", capture)

    cap = Capability(name="event_cap", version="1.0.0")
    await registry.register_capability(cap)
    await registry.unregister_capability("event_cap")

    assert events_seen == [
        "capability.register.started",
        "capability.register.completed",
        "capability.unregister.completed"
    ]


@pytest.mark.asyncio
async def test_health_report(registry: CapabilityRegistry) -> None:
    cap = Capability(name="health_cap", version="1.0.0")
    await registry.register_capability(cap)

    report = await registry.health()
    assert report.is_healthy is True
    assert report.details["count"] == "1"


def test_subsystem_properties(registry: CapabilityRegistry) -> None:
    assert registry.name == "capability_registry"
    assert "event_bus" in registry.dependencies
    assert registry.ready() is True
