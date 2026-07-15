"""
Snapshot functionality and models for the State Manager subsystem.
"""

import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any

from .models import StateCategory


@dataclass(frozen=True)
class StateSnapshot:
    """A versioned, point-in-time serialized snapshot of a state tree."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat())
    version: int = 1
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    data: dict[StateCategory, dict[str, Any]] = field(default_factory=dict)
