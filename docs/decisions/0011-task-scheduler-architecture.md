# ADR 0011: Task Scheduler Architecture

## Status
Accepted

## Context
As the Chhaya OS begins executing agent workflows, we require a robust system to manage deferred, recurring, and asynchronous workloads. Relying exclusively on immediate `asyncio.create_task` or the `EventBus` limits our ability to enforce concurrency limits, queue priorities, cancel runaway jobs, or retry transient network failures (e.g., LLM provider rate limits). We need a dedicated Task Scheduler that treats background jobs as first-class entities with explicit lifecycles.

## Decision
We will implement a distributed-ready, asynchronous **Task Scheduler** as Subsystem 9.
- **Scheduling Model:** Tasks will be submitted with explicit triggers (OneShot, Interval, Cron) and priority levels (Critical, High, Default, Low).
- **Execution:** A worker pool will drain a `TaskQueue`, executing jobs via a `TaskExecutor` abstraction, enabling concurrency constraints.
- **Resilience:** Tasks will support strict timeouts, configurable `RetryPolicy` rules, and failure isolation via Dead Letter Queues (DLQ).
- **Dependencies:** The scheduler will support Task Dependency Graphs (DAGs), ensuring Task B only executes upon the successful completion of Task A.

## Alternatives Considered
- **Standard `asyncio` Loop:** Launching background tasks directly via `asyncio.create_task`. *Rejected:* Offers no queue prioritization, persistence, or simple retry abstractions.
- **Celery / Celery Beat:** Standard Python enterprise scheduler. *Rejected:* Violates the Local-First and zero-configuration constraints for Phase 1.

## Trade-offs
- **Pros:** A native Task Scheduler provides granular control over system load. By separating the `TaskQueue` from the `TaskExecutor`, we can easily swap the in-memory queue for a persistent Redis queue in future phases without rewriting agent logic.
- **Cons:** Building a native Cron and DAG-based executor introduces significant complexity compared to simple event-driven execution.

## Long-term Implications
This architecture ensures that agents can safely "sleep" or schedule future actions (e.g., "Check my email at 9 AM tomorrow") even if they are suspended from VRAM. When scaled, this subsystem will allow distributed worker nodes to pull tasks from a central queue, transforming Chhaya into a powerful multi-machine cluster.
