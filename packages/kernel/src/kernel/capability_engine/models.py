import asyncio
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from kernel.agent_runtime import AgentContext


class CapabilityPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class CapabilityResultStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"

class CapabilityExecutionState(Enum):
    PENDING = "pending"
    AUTHORIZING = "authorizing"
    RESOLVING = "resolving"
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

@dataclass
class CapabilityHealth:
    is_healthy: bool
    details: dict[str, str] = field(default_factory=dict)

@dataclass
class CapabilityMetrics:
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    timeout_count: int = 0
    total_latency_ms: float = 0.0
    average_latency_ms: float = 0.0
    maximum_latency_ms: float = 0.0
    provider_usage: dict[str, int] = field(default_factory=dict)
    capability_usage: dict[str, int] = field(default_factory=dict)

@dataclass
class CapabilityRequest:
    capability_name: str
    agent_id: str
    arguments: dict[str, Any]
    priority: CapabilityPriority = CapabilityPriority.NORMAL
    timeout_seconds: float = 60.0
    max_retries: int = 0

@dataclass
class CapabilityResult:
    status: CapabilityResultStatus
    data: Any = None
    error: Exception | None = None
    latency_ms: float = 0.0

@dataclass
class CapabilityContext:
    request_id: str
    request: CapabilityRequest
    agent_context: AgentContext | None = None
    resolved_provider: str | None = None
    started_at: datetime.datetime | None = None
    is_cancelled: asyncio.Event = field(default_factory=asyncio.Event)
    task_result: CapabilityResult | None = None

@dataclass
class CapabilityExecution:
    execution_id: str
    state: CapabilityExecutionState
    context: CapabilityContext
    result: CapabilityResult | None = None
    task_id: str | None = None
    attempt_count: int = 0
    executor: "Any | None" = None

@dataclass
class CapabilityHandle:
    execution_id: str
    status_task: asyncio.Task[Any] | None = None
