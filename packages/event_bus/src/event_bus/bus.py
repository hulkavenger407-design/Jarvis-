"""
Event Bus Subsystem.

Provides an asynchronous Publish/Subscribe messaging architecture for the
Chhaya Kernel, supporting wildcard topics, priorities, and graceful isolation.
"""
import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeAlias

from .matcher import RegexTopicMatcher, TopicMatcher
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

    def __init__(
        self,
        logger: logging.Logger | None = None,
        matcher: TopicMatcher | None = None
    ) -> None:
        # Dictionary mapping exact topic strings to lists of (priority, handler)
        self._subscribers: dict[str, list[tuple[int, EventHandler]]] = {}

        # List of (compiled_pattern, priority, handler) for wildcard topics (e.g. "agent.*")
        self._wildcard_subscribers: list[tuple[Any, int, EventHandler]] = []

        # Ordered list of middleware
        self._middlewares: list[Middleware] = []

        self._logger = logger or logging.getLogger("chhaya.event_bus")
        self._matcher = matcher or RegexTopicMatcher()

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
        if self._matcher.is_wildcard(topic):
            compiled = self._matcher.compile(topic)
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
        Subscribers are executed sequentially to respect priority and cancellation.


        Args:
            event: The Event object to publish.
        """
        # 1. Fire 'before_publish' hook
        self.before_publish(event)

        # 2. Build the middleware chain
        async def execute_subscribers(e: Event) -> None:
            if e.is_cancelled:
                return
            await self._dispatch_to_subscribers(e)

        chain: Callable[[Event], Awaitable[None]] = execute_subscribers
        for middleware in reversed(self._middlewares):
            chain = self._wrap_middleware(middleware, chain)

        # 3. Execute the pipeline
        try:
            await chain(event)
        except Exception as e:
            self._logger.error(f"EventBus critical failure processing event {event.id}: {e}")

        # 4. Fire 'after_publish' hook
        self.after_publish(event)

    # --- Lifecycle Hooks ---
    def before_publish(self, event: Event) -> None:
        """Extension hook fired before an event enters the middleware pipeline."""
        pass

    def after_publish(self, event: Event) -> None:
        """Extension hook fired after an event has finished processing in the pipeline."""
        pass

    def before_handler(self, event: Event, handler: EventHandler) -> None:
        """Extension hook fired immediately before a specific handler executes."""
        pass

    def after_handler(self, event: Event, handler: EventHandler) -> None:
        """Extension hook fired immediately after a specific handler executes."""
        pass
    # -----------------------

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
            if self._matcher.match(pattern, event.type):
                handlers.append((priority, handler))

        # Re-sort combined list by priority
        handlers.sort(key=lambda x: x[0])

        # Execute handlers sequentially by priority, but wrap them in tasks to isolate errors
        for _, handler in handlers:
            if event.is_cancelled:
                self._logger.debug(f"Event {event.id} cancelled. Stopping propagation.")
                break

            self.before_handler(event, handler)
            await self._execute_handler_safely(handler, event)
            self.after_handler(event, handler)

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

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """
        Unsubscribes a handler from a specific topic or wildcard.

        Args:
            topic: The event type to stop listening for.
            handler: The callable that was originally subscribed.
        """
        if self._matcher.is_wildcard(topic):
            # For wildcards, we must iterate and remove matching handlers.
            # We must compile the topic to find the exact pattern match string, or
            # just rebuild the list filtering out the exact handler instance.
            # We filter by checking if the handler matches and the pattern string matches.
            # Compare pattern strings to identify the correct registration.
            compiled_target = self._matcher.compile(topic)
            self._wildcard_subscribers = [
                (pattern, priority, h)
                for pattern, priority, h in self._wildcard_subscribers
                if not (
                    h == handler
                    and getattr(pattern, "pattern", None) == getattr(
                        compiled_target, "pattern", None
                    )
                )
            ]
        else:
            if topic in self._subscribers:
                self._subscribers[topic] = [
                    (priority, h)
                    for priority, h in self._subscribers[topic]
                    if h != handler
                ]
                # Clean up empty topics to save memory
                if not self._subscribers[topic]:
                    del self._subscribers[topic]
