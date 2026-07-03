"""
Core Interfaces

Provider abstraction contracts for the Chhaya Operating System.
All external services must implement these interfaces.
"""
from typing import Any, Protocol


class LLMProvider(Protocol):
    """Interface for LLM integrations (Ollama, OpenAI, etc.)."""
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        ...

class MemoryProvider(Protocol):
    """Interface for long and short-term memory storage."""
    async def save(self, key: str, value: Any) -> None:
        ...
    async def load(self, key: str) -> Any:
        ...

class ToolProvider(Protocol):
    """Interface for functional tools (file system, web search, etc.)."""
    async def execute(self, tool_name: str, **kwargs: Any) -> Any:
        ...
