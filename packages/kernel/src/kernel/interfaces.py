"""
Core Kernel Interfaces.

Contains the frozen protocol definitions that define the architectural boundaries
of the Chhaya Kernel.
"""
from collections.abc import Awaitable, Callable
from typing import Any, Protocol


class Event(Protocol):
    """
    Protocol for the base structure for an event passing through the Chhaya Kernel.
    """
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
    """
    Frozen protocol defining the core Publish/Subscribe architecture of the Kernel.
    """
    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribes a handler to a specific exact topic."""
        ...

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """Unsubscribes a handler from a specific topic."""
        ...

    async def publish(self, event: Event) -> None:
        """Publishes an event to all matching subscribers sequentially."""
        ...
