# Phase 1: Chhaya Kernel Design Proposal

## 1. Executive Summary
This document proposes the architecture for the Chhaya Kernel, the central orchestrator of the Chhaya Agent Factory. The Kernel is designed to manage agent lifecycles, route asynchronous events, load extensible plugins, and provide dependency injection for abstraction layers (LLMs, Memory, Tools).

## 2. Kernel Responsibilities
The Kernel's primary responsibilities are:
1. **Bootstrapping**: Initializing telemetry, configuration, and security constraints.
2. **Component Registry**: Managing dependency injection for providers (LLMs, Memory).
3. **Plugin Management**: Loading and validating third-party extensions.
4. **Event Routing**: Processing synchronous API calls and asynchronous system events.
5. **Agent Orchestration**: Managing the lifecycle, memory constraints, and execution loops of running agents.

---

## 3. Architecture Deep Dive

### 3.1 Internal Package Structure (`packages/kernel`)
The Kernel will be internally modularized to ensure separation of concerns:
*   `kernel/core.py`: The `ChhayaKernel` singleton/main class.
*   `kernel/registry.py`: Dependency injection container.
*   `kernel/loader.py`: The Plugin loader subsystem.
*   `kernel/orchestrator.py`: Agent lifecycle manager.
*   `kernel/scheduler.py`: Background task/event scheduler.

### 3.2 Agent Lifecycle Management
Agents in Chhaya must be ephemeral due to the **4GB VRAM constraint**.
*   **Design**: The `orchestrator` will manage agent "Sessions". When an agent yields (waits for a tool or user input), its context is serialized to the `MemoryProvider` and the LLM is flushed from VRAM.
*   **Trade-off**: Memory swapping adds latency (loading/unloading models).
*   **Alternative**: Keep models resident in VRAM. This is faster but limits the system to a single small model, violating the "multi-agent ecosystem" vision.
*   **Recommendation**: Adopt the swapping/ephemeral state model.

### 3.3 Event Bus Architecture
The system will rely heavily on `packages/event_bus`.
*   **Design**: A local, async Pub/Sub system (e.g., using `asyncio.Queue`).
*   **Trade-off**: A local queue does not scale across multiple machines.
*   **Alternative**: Use Redis or RabbitMQ.
*   **Recommendation**: Use a native Python `asyncio` bus for Phase 1 to satisfy the "Local-First" and zero-setup constraint. The interface should be strict enough that a Redis adapter can be swapped in later without changing Agent code.

### 3.4 Provider Registry & Dependency Injection (DI)
*   **Design**: The Kernel will initialize a DI container on boot. Providers (e.g., `OllamaProvider`, `SQLiteMemoryProvider`) will be instantiated and mapped to their respective Interfaces (`LLMProvider`, `MemoryProvider`).
*   **Alternative**: Use a heavy third-party DI framework (e.g., `python-dependency-injector`).
*   **Recommendation**: Implement a lightweight, native dict-based registry in `kernel/registry.py`. Third-party frameworks add unnecessary bloat and learning curves for open-source contributors.

### 3.5 Plugin Loader
*   **Design**: The Kernel scans a designated `plugins/` directory. It uses `importlib` to dynamically load Python modules that subclass `plugin_sdk.Plugin`.
*   **Security**: Plugins run in the same process space.
*   **Recommendation**: Accept in-process plugins for Phase 1. Future phases (Phase 5) will introduce sandboxed execution (e.g., WASM or separate Docker containers) for untrusted plugins.

### 3.6 State Management & Scheduler
*   **Design**: The Kernel state (active agents, loaded models) will be managed by a thread-safe `State` object. The `Scheduler` will be an `asyncio` task loop that monitors timeouts and triggers scheduled background agents.

### 3.7 Permission Framework
*   **Design**: Every Event and Tool Execution request will pass through `security.SecurityManager.verify_permission()`. For Phase 1, this will default to "Allow All" locally, but the hooks must be in place.

### 3.8 Logging & Configuration Integration
*   **Design**: The Kernel's first boot step is initializing `packages/telemetry` (using structured JSON logging for API consumption and readable console logging for local dev) and `packages/config` (reading from `.env` and `os.environ`).

### 3.9 Testing Strategy
*   **Design**: The Kernel must be 100% testable without loading real LLMs or databases.
*   **Recommendation**:
    1.  **Unit Tests (`pytest`)**: Use mock Providers injected into the registry to test `orchestrator` and `scheduler` logic.
    2.  **Integration Tests**: Run the Kernel alongside a mock `FastAPI` instance to verify end-to-end event flowing through the `event_bus` without external IO.
    3.  **Coverage**: Enforce a strict minimum test coverage (e.g., 90%) for the `packages/kernel` directory via `pytest-cov`.

---

## 4. Required ADRs for Phase 1
Before or during Phase 1 implementation, the following ADRs will be created in `docs/decisions/`:
*   `0005-dependency-injection-strategy.md`
*   `0006-async-event-bus-implementation.md`
*   `0007-agent-memory-swapping.md`
*   `0008-plugin-loading-mechanism.md`

## 5. Conclusion
This architecture guarantees that the Kernel acts as a true Operating System—managing resources (VRAM via the Orchestrator), handling IPC (Event Bus), and exposing hardware (Providers/Tools). It avoids locking into LangChain paradigms directly at the core.
