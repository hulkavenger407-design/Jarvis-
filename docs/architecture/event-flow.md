# Event Flow Architecture

The Chhaya Agent Factory utilizes an Event-Driven Architecture to prevent tight coupling between modules.

## Architecture Diagram

```mermaid
sequenceDiagram
    participant Client as API / Client
    participant API as FastAPI
    participant Kernel as Chhaya Kernel
    participant Bus as Event Bus
    participant Agent as Agent Subsystem
    participant Tool as Tool Provider

    Client->>API: POST /agents/task (data)
    API->>Kernel: dispatch_task(data)
    Kernel->>Bus: publish(AGENT_TASK_RECEIVED)

    Bus-->>Agent: on(AGENT_TASK_RECEIVED)
    Agent->>Agent: Process prompt
    Agent->>Bus: publish(AGENT_THINKING)
    Bus-->>Kernel: on(AGENT_THINKING)
    Kernel-->>API: SSE Stream (Thinking...)
    API-->>Client: Stream chunk

    Agent->>Bus: publish(TOOL_EXECUTION_REQUESTED, tool_name)
    Bus-->>Tool: on(TOOL_EXECUTION_REQUESTED)
    Tool->>Tool: Execute local file system action
    Tool->>Bus: publish(TOOL_EXECUTION_COMPLETED, result)

    Bus-->>Agent: on(TOOL_EXECUTION_COMPLETED)
    Agent->>Agent: Formulate final response
    Agent->>Bus: publish(AGENT_TASK_COMPLETED, response)

    Bus-->>Kernel: on(AGENT_TASK_COMPLETED)
    Kernel-->>API: Task Completed Event
    API-->>Client: Final Response
```

## Description

The Event Bus guarantees that subsystems do not need to know about each other's specific implementations.
- The Agent subsystem does not invoke a specific tool directly; it emits a `TOOL_EXECUTION_REQUESTED` event.
- The Tool orchestrator listens for that event, executes the action behind the provider interface, and emits the result.
- The Kernel observes all events and can stream them out to clients (via Server-Sent Events or WebSockets) for real-time UI updates in the web dashboard.