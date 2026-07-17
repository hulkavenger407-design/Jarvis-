"""
Frozen Kernel Interfaces.

These are the immutable architectural foundations of the Chhaya AI OS.
Any change to these interfaces requires an Architecture Decision Record (ADR).
"""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from .memory.models import MemoryRecord, MemorySearchResult, MemoryTier


class Event(Protocol):
    """Protocol describing the base event structure."""

    type: str
    version: str
    payload: dict[str, Any]
    id: str
    timestamp: str
    source: str
    session_id: str | None

    @property
    def is_cancelled(self) -> bool:
        ...

    def cancel(self) -> None:
        ...


EventHandler = Callable[[Event], Any | Awaitable[Any]]


class IEventBus(Protocol):
    """Frozen Event Bus interface."""

    async def publish(self, event: Event) -> None:
        ...

    def subscribe(
        self,
        topic: str,
        handler: EventHandler,
        priority: int = 100,
    ) -> None:
        ...

    def unsubscribe(
        self,
        topic: str,
        handler: EventHandler,
    ) -> None:
        ...


class IStateManager(Protocol):
    """Frozen State Manager interface."""

    async def get_state(self, category: Any, key: str) -> Any | None:
        ...

    async def set_state(self, category: Any, key: str, value: Any) -> None:
        ...

    async def delete_state(self, category: Any, key: str) -> None:
        ...


class IMemoryEngine(Protocol):
    """Frozen Memory Engine interface."""

    async def get_memory(
        self,
        tier: MemoryTier,
        namespace: str,
        key: str,
    ) -> MemoryRecord | None:
        ...

    async def put_memory(
        self,
        record: MemoryRecord,
    ) -> None:
        ...

    async def delete_memory(
        self,
        tier: MemoryTier,
        namespace: str,
        key: str,
    ) -> None:
        ...

    async def search(
        self,
        tier: MemoryTier,
        query: Any,
        *,
        limit: int = 10,
    ) -> list[MemorySearchResult]:
        ...

    async def clear(
        self,
        tier: MemoryTier | None = None,
        namespace: str | None = None,
    ) -> None:
        ...

class IAgentRuntime(Protocol):
    """Frozen Agent Runtime interface."""

    async def initialize(self) -> None:
        ...

    async def shutdown(self) -> None:
        ...

    async def start(self) -> None:
        ...

    async def stop(self) -> None:
        ...

    async def execute(
        self,
        agent_id: str,
        capability: str,
        payload: Any,
    ) -> Any:
        ...

    async def register_agent(
        self,
        agent: Any,
    ) -> None:
        ...

    async def unregister_agent(
        self,
        agent_id: str,
    ) -> None:
        ...

    async def get_agent(
        self,
        agent_id: str,
    ) -> Any | None:
        ...

    async def list_agents(self) -> list[Any]:
        ...
