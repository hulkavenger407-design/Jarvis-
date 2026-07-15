"""
Transaction implementation for the State Manager subsystem.
"""

from typing import Any

from event_bus.models import Event

from .interfaces import StateTransaction
from .models import StateCategory, StateChange


class DefaultStateTransaction(StateTransaction):
    """
    Manages atomic updates to the state.
    Uses an overlay dict. On commit, writes everything sequentially.
    If an error occurs, it throws away the overlay.
    """

    def __init__(self, manager: Any) -> None:
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
                version="1.0",


                source="state_manager",
                session_id=None,
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

        await self._manager._bus.publish(
            Event(
                type="state.transaction.rolled_back",
                version="1.0",
                payload={},


                source="state_manager",
                session_id=None,
            )
        )

    async def __aenter__(self) -> "DefaultStateTransaction":
        await self._manager._bus.publish(
            Event(
                type="state.changed.started",
                version="1.0",
                payload={},


                source="state_manager",
                session_id=None,
            )
        )
        await self._manager._bus.publish(
            Event(
                type="state.transaction.started",
                version="1.0",
                payload={},


                source="state_manager",
                session_id=None,
            )
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
