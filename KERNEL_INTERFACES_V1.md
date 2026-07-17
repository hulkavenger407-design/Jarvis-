# KERNEL_INTERFACES_V1.md

## Document Purpose
This document is the authoritative specification for all remaining frozen kernel interfaces in the Chhaya AI Operating System. It defines the missing interfaces required by the master architecture and cross-references existing ones. This is a specification document only; it does not contain implementation.

---

## 1. Existing Frozen Interfaces (Summary)

The following interfaces are already defined and frozen within the kernel package:

### 1.1 `IEventBus`
* **Purpose**: Core messaging backbone for event-driven communication.
* **Implemented By**: Kernel Event Bus subsystem (`packages/kernel/src/kernel/eventbus/`).
* **Consumed By**: All subsystems mutating state or responding to domain events.
* **Status**: Exists in `packages/kernel/src/kernel/interfaces.py`.

### 1.2 `IStateManager`
* **Purpose**: Centralized persistence for state records, transactions, and snapshots.
* **Implemented By**: Kernel State Manager subsystem (`packages/kernel/src/kernel/statemanager/`).
* **Consumed By**: Agent Runtime, Capability Execution Engine, Memory Engine, Conversation Engine.
* **Status**: Exists in `packages/kernel/src/kernel/interfaces.py`.

### 1.3 `IMemoryEngine`
* **Purpose**: Low-level asynchronous storage operations for multiple memory tiers.
* **Implemented By**: Kernel Memory Engine subsystem (`packages/kernel/src/kernel/memory/`).
* **Consumed By**: Knowledge Engine, Context Builder.
* **Status**: Exists in `packages/kernel/src/kernel/interfaces.py`.

### 1.4 `IAgentRuntime`
* **Purpose**: Manages multi-agent lifecycles and coordinates planning/execution loops.
* **Implemented By**: Kernel Agent Runtime subsystem (`packages/kernel/src/kernel/agent_runtime/`).
* **Consumed By**: Interfaces (API/UI), Supervisor Agent.
* **Status**: Exists in `packages/kernel/src/kernel/interfaces.py`.

### 1.5 `IVectorStore`
* **Purpose**: Abstraction for vector similarity search backends.
* **Implemented By**: Infrastructure Adapters (e.g., Qdrant).
* **Consumed By**: Kernel Memory Engine, Knowledge Engine (RAG).
* **Status**: Exists in `packages/kernel/src/kernel/memory/interfaces.py`.

### 1.6 `ICapability`
* **Purpose**: Defines the contract for an executable action or tool.
* **Implemented By**: Capability Plugins (Browser, Desktop, Voice, Vision, Code).
* **Consumed By**: Capability Execution Engine.
* **Status**: Exists in `packages/kernel/src/kernel/capability_registry/interfaces.py`.

### 1.7 `IProvider` / `ILifecycleProvider`
* **Purpose**: Base interface for dynamically discoverable plugins and services.
* **Implemented By**: All loadable plugins and adapters.
* **Consumed By**: Provider Registry, DI Container.
* **Status**: Exists in `packages/kernel/src/kernel/provider_registry/interfaces.py`.

---

## 2. Unnecessary Interfaces (Review)

Per the architecture audit, the following interfaces are deemed unnecessary as discrete interfaces:

* **`IKnowledgeLayer`**: The Knowledge Layer is a structural grouping of subsystems (Knowledge Engine, RAG, Embeddings, Context Builder, User Profile) and not a single programmatic interface. Interactions occur via event publication and specific interfaces like `IVectorStore` or `IIndexingPipeline`.
* **`ICognitiveLayer`**: Similar to the Knowledge Layer, this is an architectural collection of cognitive subsystems (Model Router, Planner, Reasoning, etc.) and does not expose a monolithic interface.
* **`IReasoner`**: The architecture mentions a Reasoning subsystem. However, reasoning is typically executed as an internal step of the Agent Runtime calling the Model Router with specific prompts. No standalone `IReasoner` interface is specified as a frozen kernel interface requirement.
* **`ISemanticSearch`**: Semantic search is a feature of the RAG subsystem built on top of the existing `IVectorStore` interface. A separate kernel interface for semantic search is not explicitly required by the architecture.

---

## 3. Missing Interfaces Specification

### 3.1 Kernel & Execution Interfaces

