# ADR 0009: Lifecycle Manager Architecture

## Status
Accepted

## Context
As the Chhaya Kernel grows with discrete OS-like managers (DI Container, Event Bus, Config Manager, Provider Registry, Plugin Manager), it requires a centralized orchestrator to coordinate their initialization and termination. Without this, managers might boot out of order (e.g., trying to load plugins before the Event Bus is ready) or fail to shut down cleanly, leading to corrupted state, leaked file handles, or abandoned GPU processes.

## Decision
We will implement a dedicated **Lifecycle Manager** as Subsystem 6 based on a **Topological Dependency Model**.
- It will act as the finite state machine for the entire OS.
- It will depend *only* on a generic `KernelSubsystem` protocol interface.
- It will dynamically construct a Directed Acyclic Graph (DAG) of subsystem dependencies.
- It will enforce a strict multi-stage boot sequence (`INITIALIZING`, `STARTING`, `RUNNING`) executing topologically, and a shutdown sequence (`STOPPING`, `SHUTDOWN`) executing in reverse topological order.

## Alternatives Considered
- **Event-Driven Choreography:** Emitting a "Boot" event and letting all managers figure out when to start themselves based on subsequent events. This was rejected because it leads to unpredictable race conditions during critical OS startup phases.
- **Hardcoded Boot Levels:** Manually assigning each subsystem an integer boot level (0, 1, 2). This was rejected because it tightly couples the Lifecycle Manager to the exact list of subsystems and requires modifying the manager every time a new subsystem is added.

## Trade-offs
- **Pros:** A topological DAG approach guarantees deterministic boot ordering while maintaining extreme decoupling. The Lifecycle Manager never needs to know what a `PluginManager` or `EventBus` is; it only sees `KernelSubsystem`s. It natively provides a single choke point for health checks (`HealthReport`) and graceful signal termination.
- **Cons:** Dependency resolution via topological sorting introduces slight runtime overhead during boot and requires developers to correctly annotate their subsystem dependencies.

## Long-term Implications
This solidifies the Chhaya Kernel as a highly extensible OS. We can effortlessly inject new subsystems (like a capability registry or a web dashboard gateway) just by tagging their dependencies. They will automatically boot precisely when they are supposed to, without altering the core Lifecycle Manager code.
