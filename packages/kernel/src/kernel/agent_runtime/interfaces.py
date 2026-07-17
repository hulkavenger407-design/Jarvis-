from typing import Any, Protocol

from .models import AgentContext, AgentHandle, AgentResult


class Agent(Protocol):
    """The core interface an agent implementation must fulfill."""

    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...

    async def initialize(self, context: AgentContext) -> None:
        """Sets up the agent resources."""
        ...

    async def step(self, context: AgentContext) -> AgentResult:
        """Executes a single step of the agent's logic."""
        ...

    async def cleanup(self) -> None:
        """Cleans up agent resources."""
        ...


class AgentFactory(Protocol):
    """Factory interface for instantiating agents dynamically."""

    async def create(self, name: str, config: dict[str, Any]) -> Agent: ...


class AgentRepository(Protocol):
    """Storage interface for persisting agent handles and state across reboots."""

    async def save(self, handle: AgentHandle) -> None: ...
    async def load(self, agent_id: str) -> AgentHandle | None: ...
    async def list_all(self) -> list[AgentHandle]: ...
    async def delete(self, agent_id: str) -> None: ...


class AgentExecutor(Protocol):
    """Abstraction for how an agent's step is executed."""

    async def execute(self, agent: Agent, context: AgentContext) -> AgentResult: ...
