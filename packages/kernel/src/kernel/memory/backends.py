import datetime
from typing import Any

from .interfaces import IMemoryBackend, IVectorStore
from .models import MemoryRecord, MemorySearchResult, MemoryTier


class InMemoryBackend(IMemoryBackend):
    """
    In-memory implementation of the memory backend.
    """

    def __init__(self, vector_store: IVectorStore | None = None) -> None:
        # tier -> namespace -> key -> record
        self._store: dict[MemoryTier, dict[str, dict[str, MemoryRecord]]] = {
            MemoryTier.WORKING: {},
            MemoryTier.SHORT_TERM: {},
            MemoryTier.LONG_TERM: {},
        }
        self._vector_store = vector_store

    def _is_expired(self, record: MemoryRecord) -> bool:
        if record.expires_at is None:
            return False
        return datetime.datetime.now(datetime.UTC) >= record.expires_at

    async def get(self, tier: MemoryTier, namespace: str, key: str) -> MemoryRecord | None:
        record = self._store[tier].get(namespace, {}).get(key)
        if record is None:
            return None
        if self._is_expired(record):
            # Optional: eviction on read
            # await self.delete(tier, namespace, key)
            return None
        return record

    async def put(self, record: MemoryRecord) -> None:
        if record.namespace not in self._store[record.tier]:
            self._store[record.tier][record.namespace] = {}
        self._store[record.tier][record.namespace][record.key] = record

        if record.tier == MemoryTier.LONG_TERM and self._vector_store:
            await self._vector_store.insert(record)

    async def delete(self, tier: MemoryTier, namespace: str, key: str) -> None:
        if namespace in self._store[tier]:
            if key in self._store[tier][namespace]:
                del self._store[tier][namespace][key]
                if not self._store[tier][namespace]:
                    del self._store[tier][namespace]

        if tier == MemoryTier.LONG_TERM and self._vector_store:
            await self._vector_store.delete(key)

    async def search(
        self, tier: MemoryTier, query: Any, limit: int = 10
    ) -> list[MemorySearchResult]:
        if tier == MemoryTier.LONG_TERM and self._vector_store:
            return await self._vector_store.search(query, limit)

        # Naive fallback search for non-vector tiers or when vector_store is missing
        results: list[MemorySearchResult] = []
        for namespace, keys in self._store[tier].items():
            for key, record in keys.items():
                if self._is_expired(record):
                    continue
                # Exact match fallback
                if query == record.value or query == key:
                    results.append(MemorySearchResult(record=record, score=1.0))
                elif isinstance(query, str) and query in str(record.value):
                    results.append(MemorySearchResult(record=record, score=0.8))

        # Sort and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def clear(self, tier: MemoryTier | None = None, namespace: str | None = None) -> None:
        tiers_to_clear = [tier] if tier else list(MemoryTier)

        for t in tiers_to_clear:
            if namespace:
                if namespace in self._store[t]:
                    del self._store[t][namespace]
            else:
                self._store[t].clear()
                if t == MemoryTier.LONG_TERM and self._vector_store:
                    await self._vector_store.clear()
