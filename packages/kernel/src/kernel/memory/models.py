from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class MemoryTier(Enum):
    """Architectural tiers of memory."""

    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


@dataclass
class MemoryRecord:
    """Core kernel model for a memory item."""

    tier: MemoryTier
    namespace: str
    key: str
    value: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemorySearchResult:
    """Core kernel model for a memory search result."""

    record: MemoryRecord
    score: float
