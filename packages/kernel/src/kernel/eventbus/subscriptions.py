"""
Subscription Manager for the Event Bus.
"""
from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias

from .models import Event

# A handler can be either sync or async, taking an Event and returning nothing.
EventHandler: TypeAlias = Callable[[Event], Any | Awaitable[Any]]

class SubscriptionManager:
    """
    Manages event subscribers.
    Currently supports exact topic matching only for Milestone 0.
    """
    def __init__(self) -> None:
        # Dictionary mapping exact topic strings to lists of handlers
        self._subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """
        Subscribes a handler to a specific exact topic.
        """
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """
        Unsubscribes a handler from a specific topic.
        """
        if topic in self._subscribers:
            self._subscribers[topic] = [
                h for h in self._subscribers[topic] if h != handler
            ]
            if not self._subscribers[topic]:
                del self._subscribers[topic]

    def get_handlers(self, topic: str) -> list[EventHandler]:
        """
        Retrieves all handlers registered for a given topic.
        Currently only performs exact matches.
        """
        # A copy is returned to avoid concurrent modification issues during iteration
        return list(self._subscribers.get(topic, []))
