"""
State Manager Subsystem.

The central, async-safe, transaction-safe data store for all operational
state within the Chhaya Kernel. Abstracts backend storage and provides
robust observability and snapshotting.
"""

import asyncio
import copy
import datetime
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from event_bus.bus import EventBus
from event_bus.models import Event

from .lifecycle import HealthReport


class StateManagerError(Exception):
    """Base exception for State Manager operations."""

    pass


class StateCategory(StrEnum):
    KERNEL = "kernel"
    AGENT = "agent"
    SESSION = "session"
    WORKFLOW = "workflow"
    PLUGIN = "plugin"
    PROVIDER = "provider"
    CAPABILITY = "capability"


@dataclass(frozen=True)
class StateChange:
    category: StateCategory
    key: str
    old_value: Any
    new_value: Any
    action: str  # "CREATE", "UPDATE", "DELETE"


@dataclass(frozen=True)
class StateSnapshot:
    """A versioned, point-in-time serialized snapshot of a state tree."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat())
    version: int = 1
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    data: dict[StateCategory, dict[str, Any]] = field(default_factory=dict)


class StateSerializer(Protocol):
    """Protocol for serializing state objects into JSON-safe dictionaries."""

    def serialize(self, obj: Any) -> dict[str, Any] | str | int | float | bool | None: ...
    def deserialize(self, data: Any) -> Any: ...


class DefaultStateSerializer:
    """A basic serializer for primitive types."""

    def serialize(self, obj: Any) -> Any:
        return copy.deepcopy(obj)  # Deep copy is sufficient for InMemory phase 1

    def deserialize(self, data: Any) -> Any:
        return copy.deepcopy(data)


class StateObserver(Protocol):
    """Synchronous hook interface for internal kernel reactivity."""

    def before_change(self, change: StateChange) -> None: ...
    def after_change(self, change: StateChange) -> None: ...
    def before_snapshot(self, description: str) -> None: ...
    def after_snapshot(self, snapshot: StateSnapshot) -> None: ...


class StateBackend(Protocol):
    """Abstract protocol for underlying storage implementations."""

    async def get(self, category: StateCategory, key: str) -> Any | None: ...
    async def put(self, category: StateCategory, key: str, value: Any) -> None: ...
    async def delete(self, category: StateCategory, key: str) -> None: ...
    async def list_keys(self, category: StateCategory) -> list[str]: ...
    async def clear_category(self, category: StateCategory) -> None: ...
    async def dump_all(self) -> dict[StateCategory, dict[str, Any]]: ...


class StateTransaction(Protocol):
    """Context manager for batched, atomic state mutations."""

    async def put(self, category: StateCategory, key: str, value: Any) -> None: ...
    async def delete(self, category: StateCategory, key: str) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def __aenter__(self) -> "StateTransaction": ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...


class StateStore(Protocol):
    """The public API for the StateManager."""

    async def get_state(self, category: StateCategory, key: str) -> Any | None: ...
    async def set_state(self, category: StateCategory, key: str, value: Any) -> None: ...
    async def delete_state(self, category: StateCategory, key: str) -> None: ...
    async def update_state(
        self, category: StateCategory, key: str, updater: Callable[[Any], Any]
    ) -> None: ...
    async def has_state(self, category: StateCategory, key: str) -> bool: ...
    async def list_keys(self, category: StateCategory) -> list[str]: ...

    def transaction(self) -> StateTransaction: ...

    def register_observer(self, category: StateCategory, observer: StateObserver) -> None: ...
    def unregister_observer(self, category: StateCategory, observer: StateObserver) -> None: ...

    async def create_snapshot(
        self, description: str = "", metadata: dict[str, Any] | None = None
    ) -> StateSnapshot: ...
    async def restore_snapshot(self, snapshot: StateSnapshot) -> None: ...


class InMemoryStateBackend(StateBackend):
    """A volatile, in-memory implementation of the StateBackend protocol."""

    def __init__(self) -> None:
        self._data: dict[StateCategory, dict[str, Any]] = {}
        for category in StateCategory:
            self._data[category] = {}

    async def get(self, category: StateCategory, key: str) -> Any | None:
        return self._data[category].get(key)

    async def put(self, category: StateCategory, key: str, value: Any) -> None:
        self._data[category][key] = value

    async def delete(self, category: StateCategory, key: str) -> None:
        self._data[category].pop(key, None)

    async def list_keys(self, category: StateCategory) -> list[str]:
        return list(self._data[category].keys())

    async def clear_category(self, category: StateCategory) -> None:
        self._data[category].clear()

    async def dump_all(self) -> dict[StateCategory, dict[str, Any]]:
        return copy.deepcopy(self._data)


class DefaultStateTransaction(StateTransaction):
    """
    Manages atomic updates to the state.
    Uses an overlay dict. On commit, writes everything sequentially.
    If an error occurs, it throws away the overlay.
    """

    def __init__(self, manager: "StateManager") -> None:
        self._manager = manager
        self._overlay: dict[StateCategory, dict[str, Any]] = {}
        self._deletions: dict[StateCategory, set[str]] = {}

        for category in StateCategory:
            self._overlay[category] = {}
            self._deletions[category] = set()

        self._changes: list[StateChange] = []

    async def put(self, category: StateCategory, key: str, value: Any) -> None:
        # Prefer the overlay value if mutated in this same transaction, otherwise backend
        if key in self._overlay[category]:
            old_val = self._overlay[category][key]
        else:
            old_val = await self._manager.get_state(category, key)

        self._overlay[category][key] = value
        self._deletions[category].discard(key)

        self._changes.append(
            StateChange(
                category=category,
                key=key,
                old_value=old_val,
                new_value=value,
                action="UPDATE" if old_val is not None else "CREATE",
            )
        )

    async def delete(self, category: StateCategory, key: str) -> None:
        # Prefer the overlay value if mutated in this same transaction, otherwise backend
        if key in self._overlay[category]:
            old_val = self._overlay[category][key]
        else:
            old_val = await self._manager.get_state(category, key)
        # Check overlay since get_state hits backend
        if key in self._overlay[category]:
            old_val = self._overlay[category][key]

        if old_val is None:
            return

        self._overlay[category].pop(key, None)
        self._deletions[category].add(key)

        self._changes.append(
            StateChange(
                category=category, key=key, old_value=old_val, new_value=None, action="DELETE"
            )
        )

    async def commit(self) -> None:
        if not self._changes:
            return

        # Fire before_change on observers
        for change in self._changes:
            for obs in self._manager._observers.get(change.category, []):
                obs.before_change(change)

        # Write to backend under lock
        async with self._manager._global_lock:
            for cat, kvs in self._overlay.items():
                for k, v in kvs.items():
                    await self._manager._backend.put(cat, k, v)
            for cat, keys in self._deletions.items():
                for k in keys:
                    await self._manager._backend.delete(cat, k)

        # Publish transaction committed
        await self._manager._bus.publish(
            Event(
                type="state.transaction.committed",
                payload={
                    "changes": [
                        {"category": c.category, "key": c.key, "action": c.action}
                        for c in self._changes
                    ]
                },
            )
        )

        # Fire after_change on observers
        for change in self._changes:
            for obs in self._manager._observers.get(change.category, []):
                obs.after_change(change)

        self._changes.clear()

    async def rollback(self) -> None:
        """Throws away the overlay."""
        self._changes.clear()
        for category in StateCategory:
            self._overlay[category].clear()
            self._deletions[category].clear()

        await self._manager._bus.publish(Event(type="state.transaction.rolled_back"))

    async def __aenter__(self) -> "DefaultStateTransaction":
        await self._manager._bus.publish(Event(type="state.changed.started"))
        await self._manager._bus.publish(Event(type="state.transaction.started"))
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()


class StateManager:
    """
    Subsystem 8: The Central State Manager.
    Implements KernelSubsystem and StateStore.
    """

    def __init__(
        self,
        event_bus: EventBus,
        backend: StateBackend | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._bus = event_bus
        self._backend = backend or InMemoryStateBackend()
        self._logger = logger or logging.getLogger("chhaya.state_manager")

        # A single global lock for Phase 1.
        # Future optimization: Map of category -> Lock to increase concurrency.
        self._global_lock = asyncio.Lock()

        self._observers: dict[StateCategory, list[StateObserver]] = {c: [] for c in StateCategory}

    @property
    def name(self) -> str:
        return "state_manager"

    @property
    def dependencies(self) -> list[str]:
        return ["event_bus"]

    async def initialize(self) -> None:
        self._logger.info(
            f"State Manager initializing with backend: {self._backend.__class__.__name__}"
        )

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health(self) -> HealthReport:
        return HealthReport(is_healthy=True)

    def ready(self) -> bool:
        return True

    # --- StateStore Protocol Implementation ---

    async def get_state(self, category: StateCategory, key: str) -> Any | None:
        # Get is lockless for in-memory, but conceptually should be safe.
        return await self._backend.get(category, key)

    async def set_state(self, category: StateCategory, key: str, value: Any) -> None:
        async with self.transaction() as tx:
            await tx.put(category, key, value)

    async def delete_state(self, category: StateCategory, key: str) -> None:
        async with self.transaction() as tx:
            await tx.delete(category, key)

        await self._bus.publish(
            Event(type="state.deleted.completed", payload={"category": category, "key": key})
        )

        await self._bus.publish(
            Event(type="state.deleted.completed", payload={"category": category, "key": key})
        )

    async def update_state(
        self, category: StateCategory, key: str, updater: Callable[[Any], Any]
    ) -> None:
        async with self._global_lock:
            old_val = await self._backend.get(category, key)
            new_val = updater(old_val)

            # For simplicity in Phase 1, we just do a direct put and notify
            # A more rigorous implementation would spin up a mini-transaction
            await self._backend.put(category, key, new_val)

        change = StateChange(
            category=category,
            key=key,
            old_value=old_val,
            new_value=new_val,
            action="UPDATE" if old_val is not None else "CREATE",
        )
        for obs in self._observers[category]:
            obs.before_change(change)
            obs.after_change(change)

        await self._bus.publish(
            Event(
                type="state.changed.completed",
                payload={"category": category, "key": key, "action": change.action},
            )
        )

    async def has_state(self, category: StateCategory, key: str) -> bool:
        return await self._backend.get(category, key) is not None

    async def list_keys(self, category: StateCategory) -> list[str]:
        return await self._backend.list_keys(category)

    def transaction(self) -> StateTransaction:
        return DefaultStateTransaction(self)

    def register_observer(self, category: StateCategory, observer: StateObserver) -> None:
        if observer not in self._observers[category]:
            self._observers[category].append(observer)

    def unregister_observer(self, category: StateCategory, observer: StateObserver) -> None:
        if observer in self._observers[category]:
            self._observers[category].remove(observer)

    async def create_snapshot(
        self, description: str = "", metadata: dict[str, Any] | None = None
    ) -> StateSnapshot:
        for obs_list in self._observers.values():
            for obs in obs_list:
                obs.before_snapshot(description)

        async with self._global_lock:
            raw_data = await self._backend.dump_all()

        snap = StateSnapshot(description=description, metadata=metadata or {}, data=raw_data)

        await self._bus.publish(
            Event(type="state.snapshot.created", payload={"snapshot_id": snap.id})
        )

        for obs_list in self._observers.values():
            for obs in obs_list:
                obs.after_snapshot(snap)

        return snap

    async def restore_snapshot(self, snapshot: StateSnapshot) -> None:
        async with self._global_lock:
            # Wipe everything
            for category in StateCategory:
                await self._backend.clear_category(category)

            # Restore
            for cat, data in snapshot.data.items():
                for k, v in data.items():
                    await self._backend.put(cat, k, v)

        await self._bus.publish(
            Event(type="state.snapshot.restored", payload={"snapshot_id": snapshot.id})
        )
