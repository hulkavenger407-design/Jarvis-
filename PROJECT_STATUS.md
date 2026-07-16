jules-17875331461821373045-998f53fd
PROJECT STATUS

Project: Chhaya AI Operating System
Document Version: 1.1
Status: Active
Maintained By: Core Architecture Team
Parent Document: CHHAYA_V1_MASTER_ARCHITECTURE.md
Next Review: After completion of Milestone M1
Classification: Engineering Governance
Source of Truth: Master Architecture v1.0

Document Purpose

PROJECT_STATUS.md is the operational engineering dashboard for the Chhaya AI Operating System project. It records implementation progress, tracks milestones, identifies risks and technical debt, reports repository health, and measures engineering readiness. Unlike the Master Architecture document, which defines the system’s immutable design, PROJECT_STATUS.md reflects the current engineering state of the project and is updated continuously throughout development.

Document Change Log

Version Description
1.0 Initial release after Architecture Freeze
1.1 Added WBS, sequencing, development process, DoD, exit criteria, contributor workflow, ADR, API governance, dependency management, testing strategy, CI/CD, release management, operational readiness, documentation strategy, community governance, technical debt management, performance plan, engineering KPIs, risk register, versioning policy, document control
2.0 Reserved


Current Version: 0.1.0‑pre‑alpha (architecture freeze)
Current Phase: Architecture Complete — Implementation Readiness
Overall Completion: ~22% (Architecture 100%, Implementation 5%)
Architecture Status: Frozen
Implementation Status: Not started
Documentation Status: Master Architecture complete; implementation documentation pending
Testing Status: No implementation tests exist
Deployment Status: No builds or packages exist
Last Updated: 2026‑07‑13

---

Document Lifecycle

Created: Architecture Freeze
Updated: At every milestone completion
Review Frequency: End of every milestone (M1–M12)
Owner: Core Architecture Team

---

Related Documents

· CHHAYA_V1_MASTER_ARCHITECTURE.md (Source of Truth)
· PROJECT_STATUS.md (this document)
· DECISIONS.md
· IMPLEMENTATION_ROADMAP.md
· CONTRIBUTOR_GUIDE.md

---

Executive Summary

The Chhaya AI Operating System project has completed its architectural definition phase. The master architecture specification has been reviewed, finalised, and frozen. No further architectural changes are permitted without formal governance. The system is defined as a local‑first, event‑driven, modular AI operating system with a six‑layer architecture anchored by an immutable kernel. All design principles, subsystem boundaries, communication patterns, and integration strategies are fully documented. The project now transitions from architecture to implementation planning and foundation development. Implementation work has not yet begun, and no code exists outside of architectural documents and placeholder repositories. The next immediate priority is to establish the engineering infrastructure (repository structure, CI/CD pipelines, architecture fitness functions) and begin implementing the kernel.

---

Project Snapshot

```
Architecture       ████████████████████ 100%
Implementation     █□□□□□□□□□□□□□□□□□□□   5%
Documentation      ██████□□□□□□□□□□□□□□  30%
Testing            □□□□□□□□□□□□□□□□□□□□   0%
Release Readiness  □□□□□□□□□□□□□□□□□□□□   0%
```

---

---

## Repository Audit Summary

A comprehensive engineering audit of the codebase against the frozen `CHHAYA_V1_MASTER_ARCHITECTURE.md` and `IMPLEMENTATION_GUIDE.md` reveals that while the Kernel foundations (DI, Event Bus, State Manager) exist, they heavily rely on in-memory implementations and lack persistence. Crucially, the frozen interfaces defined in the implementation guide (`kernel/interfaces.py`) are missing, and existing interfaces (`packages/interfaces/src/interfaces/providers.py`) violate the naming conventions (`LLMProvider` vs `IModelAdapter`).

No architecture layer violations or circular dependencies were found in the current implementation. However, the lack of architecture fitness functions in CI is a critical gap. The Knowledge, Cognitive, Integration, and most Infrastructure/Interface layers are entirely missing.

## Updated Module Completion Matrix

| Module | Status | Completion % | Priority | Action |
| --- | --- | --- | --- | --- |
| Kernel Interfaces | Complete | 100% | P0 | Define frozen traits/protocols in `kernel/interfaces.py` |
| Architecture Fitness | Missing | 0% | P0 | Implement CI gate constraints |
| DI Container | Complete | 100% | P1 | Scoped resolution implemented |
| Event Bus | Exists | 80% | P1 | Implement transactional outbox (SQLite) |
| State Manager | Exists | 70% | P1 | Implement pluggable backends |
| Memory Engine | Missing | 0% | P2 | Implement ephemeral/persistent engine & vector store adapter |
| Provider Registry | Exists | 75% | P2 | Implement dynamic discovery |
| Capability Registry | Exists | 80% | P2 | Implement full lifecycle hooks |
| Scheduler | Exists | 80% | P2 | Back with State Manager for persistence |
| Agent Runtime | Exists | 70% | P3 | Implement isolation/sandboxing |
| Execution Engine | Exists | 70% | P3 | Implement sandboxing and pipeline stages |
| Infrastructure | Partial | 10% | P4 | Implement OSS adapters, Config, Auth |
| Knowledge Layer | Missing | 0% | P4 | Not Started |
| Cognitive Layer | Missing | 0% | P5 | Not Started |
| Interfaces | Partial | 5% | P6 | Implement gRPC/REST API |
| Integration Layer | Missing | 0% | P6 | Not Started |
| Plugin SDK | Partial | 20% | P7 | Create scaffolding CLI & hot-loading |
| Testing | Partial | 30% | P0 | Implement fitness functions |
| Documentation | Partial | 50% | P8 | Extract API documentation |

## Implementation Backlog

### Milestone 1 (Foundation & Interfaces)
**Task 1.1: Define Frozen Kernel Interfaces**
- **Files:** `packages/kernel/src/kernel/interfaces.py`, `packages/interfaces/src/interfaces/providers.py`
- **Dependencies:** None
- **Complexity:** Low
- **Acceptance Criteria:** `IEventBus`, `IStateManager`, `IMemoryEngine`, `IModelAdapter`, `IVectorStore` abstract classes defined with docstrings. Remove non-compliant `LLMProvider` etc.
- **Tests:** Contract tests stub

**Task 1.2: Architecture Fitness Functions in CI**
- **Files:** `tests/architecture/test_fitness.py`, `.github/workflows/ci.yml`
- **Dependencies:** None
- **Complexity:** Medium
- **Acceptance Criteria:** CI fails if kernel imports 3rd party frameworks. No circular imports allowed.
- **Tests:** Meta-tests for fitness functions

### Milestone 2 (Kernel Data Persistence)
**Task 2.1: State Manager SQLite Backend**
- **Files:** `packages/kernel/src/kernel/state_manager.py` (and new backend file)
- **Dependencies:** Kernel Interfaces
- **Complexity:** Medium
- **Acceptance Criteria:** StateManager supports SQLite backend with transactional guarantees.
- **Tests:** DB transaction tests, rollback tests

**Task 2.2: Event Bus Transactional Outbox**
- **Files:** `packages/event_bus/src/event_bus/bus.py`
- **Dependencies:** State Manager SQLite Backend
- **Complexity:** High
- **Acceptance Criteria:** EventBus writes to StateManager outbox before dispatch. Guaranteed exactly-once delivery.
- **Tests:** Idempotency integration tests, crash recovery tests

**Task 2.3: Memory Engine Implementation**
- **Files:** `packages/kernel/src/kernel/memory/engine.py`, `packages/kernel/src/kernel/memory/vector_store.py`
- **Dependencies:** DI Container, Kernel Interfaces
- **Complexity:** High
- **Acceptance Criteria:** Abstract memory storage with vector index adapter stub.
- **Tests:** Ephemeral storage tests

### Milestone 3 (Execution Core Hardening)
**Task 3.1: Task Scheduler Persistence**
- **Files:** `packages/kernel/src/kernel/task_scheduler.py`
- **Dependencies:** State Manager
- **Complexity:** Medium
- **Acceptance Criteria:** Tasks are written to StateManager. Survive process restarts.
- **Tests:** Process restart simulation tests

**Task 3.2: Capability Execution Sandboxing**
- **Files:** `packages/kernel/src/kernel/capability_engine.py`
- **Dependencies:** None
- **Complexity:** High
- **Acceptance Criteria:** Capabilities execute in isolated context (resource limits enforced).
- **Tests:** Isolation bypass tests

