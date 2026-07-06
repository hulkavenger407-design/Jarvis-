# ADR 0012: Agent Runtime Architecture

## Context
With the foundational subsystems (DI Container, Config, Event Bus, Provider Registry, Plugin Manager, Lifecycle Manager, Capability Registry, State Manager, and Task Scheduler) firmly in place, the Chhaya Kernel requires an orchestrator to manage the actual AI Agents. Agents in this OS represent autonomous, stateful processes with specific personas, toolsets, context windows, and execution loops. The system requires an Agent Runtime (or Agent Manager) to govern their lifecycle, execution contexts, boundaries, and failure isolation, serving as the bridge between external API requests and internal asynchronous multi-agent orchestrations.

## Motivation
To fulfill the vision of an AI Operating System, the Agent Runtime must be more than a simple LangChain or LangGraph wrapper. It must:
- Act as the supervisor and isolator for Agent processes.
- Bind together capabilities (tools) from the `CapabilityRegistry` into isolated Agent Contexts.
- Interface with the `TaskScheduler` for asynchronous execution and planning loops.
- Delegate LLM provider abstraction dynamically via the `ProviderRegistry`.
- Ensure strict state tracking (e.g. `SLEEPING`, `THINKING`, `ACTING`, `PAUSED`, `FAULTED`) via the `StateManager`.
- Guarantee strict safety and resource isolation (especially to comply with the 4GB VRAM hardware constraint).

## Decision
We will implement an **Agent Runtime (Agent Manager) Subsystem** built upon the following principles:

1. **Agent State Machine & Lifecycle:** Agents will follow a strict, OS-like process state machine (`CREATED`, `INITIALIZED`, `IDLE`, `THINKING`, `ACTING`, `AWAITING_INPUT`, `SLEEPING`, `TERMINATED`, `FAULTED`).
2. **Context Isolation:** Each agent will execute within an `AgentContext`. This object holds references to memory bounds, accessible capabilities, temporary state, and access permissions, securely preventing side-channel leaks between agents.
3. **Event-Driven Execution:** The runtime will not run tight blocking loops. Instead, it will use the `EventBus` and `TaskScheduler` to yield execution. Transitions (e.g. from `IDLE` to `THINKING`) trigger asynchronous background tasks.
4. **Provider Agnostic Abstraction:** The runtime will consume interfaces (e.g., `LLMProvider`, `MemoryProvider`) rather than direct implementation details, enabling dynamic hot-swapping between Ollama (local) and cloud providers.
5. **Supervisor Model (Future-Proofing):** The runtime itself operates as the master supervisor, maintaining a registry of active agents. It tracks resource constraints and gracefully handles crashes.

## Alternatives Considered
1. **LangGraph/LangChain Native Engine:**
   - *Description:* Use LangGraph directly as the core orchestrator instead of a custom state machine.
   - *Trade-offs:* Tightly couples the OS to the LangChain ecosystem. LangGraph is excellent for workflows, but less suited for OS-level process management, resource constraints, and dynamic capability injection across a polyglot system.
   - *Verdict:* Rejected as the *core* runtime engine. LangGraph will be supported as a provider/plugin format later, but the core runtime must be framework-independent.

2. **Actor Model (e.g. Ray / Pykka):**
   - *Description:* Implement agents as pure Actors passing messages.
   - *Trade-offs:* Highly scalable, but introduces immense complexity and overhead for local-first systems constrained to 32GB RAM/4GB VRAM laptops.
   - *Verdict:* Rejected. Over-engineered for Phase 1. The custom Async Event-Driven state machine balances scale and local efficiency.

## Trade-offs
- **Complexity vs. Control:** Building a custom Agent Context and State Machine takes more upfront effort than simply wrapping an existing framework, but it guarantees total control over memory management and execution limits necessary for the strict local hardware constraints.
- **Asynchronous Overhead:** Relying heavily on the Event Bus and Task Scheduler for agent loops introduces slight latency compared to raw synchronous loops, but prevents deadlocks and enables seamless pausing/resuming.

## Failure Handling
- **Agent Fault Isolation:** If an agent encounters an unhandled exception during `execute`, the runtime catches it, publishes a `domain.agent.faulted` event, and transitions the agent to `FAULTED` state. The crash will *not* propagate to the Kernel or other agents.
- **Timeouts and Constraints:** Agent steps are submitted to the `TaskScheduler` with strict timeouts. If an LLM inference hangs, the TaskScheduler triggers a timeout, allowing the Agent Runtime to forcibly halt the agent action and initiate a retry or fallback.

## Isolation Model
- **Capability Scoping:** Agents cannot access tools globally. They are injected with a specific subset of capabilities from the `CapabilityRegistry` during instantiation.
- **Memory Bounding:** The `AgentContext` will restrict conversation history size to prevent context window overflow (crucial for local models with constrained VRAM).

## Security
- Capabilities must specify required permissions. The Agent Context enforces whether an agent has authorization to execute a capability (e.g. File System Write access).
- No agent has raw access to the Kernel's DI container or EventBus unless explicitly authorized to publish specific event subsets.

## Long-term Implications
This architecture positions Chhaya to eventually support complex multi-agent orchestrations. By treating agents as managed, isolated OS processes with standard states, we can build a top-level orchestrator that schedules agents across distributed machines, monitors their health via standard Kernel hooks, and safely halts rogue agents.
