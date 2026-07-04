"""
Core Data Models for the Event Bus.
"""
import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    """
    The base structure for an event passing through the Chhaya Kernel.
    Adheres strictly to the Kernel Events Specification.
    """
    # Event routing
    type: str  # Format: DOMAIN.ACTION.STATUS
    version: str = "1.0"

    # Payload
    payload: dict[str, Any] = field(default_factory=dict)

    # Metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat()
    )
    source: str = "unknown"
    session_id: str | None = None

    # Control flow flags (not part of the spec payload directly, but used internally)
    _is_cancelled: bool = field(default=False, repr=False, init=False)

    def cancel(self) -> None:
        """
        Cancels further processing of this event by remaining handlers in the pipeline.
        This is primarily used by the Permission Manager or Middleware to block requested actions.
        """
        self._is_cancelled = True

    @property
    def is_cancelled(self) -> bool:
        """Returns True if the event has been cancelled."""
        return self._is_cancelled
