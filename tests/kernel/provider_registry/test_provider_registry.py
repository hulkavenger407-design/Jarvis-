from typing import Any, Protocol, runtime_checkable

import pytest
from kernel.provider_registry import (
    ProviderDuplicateError,
    ProviderMetadata,
    ProviderNotFoundError,
    ProviderRegistry,
    ProviderRegistryError,
    ProviderValidationError,
    StaticProviderDiscovery,
)


@runtime_checkable
class DummyLLMProvider(Protocol):
    def generate(self) -> str: ...


class BaseMockProvider:
    def __init__(self, metadata: ProviderMetadata) -> None:
        self._metadata = metadata

    @property
    def metadata(self) -> ProviderMetadata:
        return self._metadata


class LocalLLM(BaseMockProvider):
    def generate(self) -> str:
        return "local"


class CloudLLM(BaseMockProvider):
    def generate(self) -> str:
        return "cloud"


class LifecycleLLM(BaseMockProvider):
    def __init__(self, metadata: ProviderMetadata) -> None:
        super().__init__(metadata)
        self.initialized = False
        self.shutdown_called = False

    async def initialize(self) -> None:
        self.initialized = True

    async def shutdown(self) -> None:
        self.shutdown_called = True

    def generate(self) -> str:
        return "lifecycle"


class BrokenLifecycleLLM(BaseMockProvider):
    async def initialize(self) -> None:
        raise ValueError("Initialization failed")

    async def shutdown(self) -> None:
        raise ValueError("Shutdown failed")

    def generate(self) -> str:
        return "broken"


@pytest.fixture
def registry() -> ProviderRegistry:
    return ProviderRegistry()


@pytest.mark.asyncio
async def test_register_and_get_provider(registry: ProviderRegistry) -> None:
    metadata = ProviderMetadata(
        id="local_llm_1", name="Local LLM", version="1.0.0", description="A local LLM provider."
    )
    local_llm = LocalLLM(metadata)

    await registry.register_provider(DummyLLMProvider, local_llm)

    # Implicitly set as default because it is the first one registered
    assert registry.get_provider(DummyLLMProvider) is local_llm

    # Can also get by explicit ID
    assert registry.get_provider(DummyLLMProvider, "local_llm_1") is local_llm


@pytest.mark.asyncio
async def test_register_multiple_and_explicit_default(registry: ProviderRegistry) -> None:
    local_metadata = ProviderMetadata(id="local", name="Local", version="1", description="")
    cloud_metadata = ProviderMetadata(id="cloud", name="Cloud", version="1", description="")

    local_llm = LocalLLM(local_metadata)
    cloud_llm = CloudLLM(cloud_metadata)

    await registry.register_provider(DummyLLMProvider, local_llm)
    # Register a second one and force it as the default
    await registry.register_provider(DummyLLMProvider, cloud_llm, set_as_default=True)

    assert registry.get_provider(DummyLLMProvider) is cloud_llm
    assert registry.get_provider(DummyLLMProvider, "local") is local_llm

    providers = registry.get_all_providers(DummyLLMProvider)
    assert len(providers) == 2
    assert local_llm in providers
    assert cloud_llm in providers


@pytest.mark.asyncio
async def test_missing_provider_errors(registry: ProviderRegistry) -> None:
    # 1. Interface completely unknown
    with pytest.raises(ProviderNotFoundError, match="No providers registered for interface"):
        registry.get_provider(DummyLLMProvider)

    metadata = ProviderMetadata(id="local", name="Local", version="1", description="")
    await registry.register_provider(DummyLLMProvider, LocalLLM(metadata))

    # 2. Specific name not found
    with pytest.raises(ProviderNotFoundError, match="not found for interface"):
        registry.get_provider(DummyLLMProvider, "not_real")


@pytest.mark.asyncio
async def test_duplicate_registration_error(registry: ProviderRegistry) -> None:
    metadata = ProviderMetadata(id="local", name="Local", version="1", description="")
    await registry.register_provider(DummyLLMProvider, LocalLLM(metadata))

    with pytest.raises(ProviderDuplicateError, match="is already registered"):
        await registry.register_provider(DummyLLMProvider, LocalLLM(metadata))


@pytest.mark.asyncio
async def test_validation_missing_iprovider(registry: ProviderRegistry) -> None:
    class InvalidProvider:
        def generate(self) -> str:
            return "invalid"

    with pytest.raises(ProviderValidationError, match="does not implement the IProvider interface"):
        await registry.register_provider(DummyLLMProvider, InvalidProvider())


