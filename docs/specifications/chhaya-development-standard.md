# Chhaya Development Standard

This document is the permanent engineering handbook for the Chhaya Agent Factory. All contributors must adhere to these standards to ensure a highly robust, secure, and maintainable AI Operating System.

---

## 1. Folder Structure Conventions
*   `apps/`: User-facing UI applications (e.g., Next.js dashboards).
*   `packages/`: Core abstractions, interfaces, and shared utilities.
*   `services/`: Standalone executables (e.g., FastAPI gateway, Task Scheduler daemon).
*   `plugins/`: Extensible capabilities adhering to the Plugin API.
*   `sdk/`: Client libraries for external interaction (TypeScript, Python).
*   `docs/`: Living documentation (`architecture/`, `decisions/`, `specifications/`).
*   **Internal Package Layout (Python):** Must use the `src/<package_name>` layout to comply with modern `hatchling` builds.

## 2. Naming Conventions
*   **Python:** PEP 8 standard. `snake_case` for variables/functions, `PascalCase` for classes.
*   **TypeScript:** `camelCase` for variables/functions, `PascalCase` for classes/interfaces.
*   **Constants:** `UPPER_SNAKE_CASE` in all languages.
*   **Events:** `domain.action.status` (e.g., `agent.task.completed`).
*   **Files:** `kebab-case` for Markdown and TypeScript/JavaScript files. `snake_case` for Python files.

## 3. Package Design Rules
*   **Single Responsibility:** A package should do one thing well (e.g., `packages/telemetry` only handles observability).
*   **Dependency Inversion:** High-level policy packages (like the Kernel) must not depend on low-level implementation packages. Both should depend on `packages/interfaces`.
*   **Zero-Dependency Core:** Foundation packages (`event_bus`, `interfaces`, `config`) must have no internal dependencies on other Chhaya packages.

## 4. Dependency Rules
*   **Third-Party Libraries:** Minimize external dependencies. Before adding a new dependency, justify it in the PR.
*   **Lockfiles:** Both `uv.lock` and `pnpm-lock.yaml` must be committed and kept up-to-date.
*   **Pinning:** Applications (`apps/`, `services/`) must pin exact versions. Packages (`packages/`) should specify broad, compatible ranges.

## 5. Import Rules
*   **Absolute Imports:** Prefer absolute imports over relative imports (e.g., `from chhaya.kernel.core import ...` instead of `from ..core import ...`).
*   **Sorting:** Imports must be automatically sorted using `ruff` (Python) and `eslint` (TypeScript).

## 6. Error Handling Standards
*   **No Silent Failures:** Never use a bare `except:` or `catch(e)` without logging.
*   **Custom Exceptions:** Define domain-specific exceptions in the relevant package (e.g., `AgentSuspendedError`).
*   **Graceful Degradation:** The system must degrade gracefully, particularly concerning the 4GB VRAM limit. Catch Out-Of-Memory exceptions and trigger the `Resource Manager` to swap state.

## 7. Logging Standards
*   **Use Telemetry:** Do not use `print()` or `console.log()` in production code. Use the `packages/telemetry` logger.
*   **Structured Data:** Log payloads must be JSON-serializable to support downstream observability tools.
*   **Levels:**
    *   `DEBUG`: Highly verbose tracing.
    *   `INFO`: Important lifecycle events (Agent started, Plugin loaded).
    *   `WARNING`: Recoverable errors (Tool timeout, retrying).
    *   `ERROR`: Non-recoverable execution errors.
    *   `CRITICAL`: System-halting errors (Kernel panic).

## 8. Testing Standards
*   **Coverage:** Code coverage must remain above 90% for all packages.
*   **Unit Tests:** Must execute without external IO (no real databases, no network calls, no real LLMs). Use mock Providers.
*   **Frameworks:** `pytest` for Python; `vitest` for TypeScript.

## 9. Documentation Standards
*   **Docstrings:** All public classes, functions, and interfaces must have docstrings explaining their purpose, arguments, and return values.
*   **Living Documents:** `ARCHITECTURE.md`, `ROADMAP.md`, and `CHANGELOG.md` must be updated alongside relevant code changes.

## 10. Interface Design Guidelines
*   **Protocols over ABCs:** In Python, prefer `typing.Protocol` over `abc.ABC` for structural subtyping without forced inheritance.
*   **Small Interfaces:** Favor smaller, focused interfaces over large monolithic ones (Interface Segregation Principle).

## 11. Event Naming Guidelines
*   Must strictly follow `domain.action.status`.
*   Must be documented in `docs/specifications/kernel-events.md` if added to the core system.

## 12. ADR Requirements
*   An Architecture Decision Record (ADR) is mandatory for:
    *   Adding a new architectural layer.
    *   Changing IPC mechanisms.
    *   Adding a major third-party dependency.
    *   Changing the provider interface structure.
*   ADRs must be placed in `docs/decisions/` and indexed in `DECISIONS.md`.

## 13. Plugin Development Standards
*   Plugins must declare capabilities in a `manifest.json`.
*   Plugins must not assume they have full access to the Event Bus.
*   Plugins must gracefully handle `shutdown()` calls without leaking memory or leaving orphan threads.

## 14. Security Coding Standards
*   **No Hardcoded Secrets:** API keys and credentials must only be accessed via `packages/config` or `packages/security`.
*   **Principle of Least Privilege:** Agents and plugins run with minimal permissions.
*   **Sanitization:** All LLM outputs executing terminal commands or SQL must be heavily sanitized and sandboxed.

## 15. Performance Guidelines
*   **Hardware Constraints:** Always assume the target machine is a Ryzen 7 with 32GB RAM and exactly 4GB VRAM.
*   **Asynchronous:** All network IO, disk IO, and LLM generation must be asynchronous to prevent blocking the Kernel Event Loop.

## 16. Versioning Strategy
*   Follow Semantic Versioning (`MAJOR.MINOR.PATCH`).
*   Pre-1.0.0 releases may break APIs on minor version bumps. Post-1.0.0, API breaks require a major version bump.

## 17. Deprecation Policy
*   Deprecated features must be clearly marked with `@deprecated` decorators and emit a `WARNING` log for at least one full minor release cycle before removal.

## 18. Backward Compatibility Policy
*   Events traversing the Event Bus must be backward compatible. If a payload schema changes, the `version` field must be bumped.

## 19. Code Review Checklist
*   [ ] Does this change violate the 4GB VRAM constraint?
*   [ ] Are tests included and passing?
*   [ ] Are the relevant ADRs or specifications updated?
*   [ ] Is there any tight coupling to an external library (e.g., LangChain) instead of a Provider Interface?
*   [ ] Are logging and error handling implemented correctly?

## 20. Definition of Done (DoD)
For a Phase or major feature to be considered "Done":
1.  Code is implemented and follows all style guidelines.
2.  Tests are written, and CI pipeline passes.
3.  All documentation (ADRs, Specifications, API docs) is updated.
4.  The system builds and runs successfully on a local machine meeting the hardware constraints.
5.  The feature has been explicitly approved via Code Review.