#### 3.1.1 `ICapabilityEngine` (Capability Execution Engine)
* **Purpose**: Executes a requested capability through its registered adapter, enforcing isolation, timeouts, and permissions.
* **Responsibilities**: Sandbox creation, permission verification, invocation, and error handling for capabilities.
* **Dependencies**: `ICapabilityRegistry`, `IStateManager`, `IEventBus`.
* **Allowed Dependencies**: Kernel primitives.
* **Forbidden Dependencies**: Concrete capability implementations, Infrastructure adapters.
* **Lifecycle Requirements**: Initialized during boot; long-lived singleton.
* **Concurrency Requirements**: Async-safe; handles multiple capability invocations concurrently.
* **Async Requirements**: Fully asynchronous.
* **Error Behavior**: Returns `Result` or raises defined domain exceptions; transitions capability to FAILED on critical errors.
* **Cross-Reference**: Implemented by Kernel (Capability Execution Engine). Consumed by Workflow Engine, Agent Runtime. Blocked by missing definition.
```python
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

class ICapabilityEngine(Protocol):
    async def invoke(self, capability_id: str, security_context: Any, payload: dict[str, Any]) -> dict[str, Any]:
        ...
    async def cancel(self, execution_id: str) -> None:
        ...
    async def get_status(self, execution_id: str) -> str:
        ...
```

#### 3.1.2 `ICapabilityResolver`
* **Purpose**: Resolves capability IDs to their registered interface implementations.
* **Responsibilities**: Lookup capabilities via the DI Container.
* **Dependencies**: `IDIContainer`, `ICapabilityRegistry`.
* **Allowed Dependencies**: Kernel primitives.
* **Forbidden Dependencies**: Infrastructure adapters.
* **Cross-Reference**: Implemented by Kernel. Consumed by Planner, Capability Engine.
```python
class ICapabilityResolver(Protocol):
    def resolve(self, capability_id: str) -> Any:
        ...
```

#### 3.1.3 `IKernelHealth`
* **Purpose**: Reports the overall health of the kernel and its subsystems.
* **Responsibilities**: Aggregating subsystem health checks.
* **Cross-Reference**: Implemented by Kernel. Consumed by API Server (Infrastructure).
```python
class IKernelHealth(Protocol):
    async def check_health(self) -> dict[str, Any]:
        ...
```

#### 3.1.4 `IKeyValueStore`
* **Purpose**: Abstraction for persistent key-value storage.
* **Cross-Reference**: Implemented by Memory Engine (or Adapters). Consumed by Memory Engine.
```python
class IKeyValueStore(Protocol):
    async def get(self, namespace: str, key: str) -> bytes | None: ...
    async def put(self, namespace: str, key: str, value: bytes) -> None: ...
    async def delete(self, namespace: str, key: str) -> None: ...
```

#### 3.1.5 `IGraphStore`
* **Purpose**: Abstraction for graph database operations.
* **Cross-Reference**: Implemented by Infrastructure Adapters (e.g., Neo4j). Consumed by Knowledge Layer (User Profile).
```python
class IGraphStore(Protocol):
    async def add_node(self, node_id: str, properties: dict[str, Any]) -> None: ...
    async def add_edge(self, from_id: str, to_id: str, relation: str, properties: dict[str, Any]) -> None: ...
    async def query(self, query_string: str) -> list[dict[str, Any]]: ...
```

### 3.2 Cognitive Layer Interfaces

#### 3.2.1 `IModelAdapter`
* **Purpose**: Abstraction for communicating with language models.
* **Responsibilities**: Send prompts to LLMs and return raw or structured responses.
* **Allowed Dependencies**: Standard libraries.
* **Forbidden Dependencies**: Direct UI or database connections.
* **Error Behavior**: Propagates rate limit or timeout errors cleanly.
* **Cross-Reference**: Implemented by Infrastructure (e.g., LiteLLM Adapter). Consumed by Model Router.
```python
class IModelAdapter(Protocol):
    async def generate(self, prompt: str, parameters: dict[str, Any] | None = None) -> str:
        ...
    async def generate_structured(self, prompt: str, schema: dict[str, Any], parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        ...
    def health_check(self) -> bool:
        ...
```

#### 3.2.2 `IPlanner`
* **Purpose**: Decomposes user intents into executable plans.
* **Cross-Reference**: Implemented by Cognitive Layer (Planner). Consumed by Conversation Agent, Workflow Engine.
```python
class IPlanner(Protocol):
    async def plan(self, goal: str, context: dict[str, Any]) -> Any:
        ...
    async def reevaluate(self, current_plan: Any, error_context: dict[str, Any]) -> Any:
        ...
```

#### 3.2.3 `IWorkflowEngine`
* **Purpose**: Executes plan graphs and manages parallel branches.
* **Cross-Reference**: Implemented by Cognitive Layer. Consumed by Planner, Agent Runtime.
```python
class IWorkflowEngine(Protocol):
    async def activate_plan(self, plan: Any) -> None:
        ...
    async def cancel_plan(self, plan_id: str) -> None:
        ...
```

### 3.3 Knowledge Layer Interfaces

