# Kernel Events Specification

The Chhaya Kernel utilizes an Event-Driven Architecture. This document specifies the conventions, schemas, and core events utilized by the Event Bus.

## 1. Event Naming Conventions
Events must be named using the `DOMAIN.ACTION.STATUS` convention to allow for wildcard subscriptions (e.g., `agent.*`).
*   **Domain:** The subsystem generating or targeted by the event (e.g., `system`, `agent`, `tool`, `memory`, `plugin`).
*   **Action:** The verb or process occurring (e.g., `boot`, `task`, `execute`, `query`).
*   **Status:** The current state (e.g., `requested`, `started`, `completed`, `failed`, `suspended`).

*Examples:*
*   `system.boot.completed`
*   `tool.execute.requested`
*   `agent.task.failed`

## 2. Event Versioning Strategy
To ensure backward compatibility as the system evolves (especially regarding plugins), events must carry a schema version.
*   The payload will include a `version` string (e.g., `"1.0"`).
*   Minor version bumps (`"1.1"`) indicate added fields (non-breaking).
*   Major version bumps (`"2.0"`) indicate removed/changed fields (breaking).
*   The `Event Bus` will eventually support middleware to map deprecated events to new formats if necessary.

## 3. Base Event Schema
All events published to the bus must adhere to this base schema (represented as JSON/Pydantic models):

```json
{
  "id": "uuid4",
  "type": "string (DOMAIN.ACTION.STATUS)",
  "version": "string (e.g., 1.0)",
  "timestamp": "iso8601 utc datetime",
  "source": "string (e.g., 'AgentManager', 'FastAPI')",
  "session_id": "optional uuid4 (for tracing user requests)",
  "payload": "object (specific to the event type)"
}
```

## 4. Core System Events

### 4.1 System & Lifecycle Events
*   `system.boot.started`: Emitted by BootManager.
*   `system.boot.completed`: Emitted when all managers are online.
*   `system.shutdown.requested`: Emitted to trigger graceful shutdown.
*   `system.resource.critical`: Emitted by ResourceManager (e.g., payload indicates VRAM > 90%).

### 4.2 Agent Events
*   `agent.session.created`: Payload contains `agent_id` and `session_id`.
*   `agent.task.requested`: Emitted when an API client asks an agent to do something. Payload: `{ "prompt": "string" }`.
*   `agent.execution.started`: Payload: `{ "agent_id": "uuid" }`.
*   `agent.execution.suspended`: Payload: `{ "reason": "vram_limit" | "waiting_for_user" }`.
*   `agent.task.completed`: Payload: `{ "result": "string or dict" }`.

### 4.3 Tool Events
*   `tool.execute.requested`: Emitted by an Agent. Payload: `{ "tool_name": "string", "args": {} }`.
*   `tool.execute.completed`: Emitted by a Provider. Payload: `{ "result": "any" }`.
*   `tool.execute.failed`: Payload: `{ "error": "string" }`.

### 4.4 Capability Engine Events
*   `capability.execution.requested`: Emitted when a capability execution is submitted. Payload: `{ "execution_id": "string", "capability": "string" }`
*   `capability.execution.authorized`: Emitted after successful capability authorization. Payload: `{ "execution_id": "string", "capability": "string" }`
*   `capability.execution.started`: Emitted when execution begins on a worker. Payload: `{ "execution_id": "string", "capability": "string" }`
*   `capability.provider.selected`: Emitted if a provider is resolved for execution. Payload: `{ "execution_id": "string", "provider": "string" }`
*   `capability.execution.completed`: Emitted on successful completion. Payload: `{ "execution_id": "string", "capability": "string" }`
*   `capability.execution.failed`: Emitted when execution fails and retries are exhausted. Payload: `{ "execution_id": "string", "capability": "string", "error": "string" }`
*   `capability.execution.timeout`: Emitted when an execution surpasses its timeout threshold. Payload: `{ "execution_id": "string", "capability": "string", "error": "string" }`
*   `capability.execution.retry`: Emitted when a capability execution fails but is scheduled for retry. Payload: `{ "execution_id": "string", "capability": "string" }`
*   `capability.execution.cancelled`: Emitted when execution is explicitly cancelled. Payload: `{ "execution_id": "string", "capability": "string" }`
*   `capability.execution.finished`: Emitted upon execution termination regardless of outcome. Payload: `{ "execution_id": "string" }`

### 4.5 Memory Events
*   `memory.store.requested`: Payload: `{ "key": "string", "data": "any", "ttl": "optional int" }`.
*   `memory.query.completed`: Payload: `{ "results": ["..."] }`.