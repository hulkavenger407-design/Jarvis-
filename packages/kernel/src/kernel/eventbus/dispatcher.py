"""
Event Dispatcher for the Event Bus.
"""
import asyncio
import inspect

from .models import Event
from .subscriptions import EventHandler


class Dispatcher:
    """
    Handles asynchronous event dispatching.
    Isolates exceptions in subscribers to ensure one failure doesn't block others.
    """

    def __init__(self) -> None:
        pass

    async def dispatch(self, event: Event, handlers: list[EventHandler]) -> None:
        """
        Dispatches an event to a list of handlers sequentially to guarantee FIFO order.
        """
        for handler in handlers:
            if event.is_cancelled:
                self._record_telemetry("event_cancelled", event.id)
                break

            await self._execute_safely(handler, event)

    async def _execute_safely(self, handler: EventHandler, event: Event) -> None:
        """
        Executes a single handler, catching any exceptions to isolate failures.
        """
        try:
            if inspect.iscoroutinefunction(handler):
                await handler(event)
            else:
                await asyncio.to_thread(handler, event)
        except Exception as e:
            # Isolate failures and continue dispatching
            msg = f"Event {event.id} handler {handler.__name__} failed: {e}"
            self._record_telemetry("dispatch_error", msg)

    def _record_telemetry(self, event_name: str, message: str) -> None:
        """
        No-op telemetry hook.
        To be replaced or integrated with a real Kernel Telemetry system later.
        """
        pass
