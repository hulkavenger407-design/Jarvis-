# Provider Interface Specification

This document details the abstract interfaces that all external services must implement to be registered in the Chhaya Kernel's `ProviderRegistry`.

By strictly adhering to these protocols, the Kernel remains completely agnostic to the underlying technologies (e.g., Ollama vs. OpenAI).

## 1. LLM Provider (`LLMProvider`)
Provides text generation and chat completion capabilities.
```python
from typing import AsyncGenerator, List, Dict, Any, Protocol

class LLMProvider(Protocol):
    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Standard synchronous generation."""
        ...

    async def stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[str, None]:
        """Asynchronous streaming generation (for SSE/WebSockets)."""
        ...

    def get_context_window(self) -> int:
        """Returns the maximum token limit for this model."""
        ...
```

## 2. Embedding Provider (`EmbeddingProvider`)
Converts text to vector representations for RAG.
```python
class EmbeddingProvider(Protocol):
    async def embed_text(self, text: str) -> List[float]:
        ...

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        ...
```

## 3. Memory Provider (`MemoryProvider`)
Handles short-term and long-term state.
```python
class MemoryProvider(Protocol):
    async def save_short_term(self, session_id: str, key: str, value: Any) -> None:
        """Saves ephemeral state (e.g., KV store like SQLite/Redis)."""
        ...

    async def save_long_term(self, text: str, metadata: dict) -> str:
        """Saves semantic knowledge (e.g., to Vector DB). Returns UUID."""
        ...

    async def semantic_search(self, query: str, top_k: int = 5) -> List[dict]:
        """Queries the vector DB."""
        ...
```

## 4. Speech Provider (`SpeechProvider`)
Handles Text-to-Speech (TTS) and Speech-to-Text (STT).
```python
class SpeechProvider(Protocol):
    async def generate_audio(self, text: str) -> bytes:
        """TTS: Returns raw audio bytes."""
        ...

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """STT: Returns transcribed text."""
        ...
```

## 5. Tool Provider (`ToolProvider`)
A generic interface for executable actions (MCP, APIs, etc).
```python
class ToolProvider(Protocol):
    @property
    def name(self) -> str:
        ...

    def get_json_schema(self) -> dict:
        """Returns the JSON schema expected by the LLM function calling spec."""
        ...

    async def execute(self, **kwargs: Any) -> Any:
        """Executes the tool logic."""
        ...
```

## 6. Browser & Vision Providers (Future Specs)
*To be implemented in later phases, but reserved here for architecture planning.*

### Browser Provider (`BrowserProvider`)
Controls Playwright or Selenium instances.
```python
class BrowserProvider(Protocol):
    async def navigate(self, url: str) -> None: ...
    async def click(self, selector: str) -> None: ...
    async def extract_html(self) -> str: ...
```

### Vision Provider (`VisionProvider`)
Processes images.
```python
class VisionProvider(Protocol):
    async def describe_image(self, image_bytes: bytes, prompt: str) -> str: ...
```