### Milestone 4+ (Infrastructure & Cognitive)
*(Tasks to be broken down once M3 is complete)*

## Recommended Next Milestone
**M1 Foundation (Remediation)**
The exact implementation order to minimize technical debt is to first solidify the **Frozen Kernel Interfaces** (fixing the naming violations in `providers.py` and creating `interfaces.py`), followed immediately by implementing **Architecture Fitness Functions** in CI. Only then should the team proceed to implementing data persistence for the State Manager and Event Bus.


Current Phase

Phase Name: Architecture Complete — Implementation Readiness

The project has exited the architectural design phase. All major architectural decisions are locked. The master architecture document serves as the immutable reference for all future engineering work. The team is currently preparing the development environment, defining the implementation roadmap, and establishing the automated guardrails (fitness functions) that will enforce architectural compliance throughout the codebase lifecycle. No production code has been written.

---

Current Focus

Primary Goal
Implement the Kernel Foundation:

· Dependency Injection Container
· Event Bus
· State Manager
· Provider Registry
· Kernel Interfaces

Secondary Goals

· Repository foundation
· CI/CD pipeline
· Architecture Fitness Functions
· Static Analysis
· Developer Environment

Blocked Work
No subsystem implementation may begin before Kernel interfaces are complete.

Success Definition
Milestone M1 completed successfully.

---

Architecture Freeze Notice

The Master Architecture has entered Architecture Freeze.
Architectural modifications require:

· Architecture Decision Record (ADR)
· Design Review
· Approval

Implementation may evolve.
Architecture may not.

---

Implementation Dependency Order

```
Repository
    ↓
Kernel
    ↓
Infrastructure
    ↓
Knowledge
    ↓
Cognitive
    ↓
Capabilities
    ↓
Interfaces
    ↓
Testing
    ↓
Packaging
    ↓
Release
```

---

Overall Progress

Progress is measured against the complete system as defined in the frozen architecture.

Area Completion Notes
Architecture 100% Master architecture document frozen; all layers and subsystems defined
Documentation 30% Architecture document complete; implementation, user, and developer docs absent
Kernel 0% Design complete; zero implementation
Infrastructure 0% Adapter interfaces defined; no code
Knowledge Layer 0% Design complete; no code
Cognitive Layer 0% Design complete; no code
Capabilities 0% Design complete; no code
Interfaces 0% API server, desktop/mobile shells not implemented
Testing 0% Fitness function definitions exist but not yet wired into CI
CI/CD 0% Pipeline not configured
Packaging 0% No installers or packages
Deployment 0% No builds or releases
Overall Project ~18% Architecture (100%) weighted at ~20% of total project effort; remaining 82% is implementation, testing, and deployment

---

Completed Work

All items listed below have been completed to the satisfaction of the architecture review process. The completion standard is design‑level definition, not implementation.

Architecture

· Vision and mission statement
· Architectural philosophy and tenets
· Non‑negotiable design principles (14 principles documented)
· High‑level system overview with six‑layer decomposition
· Layer responsibilities and dependency rules
· Kernel subsystem architecture (DI Container, Event Bus, State Manager, Provider Registry, Capability Registry, Task Scheduler, Agent Runtime, Capability Execution Engine, Memory Engine)
· Cognitive Layer subsystem architecture (Model Router, Prompt Engine, Planner, Reasoning, Workflow, Conversation, Reflection, Learning)
· Knowledge Layer subsystem architecture (Knowledge Engine, RAG, Embeddings, Context Builder, User Profile)
· Capability Layer subsystem architecture (Browser, Desktop, Voice, Vision, Code Execution, Automation)
· Infrastructure Layer subsystem architecture (Security, Permissions, Telemetry, Observability, Configuration, Plugins, API Server, Desktop App, Android App)
· Communication architecture (commands, events, queries; exact‑once Event Bus)
· Event architecture (transactional outbox, idempotent consumers, schema versioning)
· Data flow architecture (request lifecycle, memory flow)
· Configuration architecture (hierarchical merge, schema‑validated, migration support)
· Security architecture (ABAC, Casbin, Security Context propagation, audit log)
· Plugin architecture (manifest‑based discovery, isolation, sandboxing, lifecycle)
· Deployment architecture (single local process, optional Temporal, desktop/mobile packaging)
· Package organisation and ownership table
· OSS integration strategy with build‑vs‑integrate matrix
· Non‑functional requirements (performance, availability, privacy, security, extensibility, configurability, maintainability, portability)
· Scalability, reliability, and extensibility strategies
· Architecture constraints (7 immutable constraints)
· AI OS execution lifecycle (14‑step sequence)
· Agent hierarchy architecture (11 agent roles, supervision and coordination)
· Operating system state machine (15 states with transitions)
· Capability discovery architecture (8‑step pipeline, runtime sequence, sandboxing and lifecycle)
· Model routing strategy (5 routing dimensions, 5‑step policy chain, adapter‑based execution)
· Memory hierarchy (6 tiers, relationships with subsystems)
· Context assembly pipeline (6 stages)
· Error recovery architecture (error categories, recovery patterns)
· Observability pipeline and health check architecture
· Learning feedback loop (7‑step privacy‑preserving loop)
· Internal package dependency rules (9 enforced rules)
· Boot sequence
· Event naming standard
· Configuration hierarchy and merge rules
· Plugin compatibility policy (semver‑based)
· Architecture evolution policy
· Upgrade and migration strategy (pre‑flight, backup, migration, rollback)
· Architecture fitness functions (9 automated checks defined)
· Formal architecture review (Appendix A — 10 recommendations accepted)
· Architecture freeze

---

Work In Progress

The following activities are currently being prepared or initiated. No code has been committed.

· Implementation planning — Decomposing the architecture into an implementable backlog of tasks, with clear acceptance criteria derived from fitness functions.
· Engineering environment setup — Configuring the repository structure, branch policies, and required tooling (Python project scaffold, linting, type checking).
· CI/CD pipeline definition — Designing the pipeline that will run architecture fitness functions, unit tests, integration tests, and packaging steps on every change.
· Kernel interface specification — Formalising the kernel’s public interfaces as Python abstract base classes before any implementation begins.
· Developer documentation outline — Structuring the guides that will help contributors understand the architecture and development practices.

---

Remaining Work

All remaining work is implementation, testing, and delivery. The breakdown below follows the architectural package structure and delivery concerns.

Kernel Implementation

· DI Container implementation
· Event Bus implementation with transactional outbox
· State Manager implementation (event store, snapshots)
· Provider Registry and Capability Registry
· Capability Execution Engine (with permission enforcement and sandboxing)
· Task Scheduler (local durable scheduler)
· Agent Runtime
· Memory Engine (low‑level IKeyValueStore, IVectorStore, IGraphStore adapters)
· Kernel‑level health checks

Infrastructure Implementation

· Configuration provider (file, env, plugin schema merge)
· Security services (Casbin adapter, Permission Manager, audit logging)
· Telemetry and observability adapters (OpenTelemetry, Langfuse)
· Plugin loader with manifest validation and sandboxing
· All OSS adapters (LiteLLM, LlamaIndex, Qdrant, Playwright/Browser Use, Faster‑Whisper, Piper, OpenHands, Temporal)
· Circuit breaker and retry wrappers for all external calls

Knowledge Layer Implementation

· Knowledge Engine ingestion pipeline
· Embeddings generator and model adapters
· Vector store adapter integration
· RAG retrieval pipeline
· Context Builder assembly logic
· User Profile management

Cognitive Layer Implementation

· Model Router with policy chain and fallback
· Prompt Engine with template management
· Planner (LangGraph‑based DAG decomposition)
· Reasoning subsystem
· Workflow Engine
· Conversation Manager
· Reflection Agent
· Learning Agent

Capability Layer Implementation

· Browser automation (Playwright/Browser Use adapter)
· Desktop automation (Tauri native API adapter)
· Voice I/O (Faster‑Whisper/Piper adapters)
· Vision service (screen capture, OCR, image analysis adapter)
· Code Executor (OpenHands sandbox adapter, security isolation)
· Automation composer (macro engine on top of capabilities)

Interfaces

· REST/WebSocket API server (FastAPI)
· Desktop application shell (Tauri)
· Mobile application (Flutter)
· CLI tools for administration and debugging

