"""
Core Data Models for the Event Bus.
"""
import datetime
import re
import uuid
from dataclasses import dataclass, field
from typing import Any


class EventValidationError(ValueError):
    """Raised when an Event fails validation against the Kernel Events Specification."""
    pass


# Strict DOMAIN.ACTION.STATUS convention (e.g. 'agent.task.completed')
EVENT_TYPE_REGEX = re.compile(r"^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$")


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

    def __post_init__(self) -> None:
        if not EVENT_TYPE_REGEX.match(self.type):
            raise EventValidationError(
                f"Invalid event type '{self.type}'. Must follow DOMAIN.ACTION.STATUS format."
            )

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
