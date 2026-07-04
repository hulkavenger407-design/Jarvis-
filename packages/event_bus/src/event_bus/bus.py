"""
Event Bus Subsystem.

Provides an asynchronous Publish/Subscribe messaging architecture for the
Chhaya Kernel, supporting wildcard topics, priorities, and graceful isolation.
"""
import asyncio
import inspect
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeAlias

from .models import Event

# A handler can be either sync or async, taking an Event and returning nothing.
EventHandler: TypeAlias = Callable[[Event], Any | Awaitable[Any]]


class Middleware(Protocol):
    """Protocol for Event Bus Middleware (tracing, logging, mutating)."""
    async def __call__(self, event: Event, next_call: Callable[[Event], Awaitable[None]]) -> None:
        ...


class EventBusError(Exception):
    """Base exception for Event Bus errors."""
    pass


class EventBus:
    """
    Asynchronous Event Bus for the Chhaya Kernel.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        # Dictionary mapping exact topic strings to lists of (priority, handler)
        self._subscribers: dict[str, list[tuple[int, EventHandler]]] = {}

        # List of (compiled_regex, priority, handler) for wildcard topics (e.g. "agent.*")
        self._wildcard_subscribers: list[tuple[re.Pattern[str], int, EventHandler]] = []

        # Ordered list of middleware
        self._middlewares: list[Middleware] = []

        self._logger = logger or logging.getLogger("chhaya.event_bus")

    def use(self, middleware: Middleware) -> None:
        """Appends a middleware to the execution pipeline."""
        self._middlewares.append(middleware)

    def subscribe(self, topic: str, handler: EventHandler, priority: int = 100) -> None:
        """
        Subscribes a handler to a specific topic or wildcard.

        Args:
            topic: The event type to listen for. Supports '*' for wildcards (e.g., 'agent.*').
            handler: A synchronous or asynchronous callable that accepts an Event.
            priority: Execution priority. Lower numbers execute FIRST.
        """
        if "*" in topic:
            # Convert simple wildcard "agent.*" into regex "^agent\..*$"
            pattern_str = "^" + topic.replace(".", r"\.").replace("*", ".*") + "$"
            compiled = re.compile(pattern_str)
            self._wildcard_subscribers.append((compiled, priority, handler))
            # Sort wildcard subscribers by priority (lowest number first)
            self._wildcard_subscribers.sort(key=lambda x: x[1])
        else:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append((priority, handler))
            self._subscribers[topic].sort(key=lambda x: x[0])

    async def publish(self, event: Event) -> None:
        """
        Publishes an event through the middleware pipeline and to all matching subscribers.
        Subscribers are executed sequentially to respect priority and cancellation, but order of initiation
        respects priority.

        Args:
            event: The Event object to publish.
        """
        # 1. Build the middleware chain
        async def execute_subscribers(e: Event) -> None:
            if e.is_cancelled:
                return
            await self._dispatch_to_subscribers(e)

        chain: Callable[[Event], Awaitable[None]] = execute_subscribers
        for middleware in reversed(self._middlewares):
            chain = self._wrap_middleware(middleware, chain)

        # 2. Execute the pipeline
        try:
            await chain(event)
        except Exception as e:
            self._logger.error(f"EventBus critical failure processing event {event.id}: {e}")

    def _wrap_middleware(
        self, middleware: Middleware, next_call: Callable[[Event], Awaitable[None]]
    ) -> Callable[[Event], Awaitable[None]]:
        """Helper to create closure chain for middleware."""
        async def wrapped(e: Event) -> None:
            await middleware(e, next_call)
        return wrapped

    async def _dispatch_to_subscribers(self, event: Event) -> None:
        """Internal method to gather and execute all matching handlers."""
        # Gather exact matches
        handlers: list[tuple[int, EventHandler]] = list(self._subscribers.get(event.type, []))

        # Gather wildcard matches
        for pattern, priority, handler in self._wildcard_subscribers:
            if pattern.match(event.type):
                handlers.append((priority, handler))

        # Re-sort combined list by priority
        handlers.sort(key=lambda x: x[0])

        # Execute handlers sequentially by priority, but wrap them in tasks to isolate errors
        for _, handler in handlers:
            if event.is_cancelled:
                self._logger.debug(f"Event {event.id} cancelled. Stopping propagation.")
                break

            await self._execute_handler_safely(handler, event)

    async def _execute_handler_safely(self, handler: EventHandler, event: Event) -> None:
        """Executes a single handler, catching any exceptions to isolate failures."""
        try:
            if inspect.iscoroutinefunction(handler):
                await handler(event)
            else:
                # Run sync function in a thread pool to prevent blocking the async loop
                await asyncio.to_thread(handler, event)
        except Exception as e:
            # Graceful error isolation
            self._logger.error(f"Subscriber {handler.__name__} failed on event {event.id}: {e}")