Testing

· Unit tests for all kernel and domain components
· Integration tests for event flows, capability execution, and knowledge retrieval
· Architecture fitness functions integrated into CI
· End‑to‑end tests for key user journeys
· Performance and load tests for model routing and concurrent agents

Documentation

· Developer onboarding guide
· API reference
· Plugin development guide
· Deployment and operations guide
· User manual

Packaging and Deployment

· OS‑specific installers (.deb, .msi, .app, .apk)
· One‑click local setup experience
· Silent background upgrade mechanism
· Rollback support

CI/CD

· Build pipeline for all supported platforms
· Automated test execution and coverage reporting
· Architecture fitness function gate
· Automated packaging and artifact publishing

Monitoring and Observability

· Local health dashboard
· Alerting rules
· Telemetry collection and export (local‑first with optional cloud)

Plugin SDK

· Plugin project template
· Manifest schema and validation tool
· Local plugin development and testing harness

Developer Tools

· Plugin development kit (PDK)
· Event replay and debugging tools
· State inspector

Examples and Sample Plugins

· Sample browser automation plugin
· Sample voice command plugin
· Tutorial: building a custom capability

---

Milestone Roadmap

Milestones are listed in dependency order. No calendar dates are assigned.

Milestone Name Description Status
M1 Foundation Repository setup, CI/CD pipeline, kernel interfaces defined, architecture fitness functions wired Not started
M2 Core Kernel DI Container, Event Bus (with outbox), State Manager, Provider Registry fully implemented and tested Not started
M3 Kernel Services Task Scheduler, Agent Runtime, Capability Execution Engine, Memory Engine, kernel‑level health checks complete Not started
M4 Infrastructure Essentials Configuration provider, security (Casbin), telemetry sinks, core OSS adapters (LiteLLM, Qdrant) Not started
M5 Knowledge Layer Knowledge Engine, RAG, Embeddings, Context Builder, User Profile implemented and integrated with kernel Not started
M6 Cognitive Layer Model Router, Planner, Reasoning, Workflow, Conversation, Reflection, Learning implemented end‑to‑end Not started
M7 Capabilities All six capability implementations (browser, desktop, voice, vision, code, automation) with sandboxing and permission enforcement Not started
M8 Interfaces API server, desktop shell, mobile shell, CLI tools functional Not started
M9 Integration Testing Full system integration, event flow tests, end‑to‑end user journeys validated Not started
M10 Packaging & Deployment Installers for all platforms, automatic upgrade mechanism, rollback tested Not started
M11 Release Candidate Feature freeze, performance tuning, documentation complete, security audit Not started
M12 Version 1.0 Production release, publicly available Not started

Current Target Milestone
→ M1 Foundation

Overall Roadmap
M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9 → M10 → M11 → M12

---

Work Breakdown Structure (WBS)

M1 – Foundation

Epic: Engineering Infrastructure & Kernel Interfaces
Story Points: 34

Feature Task Depends On Deliverable
Repository bootstrap Create repository with package layout per Section 18 None Monorepo scaffold with package directories
 Configure branch protection rules Repository exists Protected main branch
 Set up issue labels and project boards Repository exists Label taxonomy, milestone board
CI pipeline skeleton Implement CI workflow (lint, fitness) Repository exists .github/workflows/ci.yml
 Add Python linting (Ruff/black) CI skeleton Lint check passes
 Add type checking (mypy) CI skeleton Type check passes
Architecture fitness functions Implement layer dependency check CI skeleton Fitness function fails if layer violation
 Implement OSS isolation check CI skeleton Fitness function fails if kernel imports third-party
 Implement event naming validation CI skeleton Fitness function fails if non-conforming event
 Implement circular import detection CI skeleton Fitness function fails if cycle
Kernel interface definition Write abstract base classes for DI Container, Event Bus, State Manager, Provider Registry, Capability Registry, Memory Engine, IModelAdapter, IVectorStore, etc. Repository bootstrap kernel/interfaces/ package complete
Developer tooling Create dev container / setup script Repository bootstrap One-command developer environment
 Publish contributor guide Repository bootstrap CONTRIBUTING.md and developer docs
 Set up pre-commit hooks (lint, format) Developer environment Pre-commit config

M2 – Core Kernel

Epic: Immutable Kernel Foundation
Story Points: 40

Feature Task Depends On Deliverable
DI Container Implement container with singleton/transient/scoped lifetimes Kernel interfaces kernel/di/ package
 Write unit tests (≥ 90% coverage) DI Container impl Tests pass
Event Bus Implement transactional outbox with SQLite store DI Container kernel/events/ package
 Deliver exactly-once semantics with idempotent consumer tracking Event Bus outbox Idempotency integration tests
 Ordered delivery per aggregate stream Event Bus core Ordered stream tests
State Manager Implement event store with append-only log Event Bus kernel/state/ package
 Snapshot creation and restoration Event store Snapshot tests
Provider Registry Implement plugin registration and resolution DI Container kernel/providers/ package
Capability Registry Map interfaces to capability IDs with metadata Provider Registry kernel/capabilities/registry.py
Integration tests End-to-end event flow from publisher to consumer via outbox All kernel components Integration test suite passes
CI extension Run kernel unit + integration tests on every push CI pipeline Test gate active

M3 – Kernel Services

Epic: Execution Fabric Completion
Story Points: 32

Feature Task Depends On Deliverable
Task Scheduler Implement local durable scheduler (state-backed) State Manager, DI Container kernel/scheduler/ package
 Support recurring, delayed, and retryable tasks Task Scheduler core Scheduler tests
Agent Runtime Implement agent process lifecycle management Task Scheduler kernel/runtime/ package
 Support concurrent agent instances Agent Runtime core Concurrency tests
Capability Execution Engine Resolve capability from registry, enforce permissions, enforce timeouts, invoke Capability Registry, State Manager kernel/capabilities/execution_engine.py
 Sandboxed execution context per capability Execution Engine Isolation tests
Memory Engine Implement IKeyValueStore adapter (SQLite) DI Container kernel/memory/keyvalue.py
 Implement IVectorStore adapter (in-memory for testing, Qdrant adapter in Infra) DI Container kernel/memory/vector.py
 Implement IGraphStore adapter (in-memory) DI Container kernel/memory/graph.py
Kernel health checks IKernelHealth implementation All kernel services Health endpoint returns component status

M4 – Infrastructure Essentials

Epic: Cross-Cutting Services & OSS Adapters
Story Points: 48

Feature Task Depends On Deliverable
Configuration provider Hierarchical merge, schema validation DI Container infrastructure/config/ package
 Plugin config namespace support Configuration provider Plugin config test
Security – Casbin adapter Implement IAuthorizationService with Casbin DI Container infrastructure/security/authz.py
 ABAC policies for capability access Authorization service Policies file + tests
Permission Manager Consent management, audit logging Security, State Manager infrastructure/security/permissions.py
Telemetry & Observability ITelemetrySink adapter (OpenTelemetry) DI Container infrastructure/telemetry/ package
 Langfuse adapter for LLM traces ITelemetrySink infrastructure/observability/langfuse_adapter.py
Plugin loader Manifest validation, sandboxed assembly loading Provider Registry infrastructure/plugins/loader.py
OSS adapters LiteLLM adapter implementing IModelAdapter Kernel interfaces infrastructure/adapters/litellm/
 LlamaIndex adapter implementing IIndexingPipeline Kernel interfaces infrastructure/adapters/llamaindex/
 Qdrant adapter implementing IVectorStore Kernel interfaces infrastructure/adapters/qdrant/
Circuit breaker Implement circuit breaker decorator for all adapter calls All adapters infrastructure/adapters/resilience.py

M5 – Knowledge Layer

Epic: Semantic Memory & Retrieval
Story Points: 36

Feature Task Depends On Deliverable
Knowledge Engine Ingestion pipeline (chunking, indexing) Infrastructure adapters knowledge/engine/ package
Embeddings IEmbeddingModel adapter, local/remote selection LiteLLM adapter knowledge/embeddings/ package
RAG Query rewriting, fusion, retrieval, reranking Knowledge Engine, Qdrant adapter knowledge/rag/ pipeline
Context Builder Source collection, filtering, ranking, formatting RAG, User Profile knowledge/context/builder.py
User Profile Structured profile store (graph) Memory Engine graph store knowledge/profile/ package
Integration tests End-to-end retrieval for a sample query All Knowledge components Tests pass

