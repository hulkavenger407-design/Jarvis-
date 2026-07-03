# Chhaya Agent Factory Architecture

## Vision

Chhaya Agent Factory is a modular, open-source AI Operating System designed to create, manage, orchestrate, and evolve specialized AI agents. It prioritizes local execution, maintainability, and extensibility.

## Core Principles

1.  **Local-First Philosophy:** The system must function fully on local hardware (e.g., Ryzen 7, 32GB RAM, 4GB VRAM). Cloud dependencies are strictly optional.
2.  **Modular Monorepo:** Structured using Turborepo to seamlessly manage polyglot environments (Python and TypeScript).
3.  **Kernel-Centric Design:** A central 'Chhaya Kernel' acts as the heart of the system. All communications between agents, plugins, and providers route through this kernel.
4.  **Event-Driven Architecture:** Components communicate via an Event Bus to ensure decoupled, asynchronous processing where necessary.
5.  **Provider Abstractions:** All external services (LLMs, Memory, Tools) operate behind strict interfaces, allowing implementations to be swapped without affecting business logic.
6.  **Framework Independence:** The core runtime does not depend heavily on tools like LangChain or LangGraph; rather, these tools act as adapters or plugins.

## Monorepo Structure

*   `apps/`: User-facing applications (e.g., web dashboards).
*   `packages/`: Core libraries and shared modules.
    *   `kernel/`: The central orchestrator for the system.
    *   `interfaces/`: Provider abstraction contracts.
    *   `event_bus/`: Central event-driven communication hub.
    *   `plugin_sdk/`: Base classes and tools for building plugins.
    *   `config/`: Environment validation and configuration management.
    *   `telemetry/`: Structured logging and observability.
    *   `security/`: Auth, permissions, and secrets management.
*   `services/`: Standalone backend services (e.g., FastAPI application).
*   `plugins/`: Extensible capabilities adhering to the plugin SDK.
*   `sdk/`: Client libraries for external interaction.
*   `infrastructure/`: Deployment and provisioning scripts.
*   `docs/`: Living documentation and Architecture Decision Records (ADRs).
*   `scripts/`: Monorepo maintenance and build scripts.
*   `tests/`: End-to-end and integration test suites.

## Technology Stack

*   **Backend / AI Core:** Python >= 3.11, FastAPI, Pydantic.
*   **Frontend / Dashboard:** TypeScript, Next.js / React (future phases).
*   **Monorepo Tools:** Turborepo, pnpm (for JS/TS), uv (for Python).
*   **Testing:** `pytest` (Python), `vitest` (TypeScript).