#### 3.3.1 `IEmbeddingModel`
* **Purpose**: Generates vector representations of text.
* **Cross-Reference**: Implemented by Infrastructure (Adapters). Consumed by Embeddings subsystem.
```python
class IEmbeddingModel(Protocol):
    async def embed_text(self, text: str) -> list[float]:
        ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...
    def health_check(self) -> bool:
        ...
```

#### 3.3.2 `IIndexingPipeline`
* **Purpose**: Manages document ingestion, chunking, and embedding.
* **Cross-Reference**: Implemented by Infrastructure (e.g., LlamaIndex Adapter). Consumed by Knowledge Engine.
```python
class IIndexingPipeline(Protocol):
    async def ingest(self, source_data: bytes, metadata: dict[str, Any]) -> list[str]:
        ...
```

### 3.4 Capability Layer Interfaces

#### 3.4.1 `IBrowserDriver`
* **Purpose**: Automates web interactions.
* **Cross-Reference**: Implemented by Infrastructure (Playwright Adapter). Consumed by Browser Capability.
```python
class IBrowserDriver(Protocol):
    async def navigate(self, url: str) -> None: ...
    async def scrape_text(self, selector: str | None = None) -> str: ...
    async def click(self, selector: str) -> None: ...
    async def fill(self, selector: str, value: str) -> None: ...
    def health_check(self) -> bool: ...
```

#### 3.4.2 `IDesktopAutomation`
* **Purpose**: Controls desktop applications and window management.
* **Cross-Reference**: Implemented by Infrastructure (Tauri API). Consumed by Desktop Capability.
```python
class IDesktopAutomation(Protocol):
    async def execute_macro(self, macro_name: str, parameters: dict[str, Any]) -> Any: ...
    def health_check(self) -> bool: ...
```

#### 3.4.3 `IVisionService`
* **Purpose**: Provides screen understanding and OCR capabilities.
* **Cross-Reference**: Implemented by Infrastructure Adapters. Consumed by Vision Capability.
```python
class IVisionService(Protocol):
    async def analyze_image(self, image_bytes: bytes, prompt: str) -> str: ...
    async def extract_text(self, image_bytes: bytes) -> str: ...
    def health_check(self) -> bool: ...
```

#### 3.4.4 `ISpeechToText`
* **Purpose**: Transcribes audio to text.
* **Cross-Reference**: Implemented by Infrastructure (Faster-Whisper). Consumed by Voice Capability.
```python
class ISpeechToText(Protocol):
    async def transcribe(self, audio_bytes: bytes) -> str: ...
    def health_check(self) -> bool: ...
```

#### 3.4.5 `ITextToSpeech`
* **Purpose**: Synthesizes text to audio.
* **Cross-Reference**: Implemented by Infrastructure (Piper). Consumed by Voice Capability.
```python
class ITextToSpeech(Protocol):
    async def synthesize(self, text: str) -> bytes: ...
    def health_check(self) -> bool: ...
```

#### 3.4.6 `ICodeExecutor`
* **Purpose**: Safely runs user-supplied or AI-generated code.
* **Cross-Reference**: Implemented by Infrastructure (OpenHands). Consumed by Code Execution Capability.
```python
class ICodeExecutor(Protocol):
    async def execute_code(self, code: str, language: str) -> dict[str, Any]: ...
    def health_check(self) -> bool: ...
```

### 3.5 Infrastructure Layer Interfaces

#### 3.5.1 `IConfigurationProvider`
* **Purpose**: Loads and merges hierarchical configuration data.
* **Cross-Reference**: Implemented by Infrastructure. Consumed by all layers.
```python
class IConfigurationProvider(Protocol):
    def get_value(self, key: str, default: Any = None) -> Any: ...
    def load_schema(self, namespace: str, schema: dict[str, Any]) -> None: ...
```

#### 3.5.2 `ITelemetrySink`
* **Purpose**: Collects traces, metrics, and logs securely.
* **Cross-Reference**: Implemented by Infrastructure (OpenTelemetry). Consumed by all layers.
```python
class ITelemetrySink(Protocol):
    def record_metric(self, name: str, value: float, tags: dict[str, str]) -> None: ...
    def log_event(self, level: str, message: str, attributes: dict[str, Any]) -> None: ...
    def start_span(self, name: str, context: dict[str, Any]) -> Any: ...
```

#### 3.5.3 `IObservabilityBackend`
* **Purpose**: LLM-specific tracing and evaluation.
* **Cross-Reference**: Implemented by Infrastructure (Langfuse). Consumed by Cognitive Layer.
```python
class IObservabilityBackend(Protocol):
    async def export_trace(self, trace_data: Any) -> None: ...
    async def export_metrics(self, metrics_data: Any) -> None: ...
```

