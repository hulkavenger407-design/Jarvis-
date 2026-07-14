from typing import Any
from kernel.interfaces import IEventBus, IStateManager, IMemoryEngine
from interfaces.providers import IModelAdapter, IVectorStore, ICapability

def test_ieventbus_protocol() -> None:
    class MockEventBus:
        async def publish(self, event: Any) -> None: pass
        def subscribe(self, topic: str, handler: Any, priority: int = 100) -> None: pass
        def unsubscribe(self, topic: str, handler: Any) -> None: pass

    bus: IEventBus = MockEventBus()
    assert bus is not None

def test_istatemanager_protocol() -> None:
    class MockStateManager:
        async def get_state(self, category: Any, key: str) -> Any | None: return None
        async def set_state(self, category: Any, key: str, value: Any) -> None: pass
        async def delete_state(self, category: Any, key: str) -> None: pass

    manager: IStateManager = MockStateManager()
    assert manager is not None

def test_imodeladapter_protocol() -> None:
    class MockModelAdapter:
        async def run_async(self, prompt: str, **kwargs: Any) -> str: return "response"

    adapter: IModelAdapter = MockModelAdapter()
    assert adapter is not None
