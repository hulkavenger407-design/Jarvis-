"""
Data models and Enums for the State Manager subsystem.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .snapshot import StateSnapshot


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


class StateSerializer(Protocol):
    """Protocol for serializing state objects into JSON-safe dictionaries."""

    def serialize(self, obj: Any) -> dict[str, Any] | str | int | float | bool | None: ...
    def deserialize(self, data: Any) -> Any: ...


class StateObserver(Protocol):
    """Synchronous hook interface for internal kernel reactivity."""

    def before_change(self, change: StateChange) -> None: ...
    def after_change(self, change: StateChange) -> None: ...
    def before_snapshot(self, description: str) -> None: ...
    def after_snapshot(self, snapshot: 'StateSnapshot') -> None: ...
