"""
Asynchronous Event Bus for the Chhaya Kernel.
"""
from typing import Any

from ..interfaces import IEventBus
from .dispatcher import Dispatcher
from .subscriptions import EventHandler, SubscriptionManager


class EventBus(IEventBus):
    """
    Event Bus for routing events through the Chhaya Kernel.
    """

    def __init__(self) -> None:
        self._subscription_manager = SubscriptionManager()
        self._dispatcher = Dispatcher()

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """
        Subscribes a handler to a specific exact topic.
        """
        self._subscription_manager.subscribe(topic, handler)

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """
        Unsubscribes a handler from a specific topic.
        """
        self._subscription_manager.unsubscribe(topic, handler)

    async def publish(self, event: Any) -> None:
        """
        Publishes an event to all matching subscribers sequentially.
        """
        handlers = self._subscription_manager.get_handlers(event.type)
        await self._dispatcher.dispatch(event, handlers)
