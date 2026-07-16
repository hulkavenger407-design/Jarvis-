from typing import Any

from .interfaces import IVectorStore
from .models import MemoryRecord, MemorySearchResult


class StubVectorStore(IVectorStore):
    """Stub implementation of a vector store."""

    async def search(self, query: Any, limit: int = 10) -> list[MemorySearchResult]:
        """Stub search always returns empty list."""
        return []

    async def insert(self, record: MemoryRecord) -> None:
        """Stub insert does nothing."""
        pass

    async def delete(self, key: str) -> None:
        """Stub delete does nothing."""
        pass

    async def clear(self) -> None:
        """Stub clear does nothing."""
        pass
