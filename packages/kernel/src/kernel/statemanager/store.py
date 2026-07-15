"""
Store implementation for the State Manager subsystem.
"""

import asyncio
import copy
import logging
from collections.abc import Callable
from typing import Any

from event_bus.models import Event

from kernel.interfaces import IEventBus
from kernel.lifecycle import HealthReport

from .interfaces import StateBackend, StateStore, StateTransaction
from .models import StateCategory, StateChange, StateObserver
from .snapshot import StateSnapshot
from .transaction import DefaultStateTransaction


class StateManagerError(Exception):
    """Base exception for State Manager operations."""

    pass


class DefaultStateSerializer:
    """A basic serializer for primitive types."""

    def serialize(self, obj: Any) -> Any:
        return copy.deepcopy(obj)  # Deep copy is sufficient for InMemory phase 1

    def deserialize(self, data: Any) -> Any:
        return copy.deepcopy(data)


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


class StateManager(StateStore):
    """
    Subsystem 8: The Central State Manager.
    Implements KernelSubsystem and StateStore.
    """

    def __init__(
        self,
        event_bus: IEventBus,
        backend: StateBackend | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._bus = event_bus
        self._backend = backend or InMemoryStateBackend()
        self._logger = logger or logging.getLogger("chhaya.state_manager")

        # A single global lock for Phase 1.
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
            Event(
                type="state.deleted.completed",
                payload={"category": category, "key": key},
                version="1.0",


                source="state_manager",
                session_id=None,
            )
        )

    async def update_state(
        self, category: StateCategory, key: str, updater: Callable[[Any], Any]
    ) -> None:
        async with self._global_lock:
            old_val = await self._backend.get(category, key)
            new_val = updater(old_val)
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
                version="1.0",


                source="state_manager",
                session_id=None,
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
            Event(
                type="state.snapshot.created",
                payload={"snapshot_id": snap.id},
                version="1.0",


                source="state_manager",
                session_id=None,
            )
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
            Event(
                type="state.snapshot.restored",
                payload={"snapshot_id": snapshot.id},
                version="1.0",


                source="state_manager",
                session_id=None,
            )
        )
