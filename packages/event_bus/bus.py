"""
Event Bus

Central event-driven communication hub for the Chhaya System.
"""
from collections.abc import Callable
from typing import Any


class EventBus:
    """A simple event bus abstraction."""
    def __init__(self) -> None:
        self.listeners: dict[str, list[Callable[..., Any]]] = {}

    def subscribe(self, event_type: str, listener: Callable[..., Any]) -> None:
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)

    def publish(self, event_type: str, *args: Any, **kwargs: Any) -> None:
        for listener in self.listeners.get(event_type, []):
            listener(*args, **kwargs)
