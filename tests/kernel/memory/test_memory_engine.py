import datetime
import pytest

from kernel.memory.backends import InMemoryBackend
from kernel.memory.engine import MemoryEngine
from kernel.memory.models import MemoryRecord, MemorySearchResult, MemoryTier
from kernel.memory.vector_store import StubVectorStore


@pytest.fixture
def memory_engine() -> MemoryEngine:
    backend = InMemoryBackend()
    return MemoryEngine(backend)


@pytest.fixture
def memory_engine_with_vector() -> MemoryEngine:
    vector_store = StubVectorStore()
    backend = InMemoryBackend(vector_store)
    return MemoryEngine(backend)


@pytest.mark.asyncio
async def test_put_and_get_memory(memory_engine: MemoryEngine) -> None:
    record = MemoryRecord(
        tier=MemoryTier.WORKING, namespace="default", key="foo", value="bar"
    )
    await memory_engine.put_memory(record)

    retrieved = await memory_engine.get_memory(MemoryTier.WORKING, "default", "foo")
    assert retrieved is not None
    assert retrieved.value == "bar"


@pytest.mark.asyncio
async def test_get_nonexistent_memory(memory_engine: MemoryEngine) -> None:
    retrieved = await memory_engine.get_memory(MemoryTier.WORKING, "default", "missing")
    assert retrieved is None


@pytest.mark.asyncio
async def test_delete_memory(memory_engine: MemoryEngine) -> None:
    record = MemoryRecord(
        tier=MemoryTier.WORKING, namespace="default", key="foo", value="bar"
    )
    await memory_engine.put_memory(record)

    await memory_engine.delete_memory(MemoryTier.WORKING, "default", "foo")
    retrieved = await memory_engine.get_memory(MemoryTier.WORKING, "default", "foo")
    assert retrieved is None


@pytest.mark.asyncio
async def test_memory_ttl_expiration(memory_engine: MemoryEngine) -> None:
    # Create record that expired 1 hour ago
    expired_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    record = MemoryRecord(
        tier=MemoryTier.SHORT_TERM,
        namespace="cache",
        key="temp",
        value="data",
        expires_at=expired_time,
    )
    await memory_engine.put_memory(record)

    # Retrieval should return None since it's expired
    retrieved = await memory_engine.get_memory(MemoryTier.SHORT_TERM, "cache", "temp")
    assert retrieved is None


@pytest.mark.asyncio
async def test_memory_ttl_active(memory_engine: MemoryEngine) -> None:
    # Create record expiring 1 hour in the future
    future_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
    record = MemoryRecord(
        tier=MemoryTier.SHORT_TERM,
        namespace="cache",
        key="temp",
        value="data",
        expires_at=future_time,
    )
    await memory_engine.put_memory(record)

    # Retrieval should work
    retrieved = await memory_engine.get_memory(MemoryTier.SHORT_TERM, "cache", "temp")
    assert retrieved is not None
    assert retrieved.value == "data"


@pytest.mark.asyncio
async def test_search_memory_fallback(memory_engine: MemoryEngine) -> None:
    # Test fallback search when no vector store is available
    await memory_engine.put_memory(
        MemoryRecord(tier=MemoryTier.LONG_TERM, namespace="kb", key="1", value="apple")
    )
    await memory_engine.put_memory(
        MemoryRecord(tier=MemoryTier.LONG_TERM, namespace="kb", key="2", value="banana")
    )

    results = await memory_engine.search(MemoryTier.LONG_TERM, "apple")
    assert len(results) == 1
    assert results[0].record.key == "1"


@pytest.mark.asyncio
async def test_search_memory_vector_store(memory_engine_with_vector: MemoryEngine) -> None:
    # The stub vector store always returns empty results for search
    await memory_engine_with_vector.put_memory(
        MemoryRecord(tier=MemoryTier.LONG_TERM, namespace="kb", key="1", value="apple")
    )
    results = await memory_engine_with_vector.search(MemoryTier.LONG_TERM, "apple")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_clear_all_memory(memory_engine: MemoryEngine) -> None:
    await memory_engine.put_memory(
        MemoryRecord(tier=MemoryTier.WORKING, namespace="ns1", key="k1", value="v1")
    )
    await memory_engine.put_memory(
        MemoryRecord(tier=MemoryTier.SHORT_TERM, namespace="ns2", key="k2", value="v2")
    )

    await memory_engine.clear()

    assert await memory_engine.get_memory(MemoryTier.WORKING, "ns1", "k1") is None
    assert await memory_engine.get_memory(MemoryTier.SHORT_TERM, "ns2", "k2") is None


@pytest.mark.asyncio
async def test_clear_specific_tier(memory_engine: MemoryEngine) -> None:
    await memory_engine.put_memory(
        MemoryRecord(tier=MemoryTier.WORKING, namespace="ns1", key="k1", value="v1")
    )
    await memory_engine.put_memory(
        MemoryRecord(tier=MemoryTier.SHORT_TERM, namespace="ns2", key="k2", value="v2")
    )

    await memory_engine.clear(tier=MemoryTier.WORKING)

    assert await memory_engine.get_memory(MemoryTier.WORKING, "ns1", "k1") is None
    assert await memory_engine.get_memory(MemoryTier.SHORT_TERM, "ns2", "k2") is not None


@pytest.mark.asyncio
async def test_clear_specific_namespace(memory_engine: MemoryEngine) -> None:
    await memory_engine.put_memory(
        MemoryRecord(tier=MemoryTier.WORKING, namespace="ns1", key="k1", value="v1")
    )
    await memory_engine.put_memory(
        MemoryRecord(tier=MemoryTier.WORKING, namespace="ns2", key="k2", value="v2")
    )

    await memory_engine.clear(tier=MemoryTier.WORKING, namespace="ns1")

    assert await memory_engine.get_memory(MemoryTier.WORKING, "ns1", "k1") is None
    assert await memory_engine.get_memory(MemoryTier.WORKING, "ns2", "k2") is not None

import asyncio

@pytest.mark.asyncio
async def test_concurrent_memory_access(memory_engine: MemoryEngine) -> None:
    async def writer(i: int) -> None:
        record = MemoryRecord(
            tier=MemoryTier.WORKING, namespace="concurrent", key=str(i), value=f"val_{i}"
        )
        await memory_engine.put_memory(record)

    async def reader(i: int) -> None:
        # A simple read operation
        await memory_engine.get_memory(MemoryTier.WORKING, "concurrent", str(i))

    tasks = []
    for i in range(100):
        tasks.append(asyncio.create_task(writer(i)))
        tasks.append(asyncio.create_task(reader(i)))

    await asyncio.gather(*tasks)

    # Verify everything was written
    for i in range(100):
        retrieved = await memory_engine.get_memory(MemoryTier.WORKING, "concurrent", str(i))
        assert retrieved is not None
        assert retrieved.value == f"val_{i}"