#### 3.5.4 `IAuthorizationService`
* **Purpose**: Evaluates authorization policies (ABAC).
* **Cross-Reference**: Implemented by Infrastructure (Casbin). Consumed by Permission Manager, Security Context.
```python
class IAuthorizationService(Protocol):
    async def authorize(self, security_context: Any, action: str, resource: str) -> bool: ...
```

#### 3.5.5 `IPermissionStore`
* **Purpose**: Manages fine-grained capability access permissions.
* **Cross-Reference**: Implemented by Infrastructure. Consumed by Permission Manager.
```python
class IPermissionStore(Protocol):
    async def get_permissions(self, subject: str) -> list[str]: ...
    async def set_permissions(self, subject: str, permissions: list[str]) -> None: ...
```

#### 3.5.6 `IConsentManager`
* **Purpose**: Manages user consent for capability executions.
* **Cross-Reference**: Implemented by Infrastructure. Consumed by Permission Manager.
```python
class IConsentManager(Protocol):
    async def request_consent(self, user_id: str, capability_id: str, scope: str) -> bool: ...
    async def check_consent(self, user_id: str, capability_id: str) -> bool: ...
```

#### 3.5.7 `IHttpServer`
* **Purpose**: Exposes REST/WebSocket endpoints.
* **Cross-Reference**: Implemented by Infrastructure (FastAPI). Consumed by API interfaces.
```python
class IHttpServer(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def register_route(self, path: str, method: str, handler: Callable[..., Awaitable[Any]]) -> None: ...
```

### 3.6 Agent Hierarchy Interfaces

#### 3.6.1 `ISupervisorPolicy`
* **Purpose**: Coordinates goals and delegates to child agents.
* **Cross-Reference**: Implemented by Supervisor Agent. Consumed by Agent Runtime.
```python
class ISupervisorPolicy(Protocol):
    async def evaluate_delegation(self, goal: str, available_agents: list[str]) -> str | None: ...
    async def resolve_conflict(self, conflict_context: dict[str, Any]) -> dict[str, Any]: ...
```

#### 3.6.2 `IAgentDirectory`
* **Purpose**: Resolves specialized agent identities.
* **Cross-Reference**: Implemented by Agent Runtime. Consumed by Supervisor Agent.
```python
class IAgentDirectory(Protocol):
    async def lookup_agent(self, role: str) -> str | None: ...
    async def register_agent(self, agent_id: str, role: str, capabilities: list[str]) -> None: ...
```

#### 3.6.3 `IConversationManager`
* **Purpose**: Manages dialogue state and threading.
* **Cross-Reference**: Implemented by Conversation Agent. Consumed by Planner, Supervisor.
```python
class IConversationManager(Protocol):
    async def add_turn(self, session_id: str, text: str, role: str) -> None: ...
    async def get_context(self, session_id: str, max_turns: int) -> list[dict[str, str]]: ...
```

#### 3.6.4 `IResearcher`
* **Purpose**: Performs deep information retrieval and summarization.
* **Cross-Reference**: Implemented by Research Agent. Consumed by Planner Agent.
```python
class IResearcher(Protocol):
    async def research(self, topic: str, depth: int) -> dict[str, Any]: ...
```

#### 3.6.5 `IReflectionEngine`
* **Purpose**: Analyzes agent outputs against expectations.
* **Cross-Reference**: Implemented by Reflection Agent. Consumed by Workflow Engine, Learning Agent.
```python
class IReflectionEngine(Protocol):
    async def evaluate_outcome(self, task_id: str, expected: Any, actual: Any) -> dict[str, Any]: ...
```

#### 3.6.6 `ILearningPipeline`
* **Purpose**: Updates procedural and long-term memory from feedback.
* **Cross-Reference**: Implemented by Learning Agent. Consumed by Reflection Agent.
```python
class ILearningPipeline(Protocol):
    async def process_feedback(self, improvement_signal: dict[str, Any]) -> None: ...
```

---

## 4. Architecture Observations & Open Questions

* **`ISpeechIO` vs `ISpeechToText` / `ITextToSpeech`**: Section 9.1 mentions `ISpeechIO`, but Section 19 explicitly defines `ISpeechToText` and `ITextToSpeech`. This document specifies them separately for interface segregation, but they could be combined if desired.
* **Security Context Propagation**: Methods in `ICapabilityEngine` and `IAuthorizationService` accept a `SecurityContext` (represented here as `Any`). A strict type/dataclass should be defined in `kernel/models.py`.
* **Helper Interfaces**: Adapters might require factories (e.g., `IAdapterFactory`), but these have not been defined here to avoid inventing architecture, per constraints.
