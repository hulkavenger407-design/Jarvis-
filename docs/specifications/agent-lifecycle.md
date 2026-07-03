# Agent Lifecycle Specification

This document defines the strict lifecycle states and state machine logic for an AI Agent running inside the Chhaya Kernel. Due to hardware constraints (e.g., 4GB VRAM), managing this lifecycle is critical to prevent Out-Of-Memory (OOM) errors.

## 1. The Agent State Machine

Agents must strictly adhere to the following states. The `AgentManager` orchestrates these transitions based on events.

*   `UNINITIALIZED`: The agent definition exists, but no context has been allocated.
*   `LOADING`: The agent is pulling its `Session` context from the `MemoryProvider` and requesting VRAM allocation from the `ResourceManager`.
*   `IDLE`: The agent is loaded in RAM/VRAM but has no active tasks.
*   `THINKING`: The agent is actively utilizing the `LLMProvider` (consuming GPU cycles).
*   `WAITING_ON_TOOL`: The agent has emitted a `tool.execute.requested` event and is yielded, waiting for the result.
*   `WAITING_ON_USER`: The agent requires human-in-the-loop approval or input.
*   `SUSPENDED`: The `ResourceManager` has forced the agent out of VRAM due to hardware constraints. Its state is serialized to disk.
*   `TERMINATED`: The task is complete, or the session is explicitly closed. Memory is garbage collected.

## 2. Session Lifecycle
A `Session` binds an Agent to a specific interaction context (e.g., a conversation with a specific user on the Web Dashboard).
1.  **Creation:** An API request creates a Session. A `session_id` is generated.
2.  **Binding:** An Agent instance is assigned to the `session_id`. All memory written to the `MemoryProvider` during this interaction is tagged with this ID.
3.  **Resumption:** If a client disconnects and reconnects later, passing the `session_id` allows the `AgentManager` to resurrect the agent into the `LOADING` state, pulling the exact conversational history from the DB.
4.  **Expiration:** Sessions have a TTL (Time-To-Live). If an agent is `SUSPENDED` for longer than the TTL, the session is `TERMINATED`.

## 3. Task Lifecycle
A Task is a specific objective given to an agent within a session.
1.  `agent.task.requested` is received by the Kernel.
2.  The Kernel verifies the Session. If the Agent is `SUSPENDED`, it transitions to `LOADING`, then `IDLE`.
3.  The task is appended to the Agent's Short-Term Memory scratchpad.
4.  State moves to `THINKING`. The LLM generates a plan.
5.  State moves to `WAITING_ON_TOOL` as the agent executes its plan.
6.  Once the objective is met, state moves back to `IDLE` and `agent.task.completed` is emitted.

## 4. Recovery Behavior
The Kernel must handle failures gracefully.
*   **VRAM OOM Crash:** If the `LLMProvider` crashes due to memory limits, the `AgentManager` intercepts the error, transitions the agent to `SUSPENDED`, flags the task as `interrupted`, and attempts to restart the LLM provider with a smaller context window constraint.
*   **Tool Timeout:** If an agent remains in `WAITING_ON_TOOL` longer than the configured timeout, a `tool.execute.failed` event is forcibly injected into the `Event Bus`. The agent transitions back to `THINKING` so it can analyze the failure and attempt a different strategy.
*   **Kernel Panic:** If the entire OS process dies, the `BootManager` will read the last known good states from the local SQLite `MemoryProvider` upon next startup, resurrecting all persistent sessions into the `SUSPENDED` state.