M6 – Cognitive Layer

Epic: Reasoning & Planning
Story Points: 48

Feature Task Depends On Deliverable
Model Router Policy chain evaluation, fallback, adapter selection IModelAdapter, Telemetry cognitive/router/
Prompt Engine Template management with context injection Context Builder cognitive/prompt_engine/
Planner LangGraph-based DAG decomposition Model Router, Context Builder cognitive/planner/
Reasoning Chain-of-thought execution, verification Model Router cognitive/reasoning/
Workflow Engine Plan step execution with branching/parallelism Task Scheduler cognitive/workflow/
Conversation Manager Dialogue state, threading, turn management State Manager cognitive/conversation/
Reflection Agent Outcome evaluation, improvement signals Workflow Engine cognitive/reflection/
Learning Agent User model update, procedural memory update Reflection Agent, Knowledge Engine cognitive/learning/
Integration tests Full cognitive loop from intent to response All Cognitive components Tests pass

M7 – Capabilities

Epic: Tools & Actions
Story Points: 42

Feature Task Depends On Deliverable
Browser automation Playwright/Browser Use adapter Capability Execution Engine capabilities/browser/
Desktop automation Tauri native API adapter Capability Execution Engine capabilities/desktop/
Voice I/O Faster-Whisper STT adapter, Piper TTS adapter Capability Execution Engine capabilities/voice/
Vision Screen capture/OCR adapter Capability Execution Engine capabilities/vision/
Code Executor OpenHands sandbox adapter, security isolation Capability Execution Engine capabilities/code/
Automation composer Macro engine on top of capabilities Workflow Engine capabilities/automation/
Capability sandboxing Process isolation, resource limits per capability Capability Execution Engine Sandbox tests for each capability

M8 – Interfaces

Epic: User & System Entry Points
Story Points: 38

Feature Task Depends On Deliverable
REST/WebSocket API FastAPI server exposing conversation, capability endpoints Cognitive, Capabilities interfaces/api/
Desktop shell Tauri shell loading core library API server interfaces/desktop/
Mobile shell Flutter app communicating with local API API server interfaces/mobile/
CLI tools Admin commands (health, plugin management) API server interfaces/cli/
Interface integration tests API tests for conversation flow All interfaces Tests pass

M9 – Integration & System Testing

Epic: Full System Validation
Story Points: 34

Feature Task Depends On Deliverable
Event flow tests Verify exact-once, ordering, idempotency end-to-end Entire system Test suite
End-to-end user journeys 10 representative tasks, automated System operational E2E tests pass
Architecture fitness function gates All 9 fitness functions active in CI CI pipeline Gate prevents non-compliant merges
Performance baseline Capture and store baseline latency/throughput metrics System operational Baseline in CI artifacts
Chaos testing Simulate capability failures, recovery System operational Tests verify resilience patterns

M10 – Packaging & Deployment

Epic: Distribution
Story Points: 28

Feature Task Depends On Deliverable
OS installers .deb, .msi, .app, .apk build pipelines Full system Installer artifacts
Silent upgrade Background update mechanism with rollback State Manager snapshot Upgrade integration tests
CI/CD packaging Automated build and signing OS installers Signed release artifacts
Installation documentation User-facing installation guide Installers Docs published

M11 – Release Candidate

Epic: Final Quality Gate
Story Points: 24

Feature Task Depends On Deliverable
Feature freeze Lock all non-critical changes All M1-M10 deliverables Branch freeze
Performance tuning Profiling-driven optimization Performance baseline Improved metrics
Security audit Third-party penetration test / internal review System Audit report, remediation
Documentation completion All docs reviewed and polished All features Documentation site live
User acceptance testing Beta test group Packaged system UAT report

M12 – Version 1.0

Epic: General Availability
Story Points: 12

Feature Task Depends On Deliverable
Final release Build, sign, publish to distribution channels M11 approval Public release
Release announcement Blog post, changelog, community outreach Release artifacts Announcement
Retrospective Project post-mortem, process improvements All milestones Retrospective document

---

Detailed Implementation Sequencing

Critical Path

```
M1 (Foundation) → M2 (Core Kernel) → M3 (Kernel Services) → M4 (Infrastructure Essentials) → M5 (Knowledge Layer) → M6 (Cognitive Layer) → M7 (Capabilities) → M8 (Interfaces) → M9 (Integration Testing) → M10 (Packaging) → M11 (RC) → M12 (GA)
```

Parallel Work Streams (post-M3)

· Knowledge Layer (M5) and Cognitive Layer (M6) can proceed in parallel once core kernel interfaces are stable (M2/M3), as both depend on kernel interfaces but not on each other beyond well-defined contracts.
· Capability implementations (M7) can begin as soon as the Capability Execution Engine (M3) is stable, independent of Knowledge/Cognitive layers.
· Interfaces (M8) can start alongside later capability work, using mock capability adapters until real ones are available.
· Documentation runs as a parallel stream throughout all milestones, with each feature documenting itself.
· Testing is embedded within each milestone, with integration tests written alongside components.

Dependency Diagram (high-level)

```
        M1
         ↓
        M2
         ↓
        M3
       / | \
     M4  M5  M6
       \ | /
        M7
         ↓
        M8
         ↓
        M9
         ↓
       M10
         ↓
       M11
         ↓
       M12
```

Detailed intra-milestone dependencies are encoded in the WBS tables above.

---

Development Process

Sprint Cadence

Development is organized into two-week sprints. Each sprint begins with a planning meeting (Monday) and ends with a review/retrospective (Friday of the second week). Sprints are aligned with milestones; a milestone may span multiple sprints.

Planning

· Backlog Refinement: Every Wednesday, the team grooms the backlog for upcoming sprints, estimating tasks and clarifying acceptance criteria.
· Sprint Planning: The team selects work items from the prioritized backlog, commits to a sprint goal, and decomposes into tasks.
· Daily Standup: Fifteen minutes, asynchronous (Slack/Teams bot) or synchronous, covering progress, blockers, and plans.

Review

At the end of each sprint, a demo is held for stakeholders. Completed features are shown against their acceptance criteria. Undone work is returned to the backlog.

Retrospective

Following the review, the team reflects on process, tools, and interactions to identify actionable improvements. Outcomes are tracked as process issues.

RFC (Request for Comments) Workflow

Any change that modifies kernel interfaces, event schemas, or architectural patterns requires an RFC. The process:

1. Fork the rfcs repository or branch in the main repo.
2. Create an RFC document using the template (rfcs/template.md), placed in rfcs/active/.
3. Submit a pull request to main with the label rfc.
4. The architecture team and relevant code owners review; a minimum of two approvals is required.
5. The RFC may be discussed at the weekly architecture meeting.
6. Once approved, the RFC is merged into rfcs/accepted/ and its implementation tasks are linked to the appropriate milestone.
7. Implemented RFCs are moved to rfcs/implemented/.

Engineering Review Workflow

All code changes follow a standard pull request process:

· Create a feature branch from main.
· Implement changes with tests.
· Ensure all pre-commit checks pass (lint, type, format).
· Open a PR with a description following the PR template, linking to relevant issues/RFCs.
· Required reviews: at least one from the package owner (CODEOWNERS) and one from the security team for sensitive areas.
· CI must be green (fitness functions, unit tests, integration tests, coverage).
· Branch must be up to date with main before merge.
· Merge strategy: squash merge to keep a linear history, except for release branches.

---

Definition of Done

Every work item (feature, bug fix, enhancement) must satisfy all of the following criteria before being marked as complete:

· Code implements the specified functionality and is peer-reviewed.
· Unit tests exist and pass; coverage on new code meets or exceeds the target (≥80% for domain logic, ≥90% for kernel).
· Integration tests (if applicable) pass and cover the happy path and key failure modes.
· All architecture fitness functions pass.
· Linting and type checking pass without errors.
· Relevant documentation is updated (API docs, developer guides, user manual as needed).
· Performance impacts are measured and documented if the change affects hot paths.
· Security review is conducted if the change involves permission checks, data handling, or external interfaces.
· Acceptance criteria (defined in the issue) are satisfied and demonstrated in the sprint review.
· The change is merged via an approved pull request.
· No new technical debt items are introduced without being recorded in the debt register.
· The feature is verified on at least one target platform (Linux, macOS, or Windows) depending on the component.

