# ADR 0008: Provider Registry and Interfaces

## Status
Accepted

## Context
The core OS logic must remain agnostic to the ever-changing landscape of AI models and databases.

## Decision
We will enforce a strict `ProviderRegistry`.
- Core logic depends only on Python `Protocol` interfaces (e.g., `LLMProvider`, `MemoryProvider`).
- Concrete implementations are registered dynamically.

## Alternatives Considered
- **LangChain/LlamaIndex Abstractions:** Using third-party abstraction layers directly in the core.

## Trade-offs
- **Pros:** We control the interface. If LangChain releases a breaking version change, only our specific `LangChainLLMProvider` adapter needs to be updated, not the Kernel.
- **Cons:** We have to maintain our own interface definitions and write adapter wrappers for every service we want to use.

## Long-term Implications
This is the cornerstone of the Plugin system. Third-party developers can build new providers (e.g., a new local vector DB) and inject them into the OS without modifying the core repository.