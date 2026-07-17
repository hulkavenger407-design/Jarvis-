# KERNEL_INTERFACES_V1.md

## Document Purpose
This document is the authoritative specification for all frozen kernel interfaces in the Chhaya AI Operating System. It defines the missing interfaces required by the master architecture, classifies them strictly according to architectural boundaries, and resolves duplicate or conflicting definitions.

This is a specification document only. No implementation code is included.

---

## 1. Interface Classification and Audit Rules

According to the `CHHAYA_V1_MASTER_ARCHITECTURE.md` layered design:
* **Kernel Interfaces** (`packages/kernel/src/kernel/interfaces.py` and similar kernel-internal files): Must have zero external dependencies. They provide the core OS mechanisms. Only interfaces defined here are true "Frozen Kernel Interfaces."
* **Domain Interfaces** (Cognitive, Knowledge, Capability, Agent): Abstract policies and behavior but are NOT part of the kernel mechanisms. They sit above the kernel.
* **Infrastructure Interfaces**: Adapters that implement kernel or domain interfaces. They do not define the interfaces themselves; they consume them.

*Note on Duplicate Resolution:*
* `ISpeechIO` vs `ISpeechToText`/`ITextToSpeech`: The architecture explicitly lists `ISpeechToText` and `ITextToSpeech` as distinct in Section 19. `ISpeechIO` in Section 9 is a grouping term. The separated interfaces are the canonical ones.
* `ICapabilityEngine` vs `ICapabilityResolver`: `ICapabilityEngine` is a kernel subsystem that *contains* resolution logic. A separate `ICapabilityResolver` interface is unnecessary, as the engine itself provides the capability execution boundary.

---

## 2. Kernel Interfaces (Frozen Core)

These interfaces belong strictly inside the Kernel package. They represent the foundational, immutable mechanisms of the OS.

### 2.1 Existing Frozen Kernel Interfaces

*   **`IEventBus`**: Event-driven communication backbone. (Exists in `interfaces.py`)
*   **`IStateManager`**: Persistence for state records, transactions, and snapshots. (Exists in `interfaces.py`)
*   **`IMemoryEngine`**: Storage operations for multiple memory tiers. (Exists in `interfaces.py`)
*   **`IAgentRuntime`**: Agent lifecycle management. (Exists in `interfaces.py`)
*   **`IVectorStore`**: Vector similarity search. (Exists in `memory/interfaces.py`)
*   **`ICapability`**: Contract for an executable action. (Exists in `capability_registry/interfaces.py`)
*   **`IProvider` / `ILifecycleProvider`**: Dynamic plugin registration. (Exists in `provider_registry/interfaces.py`)

### 2.2 Missing Frozen Kernel Interfaces (To be added to the Kernel)

These must be defined within the Kernel as they represent core OS mechanisms or infrastructure contracts expected by the Kernel.

#### 2.2.1 `ICapabilityEngine`
* **Purpose**: Executes a requested capability, enforcing isolation, timeouts, and permissions.
* **Owner Subsystem**: Kernel (Capability Execution Engine).
* **Consuming Subsystem**: Workflow Engine, Agent Runtime.
* **Allowed Dependencies**: Kernel primitives (`IEventBus`, `IStateManager`).
* **Forbidden Dependencies**: Concrete capabilities, infrastructure adapters.
* **Lifecycle**: Long-lived singleton.
* **Async Requirements**: Fully asynchronous.
* **Error Behavior**: Transitions capability to FAILED on critical errors; returns Result types.
```python
class ICapabilityEngine(Protocol):
    async def invoke(self, capability_id: str, security_context: Any, payload: dict[str, Any]) -> dict[str, Any]:
        ...
    async def cancel(self, execution_id: str) -> None:
        ...
    async def get_status(self, execution_id: str) -> str:
        ...
```

#### 2.2.2 `IKernelHealth`
* **Purpose**: Reports the overall health of the kernel and its subsystems.
* **Owner Subsystem**: Kernel.
* **Consuming Subsystem**: API Server (Infrastructure).
* **Allowed Dependencies**: Kernel primitives.
* **Forbidden Dependencies**: None (internal state checks only).
```python
class IKernelHealth(Protocol):
    async def check_health(self) -> dict[str, Any]:
        ...
```

#### 2.2.3 `IKeyValueStore`
* **Purpose**: Abstraction for persistent key-value storage.
* **Owner Subsystem**: Kernel (Memory Engine).
* **Consuming Subsystem**: Memory Engine.
* **Allowed Dependencies**: None.
```python
class IKeyValueStore(Protocol):
    async def get(self, namespace: str, key: str) -> bytes | None: ...
    async def put(self, namespace: str, key: str, value: bytes) -> None: ...
    async def delete(self, namespace: str, key: str) -> None: ...
```

#### 2.2.4 `ITaskScheduler`
* **Purpose**: Asynchronous execution engine for delayed and recurring background jobs.
* **Owner Subsystem**: Kernel (Task Scheduler).
* **Consuming Subsystem**: Agent Runtime, Workflow Engine.
* **Allowed Dependencies**: Kernel primitives.
* **Forbidden Dependencies**: Concrete adapter frameworks like Temporal (these implement it).
```python
class ITaskScheduler(Protocol):
    async def schedule_task(self, task_payload: dict[str, Any], trigger: Any) -> str:
        ...
    async def cancel_task(self, task_id: str) -> None:
        ...
    async def get_task_status(self, task_id: str) -> str:
        ...
```