---

Acceptance Criteria Standard

Every issue must include acceptance criteria using the following template:

```
### Functional
- [Description of expected behavior, inputs, outputs, state transitions]

### Performance
- [Latency thresholds, throughput requirements, memory/CPU limits]

### Security
- [Permission constraints, data sanitization, audit log entries]

### Testing
- [Unit tests covering edge cases, integration test scenarios, manual test steps if needed]

### Documentation
- [New or updated documents, sections to modify]

### Architecture Compliance
- [Verify layer separation, interface usage, event naming, no framework leakage]
```

Example:

```
### Functional
- The user can trigger a browser search via the Conversation API.
- The browser capability opens a headless browser, navigates to a search engine, returns extracted text.

### Performance
- Search intent to first result latency ≤ 2 seconds.

### Security
- Browser capability requires explicit user consent; all network access is logged.

### Testing
- Unit tests for search parser; integration test with mocked Playwright adapter; end-to-end test with a real local server.

### Documentation
- Update capability API documentation and user manual section on web search.

### Architecture Compliance
- Must use IBrowserDriver interface; no Playwright imports in capability layer.
```

---

Milestone Exit Criteria

Each milestone is considered complete only when all exit criteria are met.

M1 – Foundation

· Repository is publicly accessible with the correct monorepo layout.
· All kernel interface abstract base classes are committed and reviewed.
· CI pipeline runs linting, type checking, and all nine architecture fitness functions on every push.
· Developer environment can be set up with a single command.
· CONTRIBUTING.md and ARCHITECTURE.md are published.

M2 – Core Kernel

· DI Container, Event Bus (with outbox), State Manager, Provider Registry, and Capability Registry are implemented and tested.
· Exactly-once event delivery is verified by integration tests.
· Unit test coverage for kernel packages ≥ 90%.
· No kernel module imports any third-party library (enforced by fitness function).

M3 – Kernel Services

· Task Scheduler, Agent Runtime, Capability Execution Engine, and Memory Engine are implemented.
· Capability sandboxing (process isolation) works on at least one platform.
· Kernel health checks report status of all core services.
· Integration tests demonstrate event sourcing with snapshotting.

M4 – Infrastructure Essentials

· Configuration system merges defaults, user config, and plugin config with schema validation.
· Authorization adapter (Casbin) enforces ABAC policies; denied actions produce audit logs.
· Telemetry and observability adapters export traces/metrics to configured backends.
· Plugin loader successfully registers a test plugin from a directory.

M5 – Knowledge Layer

· Knowledge Engine can ingest a document, chunk, embed, and index it.
· RAG pipeline retrieves relevant chunks for a query, verified by a golden test set.
· Context Builder assembles a context payload within a token budget.
· User Profile can store and retrieve preferences.

M6 – Cognitive Layer

· Model Router selects models based on privacy tier, latency, and capability.
· Planner produces a valid DAG for at least three representative intents.
· Workflow Engine executes a plan with capability invocations.
· Reflection Agent generates an improvement signal after task completion.
· End-to-end cognitive loop processes a natural language request without human intervention.

M7 – Capabilities

· All six capabilities (browser, desktop, voice, vision, code, automation) are functional.
· Each capability respects its declared permissions and resource limits.
· Capability sandboxing prevents file system and network access beyond declared permissions.
· Circuit breaker triggers after repeated failures and recovers gracefully.

M8 – Interfaces

· API server passes OpenAPI spec validation and all endpoint tests.
· Desktop shell launches and connects to API server via local IPC.
· Mobile shell connects to API server on localhost.
· CLI admin commands function for health check and plugin management.

M9 – Integration Testing

· All 10 end-to-end user journeys pass consistently.
· Architecture fitness functions gate all merges.
· Performance baseline established and no regression >10% from previous milestone.
· Chaos tests demonstrate resilience against capability failures.

M10 – Packaging & Deployment

· Signed installers for Linux, macOS, Windows, and Android are generated by CI.
· Silent upgrade from previous version to current with rollback tested successfully.
· Installation documentation verified by a new user.

M11 – Release Candidate

· Feature freeze in effect; only critical bugs fixed.
· Performance metrics meet NFRs (e.g., intent-to-first-token <500ms for local models).
· Security audit completed and all critical/high findings resolved.
· Documentation reviewed and updated, including user manual and operations guide.
· UAT conducted with a beta user group; feedback addressed.

M12 – Version 1.0

· Final release build signed and published.
· Release notes and changelog published.
· Announcement blog post and community outreach executed.

---

Contributor Workflow

Branch Strategy

The project uses a trunk‑based development model. main is the single source of truth and is always releasable. Developers work on short‑lived feature branches (feature/<issue-id>-short-desc) or bugfix branches (fix/<issue-id>-short-desc). All branches are rebased on main before merge.

Release branches (release-1.0) are created from main during the release candidate phase (M11) and only cherry‑pick critical fixes.

Pull Request Lifecycle

1. Create a branch from an up‑to‑date main.
2. Implement changes, ensuring the Definition of Done checklist is followed.
3. Push the branch and open a pull request against main. Use the PR template to describe the change and link to relevant issues.
4. Automated checks: CI runs linting, type checking, fitness functions, unit tests, and integration tests. The PR cannot be merged if any check fails.
5. Review: At least one CODEOWNER must approve, and a second reviewer from the security or architecture team is required for changes to kernel interfaces, permissions, or event schemas.
6. Address feedback and ensure all review comments are resolved.
7. Rebase onto latest main and squash‑merge when all checks are green. The merge commit message must follow the conventional commits format.

Review Requirements

· Every PR must have at least one approving review from a CODEOWNER of the affected packages.
· No direct pushes to main are allowed.
· Reviewers should verify adherence to architecture principles, design patterns, and quality standards, not just code correctness.

Commit Message Format

All commits must follow Conventional Commits:

```
<type>(<scope>): <description>
```

Types: feat, fix, docs, test, refactor, chore, perf, ci, build.
Scope should be the package (e.g., kernel, cognitive, capabilities/browser).
Example: feat(kernel): implement transactional outbox for Event Bus.

CODEOWNERS

A CODEOWNERS file at the repository root assigns ownership of each package:

```
/kernel/ @chhaya-ai/core-kernel-team
/infrastructure/ @chhaya-ai/infra-team
/cognitive/ @chhaya-ai/cognitive-team
/knowledge/ @chhaya-ai/knowledge-team
/capabilities/ @chhaya-ai/capabilities-team
/interfaces/ @chhaya-ai/ui-team
/tests/ @chhaya-ai/qa-team
```

The architecture team (@chhaya-ai/architecture) is automatically requested for changes to kernel interfaces and event schemas.

CLA/DCO Policy

All contributors must sign a Developer Certificate of Origin (DCO) by adding a Signed-off-by line to every commit. A CLA is not required; the project uses DCO to ensure open‑source license compliance. The CI checks for DCO sign‑off on every commit.

---

Architecture Decision Record (ADR)

Policy

Any architectural decision that affects system structure, non‑functional requirements, or external interfaces must be captured as an ADR. This includes decisions made during the initial design (retrospectively recorded) and any future changes.

Directory Structure

ADRs live in the repository under docs/adr/. The directory contains:

· README.md – index of all ADRs with status
· NNNN-title-with-dashes.md – individual decision records

Naming Convention

Files are numbered sequentially starting at 0001. The title is a short, descriptive phrase in lower‑case with hyphens. Example: 0001-use-event-bus-for-state-changes.md.

Template

```markdown
# ADR-NNNN: Title

**Date:** YYYY-MM-DD
**Status:** [Proposed | Accepted | Deprecated | Superseded]

## Context
[What is the issue motivating this decision?]

## Decision
[What is the change that we are proposing?]

## Consequences
[What becomes easier or harder because of this change?]

## Alternatives Considered
[What other options were evaluated? Why not chosen?]
```

Approval Workflow

1. An ADR is proposed as a pull request to docs/adr/ with status Proposed.
2. The architecture team discusses it in the next architecture meeting.
3. Once consensus is reached, the status is changed to Accepted and the PR is merged.
4. Superseded ADRs are marked Deprecated and linked to the new ADR.

---

API Governance

The kernel interfaces (kernel/interfaces/) constitute the public API of Chhaya AI OS. All other packages and plugins depend on these interfaces. API governance ensures stability and prevents breaking changes.

