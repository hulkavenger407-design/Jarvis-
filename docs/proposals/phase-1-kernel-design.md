# Phase 1: Chhaya Kernel Design Proposal

## 1. Executive Summary
This document outlines the revised architecture for the Chhaya Kernel. Moving away from a simple message-router paradigm, the Chhaya Kernel is designed as a true Operating System for AI agents. It utilizes a strict Event-Driven Architecture to manage hardware resources, isolate processes (agents), handle security, and abstract hardware/services via a centralized registry.

## 2. Event-Driven Architecture
The central nervous system of the Chhaya Kernel is the **Event Bus**.
*   **Design**: Subsystems never invoke each other directly (e.g., the `Agent Manager` does not call `tool.execute()`). Instead, the `Agent Manager` publishes a `ToolExecutionRequestedEvent`. The relevant provider listens, executes the tool, and publishes a `ToolExecutionCompletedEvent`.
*   **Advantage**: Extreme decoupling. This allows the `Resource Manager` to intercept events and pause the Event Bus if VRAM is exhausted, or the `Permission Manager` to cancel a `ToolExecutionRequestedEvent` before it reaches the provider.

## 3. Kernel Subsystems (OS Managers)

To achieve the OS metaphor, the Kernel is divided into 12 core managers:

### 3.1 Boot Manager
*   **Responsibility**: The entry point. It loads environment variables, initializes the `Telemetry` system first to catch boot errors, and instantiates the `DI Container`.

### 3.2 Lifecycle Manager
*   **Responsibility**: Manages the overarching state machine of the Kernel (e.g., `INITIALIZING`, `RUNNING`, `PAUSED`, `SHUTTING_DOWN`). It orchestrates the order in which other managers come online.

### 3.3 Dependency Injection Container
*   **Responsibility**: Constructs complex objects and their dependencies. It ensures that any manager that needs the `Event Bus` or `Telemetry` receives the correct singleton instance automatically.

### 3.4 Resource Manager (CPU/RAM/GPU)
*   **Responsibility**: A background daemon that polls system resources (specifically targeting the strict 4GB VRAM constraint).
*   **Action**: If VRAM hits 90%, it publishes a `ResourceCriticalEvent`. The `Agent Manager` responds by suspending idle agents and flushing their context to disk.

### 3.5 Agent Manager
*   **Responsibility**: Analogous to an OS Process Manager. It spawns, tracks, suspends, and resumes Agent instances. It handles the "context switching" required when multiple agents must share the limited LLM VRAM.

### 3.6 Plugin Manager
*   **Responsibility**: Discovers and loads external code at runtime. It verifies plugin signatures/manifests against the `Plugin SDK` and mounts their provided hooks into the `Event Bus`.

### 3.7 Provider Registry
*   **Responsibility**: The hardware/service abstraction layer. It maps abstract interfaces (e.g., `LLMProvider`, `MemoryProvider`, `VoiceProvider`) to their injected concrete implementations (e.g., `OllamaProvider`, `SQLiteMemoryProvider`). Agents only ever ask the Registry for an interface, never a specific brand.

### 3.8 Task Scheduler
*   **Responsibility**: Analogous to `cron`. It manages delayed events, background polling (e.g., "check this inbox every 5 minutes"), and resuming suspended agents when their wait conditions are met.

### 3.9 Session Manager
*   **Responsibility**: Tracks client-facing context. It maps an incoming API request (or WebSocket connection) to the correct running Agent and its specific Short-Term Memory context.

### 3.10 Permission Manager
*   **Responsibility**: The security kernel. It listens to the `Event Bus` and intercepts sensitive events (like file system access or executing code). It verifies the request against the current Session's capabilities.

### 3.11 Telemetry & Logging
*   **Responsibility**: Structured observability. It captures all events flowing through the `Event Bus` to provide debugging traces, performance metrics (latency to LLM), and system health reports.

### 3.12 Shutdown Manager
*   **Responsibility**: Handles `SIGINT` / `SIGTERM` gracefully. It instructs the `Agent Manager` to serialize active states, closes database connections in the `Provider Registry`, and unloads models from the `Resource Manager` to prevent corrupted states.

---

## 4. Alternative Designs & Trade-offs

### 4.1 Event Bus Implementation
*   **Alternative**: Use RabbitMQ or Kafka.
*   **Trade-off**: Highly scalable for distributed systems but violates the "Local-First" and zero-configuration constraint.
*   **Recommendation**: Implement a fast, in-memory asynchronous `asyncio` Event Bus for Phase 1. Design the interface so it can be swapped for Redis in a future distributed phase.

### 4.2 Agent Concurrency vs. Swapping
*   **Alternative**: Load multiple LLMs into VRAM simultaneously for true parallel agent execution.
*   **Trade-off**: The target hardware (4GB VRAM) absolutely cannot support multiple modern LLMs simultaneously.
*   **Recommendation**: The `Agent Manager` must implement a "Context Switching" pattern. Only one LLM is active in VRAM. When Agent B needs to think, Agent A's LLM context is unloaded, and B's is loaded. This trades speed for capability.

## 5. Testing Strategy
*   **Unit Testing**: The OS-manager design makes unit testing trivial. The `Agent Manager` can be tested in isolation by injecting a Mock `Event Bus` and asserting that it emits the correct `AgentSuspendedEvent` when a mock `ResourceCriticalEvent` is received.
*   **Integration Testing**: Boot the entire Kernel with Mock Providers in the `Provider Registry` to ensure the `Lifecycle Manager` transitions states correctly without requiring real hardware monitoring.

## 6. Required ADRs for Phase 1
Before or during Phase 1 implementation, the following ADRs will be finalized in `docs/decisions/`:
*   `0005-os-kernel-architecture.md` (Documenting the 12 managers)
*   `0006-event-driven-bus.md`
*   `0007-vram-context-switching.md` (Addressing the 4GB constraint)
*   `0008-provider-registry-pattern.md`