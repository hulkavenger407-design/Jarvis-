"""
Frozen Kernel Interfaces

These are the immutable architectural foundations of the Chhaya AI OS.
Any change to these interfaces requires an Architecture Decision Record (ADR).
"""
from typing import Any, Protocol


class IEventBus(Protocol):
    """Event Bus protocol for exact-once event delivery."""
    async def publish(self, event: Any) -> None:
        ...

    def subscribe(self, topic: str, handler: Any, priority: int = 100) -> None:
        ...

    def unsubscribe(self, topic: str, handler: Any) -> None:
        ...


class IStateManager(Protocol):
    """State Manager protocol for transactional state persistence."""
    async def get_state(self, category: Any, key: str) -> Any | None:
        ...

    async def set_state(self, category: Any, key: str, value: Any) -> None:
        ...

    async def delete_state(self, category: Any, key: str) -> None:
        ...


class IMemoryEngine(Protocol):
    """Memory Engine protocol for persistent, multi-tiered memory storage."""
    pass