Versioning

· Interfaces follow semantic versioning at the package level. The kernel package version is incremented according to semver rules based on interface changes.
· Each interface class carries a @version decorator or docstring indicating its major version.

Compatibility

· Backward compatibility is required within a major version. New methods may be added with default implementations.
· Breaking changes require a major version increment and must be accompanied by an ADR and a migration guide.
· The previous major version is supported (with deprecated warnings) for at least one full release cycle.

Deprecation

· Mark deprecated methods with a @deprecated decorator that emits warnings.
· Document deprecated APIs in the release notes.
· Remove deprecated APIs only in the next major version after the deprecation announcement.

Approval Process

· Any change to a kernel interface (add, modify, or remove a method) requires an approved RFC or ADR and review by the architecture team.
· The CI must verify that all adapters implement the updated interface (enforced by fitness function).

---

Dependency Management Policy

Third‑Party Pinning

· All direct dependencies are pinned to exact versions in requirements.txt or pyproject.toml (using ==). Transitive dependencies are pinned via lock files (requirements-lock.txt or poetry.lock).
· Dependabot or Renovate is configured to automatically submit pull requests for version updates on a weekly basis.

License Policy

· Only packages with licenses compatible with the project’s license (Apache 2.0 or MIT) are permitted. A license check is integrated into CI.
· Any new dependency must be approved by the core team before merge.

SBOM Generation

· A Software Bill of Materials (SBOM) in SPDX format is generated during the release build using a tool like syft. The SBOM is published alongside release artifacts.

Vulnerability Scanning

· CI runs pip-audit or Safety on every pull request to detect known vulnerabilities. High‑severity findings block the merge.
· Dependencies are also scanned nightly; critical vulnerabilities trigger an immediate fix PR.

Upgrade Cadence

· Non‑breaking updates (patch/minor) are merged automatically if all tests pass.
· Major updates require manual review and are scheduled at the beginning of a sprint.

---

Complete Testing Strategy

Test Pyramid

The project enforces the following test distribution:

· Unit tests: Cover all domain logic, kernel services, and utility functions. Target ≥ 80% line coverage overall; kernel ≥ 90%.
· Integration tests: Verify interactions between kernel components, adapters, and layers. Must cover happy paths and failure modes.
· End‑to‑end (E2E) tests: Validate complete user journeys from UI/API to capability execution and response. The initial set includes 10 representative tasks.
· Contract tests: Ensure that all adapters correctly implement kernel interfaces. Run on each adapter in isolation.
· Performance tests: Measure latency, throughput, and resource usage under load.
· Security tests: Include fuzz testing of parsers, static analysis, and dependency scanning.

Coverage Goals

· Kernel: ≥90% line coverage.
· Cognitive/Knowledge: ≥85%.
· Capability adapters: ≥80%.
· Infrastructure: ≥80%.
· Fitness function verifies coverage thresholds in CI; coverage below target fails the build.

Mutation Testing

· Mutation testing is applied to critical path code (Event Bus, State Manager, Capability Execution Engine) to ensure test effectiveness. A mutation score of ≥75% is required. Run nightly, not per PR.

Contract Testing

· Each adapter’s public interface is validated against the kernel interface it implements. Contract tests are written using a test harness that runs the same test suite for all implementations.

Regression Testing

· A full regression suite (all unit, integration, and E2E tests) runs on every push to main and on PRs that modify kernel or shared infrastructure.

Performance Testing

· Benchmarks are defined for:
  · Event Bus publish‑to‑delivery latency (target < 5ms p99).
  · Model router selection time (< 10ms).
  · Intent‑to‑first‑token for local models (< 500ms).
  · Memory usage during idle and under load.
· Benchmarks run as part of CI for relevant PRs; a regression threshold prevents performance degradation.
· A dedicated performance lab environment collects historical trend data.

Load Testing

· The system is load‑tested with multiple concurrent agents (up to 100 simulated) to ensure no deadlocks and resource exhaustion.

Chaos Testing

· Random capability failures, network drops (for adapters), and process restarts are injected during integration and E2E testing. The system must recover as per error recovery architecture.

Security Testing

· SAST (static application security testing) with Bandit and Semgrep runs on every PR.
· Fuzz testing targets input parsers (API, event payloads) using atheris or python-afl.
· Dependency vulnerability scanning is part of CI.
· A penetration test is conducted before the RC phase.

Golden Tests

· A set of known inputs and expected outputs (golden files) are used for RAG, reasoning, and planning to detect regressions in model outputs (qualitative checks).

Architecture Fitness Functions

· Nine automated checks (defined in Master Architecture 36.7) are run on every build and block the PR if violated.

CI Test Matrix

The CI runs the test suite on:

· Python 3.11, 3.12
· Linux (Ubuntu latest), macOS, and Windows
· With and without optional heavy dependencies (GPU-required tests are skipped on CPU-only runners)

---

CI/CD Architecture

Pipeline Stages (sequential)

1. Lint & Format: Ruff, black, isort — must pass with zero errors.
2. Type Checking: mypy in strict mode for the entire codebase.
3. Architecture Fitness Functions: Run the 9 fitness tests; failure blocks progress.
4. Unit Tests: Run on all platform/Python combinations in parallel.
5. Integration Tests: Require a local SQLite DB and a test vector store (in‑memory); run sequentially to avoid port conflicts.
6. Coverage Report: Generate coverage XML; fail if below threshold.
7. Build Package: Create Python wheel and source tarball.
8. Security Scan: Run Bandit, pip‑audit, and license checker.
9. Sign Artifacts: Sign the wheel and tarball with GPG key.
10. Publish Pre‑release: For non‑main branches, publish to internal PyPI or GitHub Releases (pre‑release). On tag push, publish as latest release.

Rollback

If a release artifact causes critical issues, a rollback consists of re‑tagging the previous commit and re‑running the release pipeline. The deployment mechanism supports downgrading via the automatic upgrade system.

---

Release Management

Semantic Versioning

Software releases follow SemVer 2.0: MAJOR.MINOR.PATCH.

· MAJOR: Breaking changes to kernel interfaces, event schemas, or configuration format.
· MINOR: New backward‑compatible functionality, new capabilities, new plugins.
· PATCH: Bug fixes, performance improvements.

Release Branches

· A release-MAJOR.MINOR branch is created from main during the RC phase (M11). Only cherry‑picks of critical fixes are allowed after branch creation.
· The branch is deleted after the final release and back‑porting to main.

LTS Policy

· A designated “long‑term support” version is planned annually. LTS releases receive critical bug fixes and security patches for 2 years. The first LTS release will be determined after v1.0 based on stability.

Hotfixes

· For critical production issues, a hotfix branch is forked from the release branch, fixed, merged, and a new patch release is issued. The fix is also cherry‑picked to main.

RC Process

· When all exit criteria for M10 are met, a Release Candidate (RC) is built. The community is invited to test and report blockers. RC duration is at least 2 weeks.

Release Checklist

· All M11 exit criteria satisfied.
· Documentation is frozen.
· Release notes written with a detailed changelog.
· Artifacts are signed and published.
· Announcement post scheduled.

Artifact Signing

All release artifacts are signed with the project’s GPG key. Signatures and checksums are published alongside the artifacts.

---

Operational Readiness

Runbooks

A runbook directory (docs/runbooks/) contains procedures for:

· Starting and stopping the system on each platform.
· Backing up and restoring the state store.
· Upgrading to a new version and rolling back.
· Troubleshooting common issues (capability failure, memory exhaustion, configuration errors).

Backup and Restore Testing

· Automated tests verify that a snapshot taken by the State Manager can be restored successfully.
· The upgrade integration test includes a rollback scenario.

Health Checks

· The system exposes a /health endpoint (API) and a system tray indicator (desktop) reporting status of all kernel and infrastructure services.
· A health aggregator computes an overall status: HEALTHY, DEGRADED, or UNHEALTHY, based on component statuses.

Monitoring & Alerting

· Metrics are exported via OpenTelemetry (when configured) and displayed on a local dashboard.
· Key metrics: event bus lag, capability execution latency, model router selection time, memory usage, error rate.
· Alert rules are defined for critical conditions (e.g., multiple capability failures within a minute). Alerts generate system events.

Logging

· All components emit structured JSON logs to stderr. Log levels: DEBUG, INFO, WARNING, ERROR.
· Sensitive data is masked before logging.

