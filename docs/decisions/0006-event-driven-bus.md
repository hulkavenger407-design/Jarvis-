# ADR 0006: Event-Driven Bus & Payload Schema

## Status
Accepted

## Context
Subsystems within the OS architecture need to communicate without tightly coupling their codebases.

## Decision
We will use a central `Event Bus` as the primary IPC (Inter-Process Communication) mechanism.
- All events will follow a strict `DOMAIN.ACTION.STATUS` naming convention.
- All payloads will be strongly typed, versioned JSON/Pydantic schemas.

## Alternatives Considered
- **Direct Method Invocation:** Subsystems hold references to each other (e.g., `agent_manager.execute_tool()`).
- **External Message Broker (RabbitMQ):** Using an external service for IPC.

## Trade-offs
- **Pros:** Extreme decoupling. A new `PermissionManager` can simply listen to the bus and intercept events without rewriting the `AgentManager`.
- **Cons:** Tracing the execution flow of a single user request becomes more difficult because it is highly asynchronous.

## Long-term Implications
This guarantees the extensibility of the system. Plugins can interact with the entire OS simply by subscribing to or emitting standard events.