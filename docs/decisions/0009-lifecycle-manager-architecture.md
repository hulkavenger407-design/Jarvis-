# ADR 0009: Lifecycle Manager Architecture

## Status
Accepted

## Context
As the Chhaya Kernel grows with discrete OS-like managers (DI Container, Event Bus, Config Manager, Provider Registry, Plugin Manager), it requires a centralized orchestrator to coordinate their initialization and termination. Without this, managers might boot out of order (e.g., trying to load plugins before the Event Bus is ready) or fail to shut down cleanly, leading to corrupted state, leaked file handles, or abandoned GPU processes.

## Decision
We will implement a dedicated **Lifecycle Manager** as Subsystem 6.
- It will act as the finite state machine for the entire OS.
- It will enforce a strict multi-stage boot sequence (`INITIALIZING`, `STARTING`, `RUNNING`) and a shutdown sequence (`STOPPING`, `SHUTDOWN`).
- It will publish state transitions over the Event Bus.
- It will monitor subsystem health and gracefully degrade or halt the system if critical subsystems fail to initialize.

## Alternatives Considered
- **BootManager / Main Script logic:** Handling boot sequences inside `main.py` or a procedural bootstrap script.
- **Event-Driven Choreography:** Emitting a "Boot" event and letting all managers figure out when to start themselves based on subsequent events.

## Trade-offs
- **Pros:** A centralized Lifecycle Manager guarantees deterministic boot ordering. It provides a single choke point for health checks and graceful termination, which is crucial for handling signals (SIGINT/SIGTERM) correctly in an OS context.
- **Cons:** It acts as a central orchestration bottleneck, slightly coupling the high-level startup logic of the various managers into one place.

## Long-term Implications
This solidifies the Chhaya Kernel as a robust application server. By enforcing strict, hook-based lifecycle stages, developers can safely inject long-running background tasks, API servers, and UI dashboards, knowing exactly when it is safe to begin listening for traffic or accepting agent requests.