Tracing

· Each request is assigned a correlation ID propagated through events and API calls. Traces are exported to Langfuse/OTLP backend for observability.

Incident Response

· When a critical event (SYSTEM.ERROR.CRITICAL) occurs, the system enters ERROR_RECOVERY state. The automated recovery process attempts to snapshot state, restart failed components, and notify the user. If unrecoverable, a manual runbook is referenced.

---

Documentation Strategy

Docs-as-Code

All documentation lives in the repository under docs/ and is written in Markdown. Documentation is versioned alongside the source code. A documentation build (using MkDocs or Sphinx) is part of the CI pipeline, and published documentation is hosted on a dedicated site (e.g., docs.chhaya.dev).

Review Process

· Documentation pull requests are reviewed by at least one subject matter expert and a technical writer (if available).
· Every feature pull request must include documentation changes (or a justification for why none are needed).

Diátaxis Framework

Documentation is structured according to the Diátaxis framework:

· Tutorials: Step‑by‑step lessons (e.g., “Build your first plugin”).
· How‑to Guides: Recipes for specific tasks (e.g., “How to switch model backends”).
· Explanation: Background and context (e.g., “Memory hierarchy in Chhaya”).
· Reference: API documentation, configuration schema, CLI commands.

API Documentation

· All public interfaces and classes have comprehensive docstrings. Sphinx auto‑generates API reference pages.
· The CI fails if a public symbol lacks a docstring.

Developer Documentation

· CONTRIBUTING.md, architecture overview, development environment setup, and coding standards.

User Documentation

· Installation guide, user manual covering all capabilities, and a quick‑start tutorial.

Operations Documentation

· Deployment guide for each platform, monitoring setup, runbooks, and security hardening.

---

Community Governance

Roles

· Maintainers: Core contributors with write access. Responsible for reviewing and merging PRs, guiding the technical direction, and ensuring quality. Maintainers are nominated by existing maintainers based on sustained contributions.
· Committers: Trusted contributors with write access to specific repositories/packages. They can merge approved PRs within their scope.
· Reviewers: Community members recognized for expertise in an area. They are automatically requested for PR reviews.
· Community Ladder: Clear path from first‑time contributor → reviewer → committer → maintainer, based on contribution history, review quality, and community trust.

Code of Conduct

The project adopts the Contributor Covenant 2.1. Enforcement guidelines and a reporting mechanism (email to conduct@chhaya.dev) are documented in CODE_OF_CONDUCT.md. All participants are required to abide by it.

Issue Triage

· New issues are automatically labeled triage.
· A maintainer triages weekly, assigning labels (bug, enhancement, question), priority (p0–p3), and milestone.
· Stale issues are closed after 90 days of inactivity with a warning.

Label Conventions

· area/kernel, area/cognitive, etc. – identifies the subsystem.
· type/bug, type/feature, type/docs, type/debt – classifies the work.
· priority/p0 (blocker), p1 (critical), p2 (normal), p3 (low).
· good first issue – accessible for new contributors.

Meeting Cadence

· Weekly Architecture Meeting: Discuss ADRs, RFCs, and architectural concerns.
· Bi‑weekly Community Call: Open to all contributors, demo recent progress, and answer questions.
· Monthly Steering Committee: Strategic decisions, roadmaps, budget.

---

Technical Debt Management

Debt Register

A technical debt register is maintained as a GitHub issue label type/debt. Each debt item includes:

· Description and impact
· Component affected
· Estimated effort to resolve
· Proposed milestone for resolution
· Owner

Prioritization

Debt items are prioritized together with new features during sprint planning. High‑impact debt (e.g., potential to cause production outages) is P1. The team allocates at least 10% of sprint capacity to debt reduction.

Debt Budget

No component may accumulate more than 3 open debt items at a time. If exceeded, the next sprint must prioritize debt reduction.

Ownership

The component owner (from CODEOWNERS) is responsible for keeping the debt list manageable and for scheduling reduction.

Review Cadence

The debt register is reviewed at the retrospective and during the monthly steering meeting.

---

Performance Engineering Plan

Measurable Targets

Metric Target
Intent‑to‑first‑token (local model) ≤ 500 ms p95
Event bus publish‑to‑consumer latency ≤ 5 ms p99
Model router selection latency ≤ 10 ms p99
Capability execution overhead (excluding capability work) ≤ 50 ms
Idle memory usage (all services) ≤ 500 MB
Load memory under 10 concurrent agents ≤ 2 GB
Agent context switch time ≤ 20 ms
Throughput (simple conversational turns) ≥ 10 req/s on consumer hardware

Profiling

· Weekly profiling using py-spy or cProfile on representative workloads. Results are stored and trended.
· Hot paths (Event Bus dispatch, model routing) are benchmarked in CI to detect regressions.

Regression Detection

· Performance tests run on each PR that touches kernel or cognitive code. A regression is defined as a degradation >10% from the stored baseline. Such PRs are blocked until the performance is restored or a conscious trade‑off is accepted (with an ADR).

---

Engineering KPIs

Key performance indicators are tracked using GitHub’s built‑in analytics and a project dashboard (e.g., Grafana with GitHub data source). The following KPIs are reviewed monthly:

KPI Target
Velocity (story points/sprint) Consistent ±20%
Lead Time (time from issue open to merge) < 5 days for P1
Deployment Frequency At least once per sprint (for pre‑release)
Code Coverage (overall) ≥ 80%, kernel ≥ 90%
Bug Escape Rate (bugs found after release per sprint) < 2
Mean Time to Recovery (MTTR) < 1 hour for critical issues
Issue Aging (open issue > 30 days) < 10% of open issues
PR Aging (open PR > 3 days) 0 (stale PRs closed)
Architecture Compliance (fitness function pass rate) 100% on main
Fitness Function Pass Rate 100%

---

Risk Register

Each risk is assigned an owner and actively managed through the risk register.

Risk ID Risk Probability Impact Owner Mitigation Contingency Trigger Review Frequency
R1 Local model performance below latency target Medium (40%) High Cognitive Team Quantization, hardware detection, fallback routing Enable cloud fallback for real‑time tasks (with user opt‑in) p95 latency >500ms for 2 consecutive weeks Monthly
R2 Exact‑once implementation complexity causes delay Medium (30%) Medium Kernel Team Prototype early, design review, allow at‑least‑once with idempotency as interim Ship v1 with at‑least‑once if exact‑once is not ready by M9 M3 exit not met by schedule Bi‑weekly
R3 Sandboxing insufficient on certain platforms High (50%) High Security Team Start with process isolation; use platform‑specific sandboxing where available Document known limitations; require user confirmation for risky capabilities Penetration test finds bypass Monthly
R4 Plugin compatibility breaks with ecosystem updates Medium (30%) Medium Plugin Working Group Automated compatibility tests, pinned plugin versions Rapid release of compatibility patches; notify plugin authors A plugin fails to load after a dependency upgrade Weekly
R5 Scope creep delays v1.0 High (40%) High PM Strict milestone exit criteria, weekly scope review Cut non‑critical features from v1.0 scope Velocity drops 30% below plan Weekly
R6 Key contributor departure Low (20%) High Project Lead Documentation, pair programming, bus factor >1 for all components Engage community to backfill; reduce scope temporarily Single point of failure for >2 sprints Monthly
R7 Third‑party library breaking change Medium (30%) Medium Infra Team Pin versions, automated upgrade tests Temporarily pin to previous version; fork if necessary CI fails after a dependency update On each Dependabot PR
R8 Model unavailability on specific hardware Medium (40%) Low Cognitive Team Hardware detection, provide alternative models Fallback to simpler models; guide user to install missing components User reports missing model support During release testing
R9 Memory exhaustion under load Medium (30%) Medium Kernel/Infra Lazy loading, dynamic unloading, resource limits Throttle concurrent agents; notify user to reduce load Memory usage exceeds threshold alert Monthly performance review
R10 Asynchronous testing gaps lead to production failures Medium (30%) High QA Team Deterministic simulation harness, chaos testing Halt release until critical test gaps filled A concurrency bug escapes to production Post‑mortem after each escape

---

Repository Health

Area Status Comment
Architecture 🟢 Frozen Complete and approved
Documentation 🟡 Partial Architecture complete; implementation documents pending
Implementation ⚪ Not Started No production code
Testing ⚪ Not Started Fitness functions defined only
CI/CD ⚪ Not Started Pipeline not configured
Release ⚪ Pre-Alpha No builds available

