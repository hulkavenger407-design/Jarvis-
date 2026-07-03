# Package Dependency Diagram

This diagram visualizes how the internal Monorepo packages depend on one another.

## Dependency Diagram

```mermaid
graph TD
    subgraph "Services"
        API[services/api]
    end

    subgraph "Core Hub"
        Kernel[packages/kernel]
    end

    subgraph "Abstractions & Infrastructure"
        Interfaces[packages/interfaces]
        EventBus[packages/event_bus]
        PluginSDK[packages/plugin_sdk]
        Config[packages/config]
        Telemetry[packages/telemetry]
        Security[packages/security]
    end

    %% Dependency flow (A --> B means A imports/depends on B)
    API --> Kernel
    API --> Config
    API --> Telemetry

    Kernel --> Interfaces
    Kernel --> EventBus
    Kernel --> PluginSDK
    Kernel --> Config
    Kernel --> Telemetry
    Kernel --> Security

    PluginSDK --> Interfaces
    PluginSDK --> EventBus

    %% Note: Interfaces, EventBus, Config, Telemetry should generally have NO internal dependencies.
```

## Description

To maintain a clean architecture, dependencies must flow inwards toward the core abstractions:
1. **Zero-Dependency Packages:** Packages like `interfaces`, `event_bus`, `config`, and `telemetry` form the absolute base. They should not import from other internal packages.
2. **The Kernel:** The Kernel orchestrates the system, meaning it depends on almost all lower-level infrastructure packages.
3. **Services:** Standalone applications (like the FastAPI gateway) depend on the Kernel and configuration/telemetry, but should never bypass the Kernel to execute business logic directly.