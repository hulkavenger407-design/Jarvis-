# ADR 0010: State Manager Architecture

## Status
Accepted

## Context
As the Chhaya OS scales to manage complex, multi-agent workflows, state management becomes a critical bottleneck. State exists across multiple categories: Kernel, Agent, Session, Workflow, Plugin, Provider, and Capability. Direct manipulation of global or nested dictionaries introduces race conditions, makes rollback impossible, and deeply couples subsystems to specific storage mechanics (e.g., SQLite vs Redis).

We need a unified State Manager to act as the single source of truth for all operational state, ensuring async safety and future distributed persistence without polluting the business logic.

## Decision
We will implement a unified **State Manager** as Subsystem 8.
- **Categorization:** It will strictly partition state by category (`Kernel`, `Agent`, `Session`, etc.) to prevent cross-contamination.
- **Transactions & Snapshots:** It will enforce a transaction model (`StateTransaction`) that generates atomic `StateChange` records, allowing for safe `StateSnapshot` generation and rollback strategies.
- **Storage Abstraction:** It will depend on a `StateBackend` protocol. For Phase 1, an in-memory backend will be used, but the architecture will fully support swapping to persistent backends (like Redis or PostgreSQL) in the future.
- **Observability:** It will publish state mutations to the `EventBus` (`state.changed.started`, `state.transaction.committed`) and support a `StateObserver` pattern for synchronous reactivity.

## Alternatives Considered
- **Decentralized State:** Allowing each subsystem (AgentManager, SessionManager) to hold its own state internally in raw variables or bespoke databases.
- **Direct Database Coupling:** Tightly coupling the State Manager to SQLite for phase 1.

## Trade-offs
- **Pros:** A unified State Manager eliminates race conditions via strict async/transactional boundaries. The backend abstraction ensures that migrating the kernel from a single laptop to a distributed cloud later will not require rewriting agent logic. The event-driven hook model natively supports time-travel debugging and UI reactivity.
- **Cons:** It introduces memory allocation and computational overhead due to the generation of intermediate transaction objects and deep copies required for snapshots.

## Long-term Implications
By abstracting state into explicit transactions and snapshots now, we guarantee that long-running agents (which may take days to complete a task) can be safely suspended (VRAM flushing), serialized, and resurrected perfectly across hardware reboots without data loss.