The repository currently serves as a design artefact. Its transformation into an active engineering project begins with the immediate next steps outlined below.

---

Repository Metrics

Asset Count
Architecture Documents 1
Governance Documents 1
Implementation Documents 0
Developer Guides 0
Implemented Packages 0
Implemented Subsystems 0
Installed Plugins 0
Unit Tests 0
Integration Tests 0
Architecture Fitness Functions 9 (Defined, Not Implemented)

---

Success Criteria

The Chhaya AI Operating System v1.0 will be considered complete when:

1. All subsystems defined in the Master Architecture are implemented and pass their architecture fitness functions.
2. The system operates fully offline for all core capabilities (browser, desktop, voice, vision, code execution, reasoning, conversation).
3. Users can install the system on Windows, macOS, Linux, or Android and complete a pre‑defined set of 10 representative tasks (e.g., “book a flight”, “summarise my emails”, “write and run a Python script”) without manual intervention beyond initial consent.
4. The Plugin SDK enables a developer to create, test, and install a new capability without modifying core system code.
5. All automated architecture fitness functions, integration tests, and end‑to‑end tests pass.
6. Documentation exists for developers, administrators, and end‑users.
7. A security audit confirms that no user data leaves the device without explicit permission, and all capabilities are properly sandboxed.

---

Immediate Next Steps

These tasks are the highest‑priority engineering actions to be completed before any feature implementation begins.

1. Create the official project repository with the frozen master architecture document as the top‑level reference.
2. Establish the Python project structure mirroring the package organisation defined in Section 18 of the architecture.
3. Define kernel interfaces as Python abstract base classes (kernel/interfaces/) — these are the contracts that all implementation will follow.
4. Implement the first architecture fitness function (layer dependency check) and integrate it into a CI pipeline, even before any code exists, to verify the pipeline gate works.
5. Set up static analysis and linting rules that enforce the import constraints and coding standards.
6. Begin kernel DI Container implementation as the first executable component, since all other components depend on it.
7. Create a contributor guide that explains the architecture, the development workflow, and how to adhere to the design principles.
8. Set up an issue tracker with labels aligned to the architectural layers and milestone roadmap.
9. Draft a lightweight Request for Comments (RFC) template for any future design changes that require architecture governance.

---

Appendix — Project Phase Glossary

· Pre‑Architecture: Initial concept exploration and prototyping. Complete.
· Architecture Definition: Detailed design of all layers, subsystems, and interfaces. Complete.
· Architecture Freeze: Formal lock of the master architecture; no further changes without governance. Current phase.
· Implementation Planning: Decomposition of architecture into work packages, prioritisation, and engineering setup. Entering now.
· Foundation Development: Implementation of kernel interfaces and core kernel services (M1‑M3).
· Core Implementation: Implementation of remaining layers (Infrastructure, Knowledge, Cognitive, Capabilities, Interfaces) (M4‑M8).
· Integration & Testing: Full system integration, end‑to‑end testing, and architecture compliance validation (M9).
· Packaging & Deployment: Build system, installers, and automated upgrades (M10).
· Release Candidate: Feature freeze, final testing, and documentation completion (M11).
· General Availability: Public release of v1.0 (M12).
· Maintenance & Evolution: Post‑v1.0 feature additions, plugin ecosystem growth, and architectural evolution under governance.

Versioning Policy

This document follows Semantic Versioning.

• Major versions indicate significant structural revisions.

• Minor versions record milestone completions and engineering progress.

• Patch versions record editorial corrections that do not alter engineering status.

Document Control

Document Owner: Core Architecture Team
Review Trigger: Completion of every Milestone
Approval Required: Architecture Governance Team
Status: ACTIVE
Version: 1.1
Last Updated: 2026-07-13

---

"""
Frozen Kernel Interfaces.

These are the immutable architectural foundations of the Chhaya AI OS.
Any change to these interfaces requires an Architecture Decision Record (ADR).
"""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol


class Event(Protocol):
    """Protocol describing the base event structure."""

    type: str
    version: str
    payload: dict[str, Any]
    id: str
    timestamp: str
    source: str
    session_id: str | None

    @property
    def is_cancelled(self) -> bool:
        ...

    def cancel(self) -> None:
        ...


EventHandler = Callable[[Event], Any | Awaitable[Any]]


class IEventBus(Protocol):
    """Frozen Event Bus interface."""

    async def publish(self, event: Event) -> None:
        ...

    def subscribe(
        self,
        topic: str,
        handler: EventHandler,
        priority: int = 100,
    ) -> None:
        ...

    def unsubscribe(
        self,
        topic: str,
        handler: EventHandler,
    ) -> None:
        ...


class IStateManager(Protocol):
    """Frozen State Manager interface."""

    async def get_state(self, category: Any, key: str) -> Any | None:
        ...

    async def set_state(self, category: Any, key: str, value: Any) -> None:
        ...

    async def delete_state(self, category: Any, key: str) -> None:
        ...


class IMemoryEngine(Protocol):
    """Frozen Memory Engine interface."""

    ... of Document
# Project Status

**Current Phase:** Phase 1 (Implementation)

## Milestones Completed
*   **[x] Phase 0: Foundation (v0.1.0-alpha)**
    *   Initial Monorepo Structure Setup
    *   Dependency Management Tooling (pnpm, uv, Turborepo)
    *   Foundational Documentation Drafted (ARCHITECTURE, ROADMAP, DECISIONS, Architecture Diagrams)
    *   Tooling configured (Ruff, MyPy, ESLint, Prettier, Pytest, Vitest)
    *   Core interface packages scaffolded (`kernel`, `interfaces`, `event_bus`, etc.)
    *   CI/CD Github Actions Configured

*   **[x] Phase 1 Design**
    *   OS Kernel Architecture Proposal drafted and approved.
    *   Development Standards (`chhaya-development-standard.md`) ratified.
    *   Subsystem Specifications (Kernel Events, Plugin API, Provider Interfaces, Agent Lifecycle) completed.

*   **[x] Phase 1 Subsystems (Active)**
    *   [x] Subsystem 1: Dependency Injection Container
    *   [x] Subsystem 2: Configuration Manager (Refactored to `ConfigProvider` abstraction)
    *   [x] Subsystem 3: Event Bus
        *   Architectural refinements integrated: Event validation (`DOMAIN.ACTION.STATUS`), `TopicMatcher` abstraction, `unsubscribe()` support, and event lifecycle hooks.
        *   Status: 100% Complete
        *   Tests: Passing
        *   Architecture: Compliant
        *   Review: Passed
    *   [x] Subsystem 4: Provider Registry
        *   Status: 100% Complete
        *   Tests: Passing
        *   Architecture: Compliant
        *   Review: Passed
    *   [x] Subsystem 5: Plugin Manager
    *   [x] Subsystem 6: Lifecycle Manager
    *   [x] Subsystem 7: Capability Registry
    *   [x] Subsystem 8: State Manager
    *   [x] Subsystem 9: Task Scheduler
    *   [x] Subsystem 10: Agent Runtime
    *   [x] Subsystem 11: Capability Execution Engine
    *   [x] Subsystem 12: Memory Engine (Core Implementation Complete)

## Active Work
Phase 1 - Subsystem 12: ContextBuilder & Semantic Search (Pending)

## Next Up
Phase 1 Implementation: Subsystem 13.

### Memory Engine Notes
The core Kernel Memory Engine implementation has been completed in `packages/kernel/src/kernel/memory/`.
- MemoryTier Explicit Implementation (Working, Short-Term, Long-Term)
- IMemoryEngine Async API completed
- Dependency Injection for IVectorStore abstraction (Stub implemented)
- Naive Fallback Search
- ContextBuilder, semantic retrieval, embedding generation, Scheduler-based TTL cleanup, and advanced context assembly remain as future milestones.
phase-0-foundation-405616865675962247
feat/state-manager-implementation-9725322336723295617

### State Manager Notes
The State Manager has been fully implemented in `packages/kernel/src/kernel/statemanager/` with 100% test coverage including:
- CRUD operations
- Transaction commit & rollback
- Snapshot creation & restoration
- Observers and event firing
- Concurrency
- Lifecycle checks
- State serializations
 phase-0-foundation-405616865675962247
