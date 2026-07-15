"""
Frozen Kernel Interfaces.

These are the immutable architectural foundations of the Chhaya AI OS.
Any change to these interfaces requires an Architecture Decision Record (ADR).
"""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol


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

    ...