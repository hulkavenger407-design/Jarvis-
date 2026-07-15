from typing import Any, Protocol

from .models import MemoryRecord, MemorySearchResult, MemoryTier


class IVectorStore(Protocol):
    """Abstraction for a vector store used for long-term memory."""

    async def search(self, query: Any, limit: int = 10) -> list[MemorySearchResult]:
        ...

    async def insert(self, record: MemoryRecord) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def clear(self) -> None:
        ...


class IMemoryBackend(Protocol):
    """Abstraction for the core memory storage engine."""

    async def get(self, tier: MemoryTier, namespace: str, key: str) -> MemoryRecord | None:
        ...

    async def put(self, record: MemoryRecord) -> None:
        ...

    async def delete(self, tier: MemoryTier, namespace: str, key: str) -> None:
        ...

    async def search(
        self, tier: MemoryTier, query: Any, limit: int = 10
    ) -> list[MemorySearchResult]:
        ...

    async def clear(self, tier: MemoryTier | None = None, namespace: str | None = None) -> None:
        ...
