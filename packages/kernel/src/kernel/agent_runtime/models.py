import asyncio
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from event_bus.bus import EventBus

from kernel.capability_registry import CapabilityRegistry
from kernel.di import DIContainer
from kernel.provider_registry import ProviderRegistry
from kernel.statemanager import StateManager


class AgentState(Enum):
    CREATED = "created"
    INITIALIZED = "initialized"
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    AWAITING_INPUT = "awaiting_input"
    SLEEPING = "sleeping"
    SUSPENDED = "suspended"
    FAULTED = "faulted"
    TERMINATED = "terminated"


class AgentPriority(Enum):
    BACKGROUND = 0
    NORMAL = 1
    HIGH = 2
    REALTIME = 3


@dataclass
class AgentHealth:
    is_healthy: bool
    state: AgentState
    last_error: Exception | None = None
    last_ping: datetime.datetime | None = None


@dataclass
class AgentMetrics:
    total_executions: int = 0
    total_failures: int = 0
    total_time_ms: float = 0.0
    capabilities_used: dict[str, int] = field(default_factory=dict)
    tokens_consumed: int = 0


@dataclass
class AgentContext:
    agent_id: str
    metadata: dict[str, Any]
    capabilities: list[str]  # List of allowed capability names
    di: DIContainer
    state_manager: StateManager
    event_bus: EventBus
    provider_registry: ProviderRegistry
    capability_registry: CapabilityRegistry

    # Execution bounds
    memory_limit_mb: int = 512
    max_history_turns: int = 100
    timeout_seconds: float = 300.0

    is_cancelled: asyncio.Event = field(default_factory=asyncio.Event)


@dataclass
class AgentResult:
    success: bool
    data: Any = None
    error: Exception | None = None


@dataclass
class AgentExecution:
    execution_id: str
    agent_id: str
    started_at: datetime.datetime
    finished_at: datetime.datetime | None = None
    result: AgentResult | None = None
    task_id: str | None = None


@dataclass
class AgentHandle:
    id: str
    name: str
    state: AgentState
    priority: AgentPriority
    health: AgentHealth
    metrics: AgentMetrics
    context: AgentContext
