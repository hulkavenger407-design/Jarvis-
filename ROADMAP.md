# Roadmap

## Phase 0: Foundation (Current)
*   Initialize polyglot monorepo (Python/TypeScript).
*   Set up dependency management (pnpm, uv) and build tools (Turborepo).
*   Establish code quality standards (Ruff, MyPy, ESLint, Prettier).
*   Create core architectural stubs (`kernel`, `interfaces`, `event_bus`, `plugin_sdk`, `config`, `telemetry`, `security`).
*   Configure CI/CD pipelines via GitHub Actions.
*   Establish foundational documentation (ADRs, Architecture, etc.).

## Phase 1: Core AI Runtime & Local Inference
*   Implement `kernel` execution loop and event routing.
*   Implement `interfaces` for basic LLM providers.
*   Integrate Ollama as the default local LLM provider.
*   Implement basic agent execution capabilities.
*   Create a simple CLI or REST API to interact with the runtime.

## Phase 2: Memory & Knowledge (RAG)
*   Define RAG and Memory interfaces.
*   Implement vector database integration (local first, e.g., Chroma or Qdrant).
*   Implement short-term and long-term memory for agents.

## Phase 3: Tooling & Workflows
*   Implement MCP (Model Context Protocol) support.
*   Build integration tools for file system, web search, and basic APIs.
*   Implement workflow orchestration (e.g., integrating LangGraph as an adapter).

## Phase 4: User Interface & Dashboard
*   Develop the Next.js web dashboard.
*   Implement WebSockets/SSE for live agent streaming.
*   Provide visual management for agents, memory, and settings.

## Phase 5: Advanced Automation & Ecosystem
*   Implement background autonomous execution.
*   Browser automation and computer control capabilities.
*   Solidify Plugin Ecosystem and marketplace.