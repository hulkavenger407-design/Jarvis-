"""
State Manager package.
"""

from .interfaces import (
    StateBackend,
    StateStore,
    StateTransaction,
)
from .models import (
    StateCategory,
    StateChange,
    StateObserver,
    StateSerializer,
)
from .snapshot import StateSnapshot
from .store import (
    DefaultStateSerializer,
    InMemoryStateBackend,
    StateManager,
    StateManagerError,
)
from .transaction import DefaultStateTransaction

__all__ = [
    "StateCategory",
    "StateChange",
    "StateSnapshot",
    "StateSerializer",
    "StateObserver",
    "StateBackend",
    "StateTransaction",
    "StateStore",
    "StateManager",
    "InMemoryStateBackend",
    "DefaultStateSerializer",
    "DefaultStateTransaction",
    "StateManagerError",
]
