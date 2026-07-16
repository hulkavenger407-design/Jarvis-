from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kernel.interfaces import IMemoryEngine
else:
    IMemoryEngine = object

from .interfaces import IMemoryBackend
from .models import MemoryRecord, MemorySearchResult, MemoryTier


class MemoryEngine(IMemoryEngine):
    """
    Concrete implementation of the Memory Engine subsystem.
    """

    def __init__(self, backend: IMemoryBackend) -> None:
        self._backend = backend

    async def get_memory(
        self, tier: MemoryTier, namespace: str, key: str
    ) -> MemoryRecord | None:
        return await self._backend.get(tier, namespace, key)

    async def put_memory(self, record: MemoryRecord) -> None:
        await self._backend.put(record)

    async def delete_memory(self, tier: MemoryTier, namespace: str, key: str) -> None:
        await self._backend.delete(tier, namespace, key)

    async def search(
        self, tier: MemoryTier, query: Any, *, limit: int = 10
    ) -> list[MemorySearchResult]:
        return await self._backend.search(tier, query, limit=limit)

    async def clear(
        self, tier: MemoryTier | None = None, namespace: str | None = None
    ) -> None:
        await self._backend.clear(tier, namespace)
