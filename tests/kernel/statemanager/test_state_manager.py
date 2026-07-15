import asyncio
from typing import Any

import pytest
from event_bus.bus import EventBus
from event_bus.models import Event
from kernel.statemanager import StateCategory, StateChange, StateManager, StateSnapshot


@pytest.fixture
def store() -> StateManager:
    bus = EventBus()
    return StateManager(bus)


@pytest.mark.asyncio
async def test_crud_operations(store: StateManager) -> None:
    # Set
    await store.set_state(StateCategory.AGENT, "test_key", "value1")
    assert await store.has_state(StateCategory.AGENT, "test_key")

    # Get
    assert await store.get_state(StateCategory.AGENT, "test_key") == "value1"

    # List
    keys = await store.list_keys(StateCategory.AGENT)
    assert "test_key" in keys

    # Update
    await store.update_state(StateCategory.AGENT, "test_key", lambda v: f"{v}_updated")
    assert await store.get_state(StateCategory.AGENT, "test_key") == "value1_updated"

    # Delete
    await store.delete_state(StateCategory.AGENT, "test_key")
    assert not await store.has_state(StateCategory.AGENT, "test_key")
    assert await store.get_state(StateCategory.AGENT, "test_key") is None


@pytest.mark.asyncio
async def test_transaction_commit(store: StateManager) -> None:
    async with store.transaction() as tx:
        await tx.put(StateCategory.KERNEL, "key1", "val1")
        await tx.put(StateCategory.KERNEL, "key2", "val2")
        await tx.delete(StateCategory.KERNEL, "key2")

    assert await store.get_state(StateCategory.KERNEL, "key1") == "val1"
    assert await store.get_state(StateCategory.KERNEL, "key2") is None


@pytest.mark.asyncio
async def test_transaction_rollback(store: StateManager) -> None:
    await store.set_state(StateCategory.SESSION, "safe_key", "safe_val")

    with pytest.raises(ValueError, match="Abort"):
        async with store.transaction() as tx:
            await tx.put(StateCategory.SESSION, "safe_key", "corrupted_val")
            await tx.put(StateCategory.SESSION, "new_key", "bad_val")
            raise ValueError("Abort")

    # State should remain untouched
    assert await store.get_state(StateCategory.SESSION, "safe_key") == "safe_val"
    assert await store.get_state(StateCategory.SESSION, "new_key") is None


@pytest.mark.asyncio
async def test_snapshot_and_restore(store: StateManager) -> None:
    await store.set_state(StateCategory.PLUGIN, "p1", "active")
    await store.set_state(StateCategory.PLUGIN, "p2", "stopped")

    snap = await store.create_snapshot(description="test_snap", metadata={"version": "1.0"})

    assert snap.version == 1
    assert snap.description == "test_snap"
    assert snap.data[StateCategory.PLUGIN]["p1"] == "active"

    # Mutate state after snapshot
    await store.set_state(StateCategory.PLUGIN, "p1", "failed")
    await store.delete_state(StateCategory.PLUGIN, "p2")

    # Restore
    await store.restore_snapshot(snap)

    assert await store.get_state(StateCategory.PLUGIN, "p1") == "active"
    assert await store.get_state(StateCategory.PLUGIN, "p2") == "stopped"


@pytest.mark.asyncio
async def test_concurrency(store: StateManager) -> None:
    async def worker(idx: int) -> None:
        async with store.transaction() as tx:
            await tx.put(StateCategory.WORKFLOW, f"k_{idx}", idx)

    # Launch 100 concurrent transactions
    await asyncio.gather(*(worker(i) for i in range(100)))

    keys = await store.list_keys(StateCategory.WORKFLOW)
    assert len(keys) == 100


@pytest.mark.asyncio
async def test_observers_and_events() -> None:
    bus = EventBus()
    store = StateManager(bus)

    bus_events = []

    async def capture_event(e: Event) -> None:
        bus_events.append(e.type)

    bus.subscribe("state.*", capture_event)

    class TestObserver:
        def __init__(self) -> None:
            self.before_calls: list[Any] = []
            self.after_calls: list[Any] = []

        def before_change(self, change: StateChange) -> None:
            self.before_calls.append(change)

        def after_change(self, change: StateChange) -> None:
            self.after_calls.append(change)

        def before_snapshot(self, description: str) -> None:
            self.before_calls.append(description)

        def after_snapshot(self, snapshot: StateSnapshot) -> None:
            self.after_calls.append(snapshot)

    obs = TestObserver()
    store.register_observer(StateCategory.CAPABILITY, obs)

    async with store.transaction() as tx:
        await tx.put(StateCategory.CAPABILITY, "cap1", "val1")

    assert len(obs.before_calls) == 1
    assert len(obs.after_calls) == 1
    assert obs.after_calls[0].action == "CREATE"
    assert obs.after_calls[0].key == "cap1"

    assert "state.transaction.started" in bus_events
    assert "state.transaction.committed" in bus_events

    await store.create_snapshot(description="test_snap")
    assert "state.snapshot.created" in bus_events
    assert "test_snap" in obs.before_calls
    assert len(obs.after_calls) == 2  # 1 change, 1 snapshot


@pytest.mark.asyncio
async def test_lifecycle_and_health(store: StateManager) -> None:
    assert store.name == "state_manager"
    assert "event_bus" in store.dependencies
    assert store.ready() is True

    health = await store.health()
    assert health.is_healthy is True

    await store.initialize()  # Should not raise
    await store.start()
    await store.stop()
    await store.shutdown()


@pytest.mark.asyncio
async def test_state_serializer() -> None:
    from kernel.statemanager import DefaultStateSerializer

    serializer = DefaultStateSerializer()

    obj = {"a": 1, "b": [1, 2, 3]}
    serialized = serializer.serialize(obj)
    assert serialized == obj
    assert serialized is not obj  # deep copy

    deserialized = serializer.deserialize(serialized)
    assert deserialized == obj
    assert deserialized is not serialized