@pytest.mark.asyncio
async def test_validation_missing_metadata_fields(registry: ProviderRegistry) -> None:
    class MissingMetadataProvider(BaseMockProvider):
        @property
        def metadata(self) -> Any:
            # Returning invalid object
            return {"id": "invalid"}

    with pytest.raises(ProviderValidationError, match="is not a valid ProviderMetadata instance"):
        await registry.register_provider(DummyLLMProvider, MissingMetadataProvider(metadata=None)) # type: ignore


@pytest.mark.asyncio
async def test_validation_empty_metadata_id(registry: ProviderRegistry) -> None:
    metadata = ProviderMetadata(id="", name="Name", version="1", description="")

    with pytest.raises(ProviderValidationError, match="must include an 'id' and 'name'"):
        await registry.register_provider(DummyLLMProvider, LocalLLM(metadata))


@pytest.mark.asyncio
async def test_validation_protocol_mismatch(registry: ProviderRegistry) -> None:
    class NotAnLLM(BaseMockProvider):
        def something_else(self) -> str:
            return "not generate"

    metadata = ProviderMetadata(id="not_llm", name="Not LLM", version="1", description="")
    with pytest.raises(ProviderValidationError, match="does not implement the DummyLLMProvider protocol"):
        await registry.register_provider(DummyLLMProvider, NotAnLLM(metadata))


@pytest.mark.asyncio
async def test_lifecycle_hooks(registry: ProviderRegistry) -> None:
    metadata = ProviderMetadata(id="lifecycle", name="Lifecycle", version="1", description="")
    provider = LifecycleLLM(metadata)

    assert not provider.initialized
    await registry.register_provider(DummyLLMProvider, provider)
    assert provider.initialized

    assert not provider.shutdown_called
    await registry.unregister_provider(DummyLLMProvider, "lifecycle")
    assert provider.shutdown_called

    # Verify it is removed
    with pytest.raises(ProviderNotFoundError):
        registry.get_provider(DummyLLMProvider, "lifecycle")


@pytest.mark.asyncio
async def test_lifecycle_initialization_failure(registry: ProviderRegistry) -> None:
    metadata = ProviderMetadata(id="broken", name="Broken", version="1", description="")
    provider = BrokenLifecycleLLM(metadata)

    with pytest.raises(ProviderRegistryError, match="initialization failed"):
        await registry.register_provider(DummyLLMProvider, provider)

    # Should not be registered if init failed
    with pytest.raises(ProviderNotFoundError):
        registry.get_provider(DummyLLMProvider, "broken")


@pytest.mark.asyncio
async def test_lifecycle_shutdown_failure(registry: ProviderRegistry) -> None:
    metadata = ProviderMetadata(id="broken_shutdown", name="Broken", version="1", description="")
    provider = BrokenLifecycleLLM(metadata)
    # Patch initialize so it only fails on shutdown
    async def dummy_init() -> None: pass
    provider.initialize = dummy_init # type: ignore

    await registry.register_provider(DummyLLMProvider, provider)

    with pytest.raises(ProviderRegistryError, match="shutdown failed"):
        await registry.unregister_provider(DummyLLMProvider, "broken_shutdown")

    # Standard behavior when shutdown fails is to STILL remove it from registry
    # to avoid a dirty state, or keep it. Our implementation removes it.
    with pytest.raises(ProviderNotFoundError):
        registry.get_provider(DummyLLMProvider, "broken_shutdown")


@pytest.mark.asyncio
async def test_static_discovery() -> None:
    metadata = ProviderMetadata(id="test1", name="Test1", version="1", description="")
    discovery = StaticProviderDiscovery([metadata])

    providers = await discovery.discover_providers()
    assert len(providers) == 1
    assert providers[0].id == "test1"


@pytest.mark.asyncio
async def test_unregister_default_fallback(registry: ProviderRegistry) -> None:
    p1 = LocalLLM(ProviderMetadata(id="p1", name="P1", version="1", description=""))
    p2 = LocalLLM(ProviderMetadata(id="p2", name="P2", version="1", description=""))

    await registry.register_provider(DummyLLMProvider, p1)
    await registry.register_provider(DummyLLMProvider, p2)

    # p1 is default
    assert registry.get_provider(DummyLLMProvider) is p1

    # unregister p1
    await registry.unregister_provider(DummyLLMProvider, "p1")

    # default should fallback to p2
    assert registry.get_provider(DummyLLMProvider) is p2