---

## 3. Infrastructure & Domain Interfaces (Outside Kernel)

These interfaces are explicitly defined in the architecture but **DO NOT** belong in the immutable Kernel core. They dictate policy (Cognitive/Knowledge) or represent external systems (Infrastructure Adapters) and belong in their respective layer definitions (e.g., `packages/interfaces/src/interfaces/` or within the layer packages themselves).

### 3.1 Infrastructure Adapter Interfaces
*(These are contracts defined to be implemented by infrastructure plugins)*

*   **`IModelAdapter`**: Communicates with language models (e.g., LiteLLM).
*   **`IConfigurationProvider`**: Loads hierarchical configuration.
*   **`ITelemetrySink`**: Collects traces, metrics, and logs (OpenTelemetry).
*   **`IObservabilityBackend`**: LLM tracing (Langfuse).
*   **`IAuthorizationService`**: ABAC policy evaluation (Casbin).
*   **`IHttpServer`**: REST/WebSocket endpoint manager (FastAPI).

### 3.2 Cognitive Layer Interfaces
*   **`IPlanner`**: Decomposes user intents into plan graphs.
*   **`IWorkflowEngine`**: Executes plan graphs and manages parallel branches.

### 3.3 Knowledge Layer Interfaces
*   **`IEmbeddingModel`**: Generates vector representations of text.
*   **`IIndexingPipeline`**: Manages document ingestion, chunking, and embedding.
*   **`IGraphStore`**: Abstraction for graph database operations (User Profile).

### 3.4 Capability Layer Interfaces
*   **`IBrowserDriver`**: Web automation (Playwright).
*   **`IDesktopAutomation`**: Desktop/window management (Tauri).
*   **`IVisionService`**: Screen understanding (Vision Models).
*   **`ISpeechToText`**: Audio to text (Faster-Whisper).
*   **`ITextToSpeech`**: Text to audio (Piper).
*   **`ICodeExecutor`**: Sandboxed code execution (OpenHands).

### 3.5 Agent Interfaces
*   **`ISupervisorPolicy`**: Coordinates goals across child agents.
*   **`IConversationManager`**: Manages dialogue state.
*   **`IReflectionEngine`**: Analyzes outcomes.
*   **`ILearningPipeline`**: Updates long-term memory from feedback.

---

## 4. Final Recommendations

### Final Frozen Interface List
The following interfaces are the canonical set that must be defined within `packages/kernel/src/kernel/interfaces.py` (or designated internal kernel interface files) to unblock Phase 1 implementation.

1.  `IEventBus` *(Existing)*
2.  `IStateManager` *(Existing)*
3.  `IMemoryEngine` *(Existing)*
4.  `IAgentRuntime` *(Existing)*
5.  `IVectorStore` *(Existing)*
6.  `ICapability` *(Existing)*
7.  `IProvider` *(Existing)*
8.  `ICapabilityEngine` *(Missing - required for Subsystem 11)*
9.  `ITaskScheduler` *(Missing - required for Subsystem 9 wrapper clarity / adapter drop-in)*
10. `IKernelHealth` *(Missing - required for overall observability)*
11. `IKeyValueStore` *(Missing - required for Memory Engine backend)*

### Deferred Interfaces
These interfaces are valid and architecturally required, but belong in layers outside the Kernel (e.g., Cognitive, Knowledge, Infrastructure). They should be implemented when their respective subsystems are built in future milestones, not during the Phase 1 Kernel freeze.

*   `IModelAdapter`, `IConfigurationProvider`, `ITelemetrySink`, `IObservabilityBackend`, `IAuthorizationService`, `IPermissionStore`, `IConsentManager`, `IHttpServer`
*   `IPlanner`, `IWorkflowEngine`
*   `IEmbeddingModel`, `IIndexingPipeline`, `IGraphStore`
*   `IBrowserDriver`, `IDesktopAutomation`, `IVisionService`, `ISpeechToText`, `ITextToSpeech`, `ICodeExecutor`
*   Agent-specific interfaces (`ISupervisorPolicy`, `IAgentDirectory`, `IConversationManager`, `IResearcher`, `IReflectionEngine`, `ILearningPipeline`)

### Rejected Interfaces
These interfaces are removed because they duplicate existing abstractions or represent architectural concepts rather than programmatic interfaces.

*   **`IKnowledgeLayer`**: Structural concept, not an interface.
*   **`ICognitiveLayer`**: Structural concept, not an interface.
*   **`IReasoner`**: Reasoning is a process utilizing `IModelAdapter` inside the Agent Runtime/Cognitive loop, not a distinct frozen interface.
*   **`ISemanticSearch`**: Subsumed by `IVectorStore` and RAG pipelines.
*   **`ISpeechIO`**: Superseded by explicit `ISpeechToText` and `ITextToSpeech` interfaces as defined in Section 19.
*   **`ICapabilityResolver`**: Responsibility belongs to the DI Container and `ICapabilityEngine` internally.
