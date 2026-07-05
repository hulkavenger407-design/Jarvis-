from typing import Protocol

import pytest
from kernel.di import DIContainer
from kernel.provider_registry import ProviderRegistry, ProviderRegistryError


class DummyLLMProvider(Protocol):
    def generate(self) -> str: ...


class LocalLLM:
    def generate(self) -> str:
        return "local"


class CloudLLM:
    def generate(self) -> str:
        return "cloud"


@pytest.fixture
def registry() -> ProviderRegistry:
    di = DIContainer()
    return ProviderRegistry(di)


@pytest.mark.asyncio
async def test_register_and_get_provider(registry: ProviderRegistry) -> None:
    local_llm = LocalLLM()
    await registry.register_provider(DummyLLMProvider, "local", local_llm)

    # Implicitly set as default because it is the first one registered
    assert registry.get_provider(DummyLLMProvider) is local_llm

    # Can also get by name explicitly
    assert registry.get_provider(DummyLLMProvider, "local") is local_llm


@pytest.mark.asyncio
async def test_register_multiple_and_explicit_default(registry: ProviderRegistry) -> None:
    local_llm = LocalLLM()
    cloud_llm = CloudLLM()

    await registry.register_provider(DummyLLMProvider, "local", local_llm)
    # Register a second one and force it as the default
    await registry.register_provider(DummyLLMProvider, "cloud", cloud_llm, set_as_default=True)

    assert registry.get_provider(DummyLLMProvider) is cloud_llm
    assert registry.get_provider(DummyLLMProvider, "local") is local_llm

    providers = registry.get_all_providers(DummyLLMProvider)
    assert set(providers) == {"local", "cloud"}


@pytest.mark.asyncio
async def test_di_container_integration() -> None:
    di = DIContainer()
    registry = ProviderRegistry(di)

    local_llm = LocalLLM()
    cloud_llm = CloudLLM()

    await registry.register_provider(DummyLLMProvider, "local", local_llm)
    await registry.register_provider(DummyLLMProvider, "cloud", cloud_llm, set_as_default=True)

    # DI should resolve the default provider
    resolved_llm = di.resolve(DummyLLMProvider)
    assert resolved_llm is cloud_llm


@pytest.mark.asyncio
async def test_missing_provider_errors(registry: ProviderRegistry) -> None:
    # 1. Interface completely unknown
    with pytest.raises(ProviderRegistryError, match="No providers registered for interface"):
        registry.get_provider(DummyLLMProvider)

    await registry.register_provider(DummyLLMProvider, "local", LocalLLM())

    # 2. Specific name not found
    with pytest.raises(ProviderRegistryError, match="not found for interface"):
        registry.get_provider(DummyLLMProvider, "not_real")


@pytest.mark.asyncio
async def test_duplicate_registration_error(registry: ProviderRegistry) -> None:
    await registry.register_provider(DummyLLMProvider, "local", LocalLLM())

    with pytest.raises(ProviderRegistryError, match="is already registered"):
        await registry.register_provider(DummyLLMProvider, "local", LocalLLM())
