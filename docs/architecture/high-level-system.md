# High-Level System Architecture

This document outlines the high-level architecture of the Chhaya Agent Factory, illustrating how the major components interact to form an AI Operating System.

## Architecture Diagram

```mermaid
graph TD
    subgraph "External Clients (Apps / SDKs)"
        WebUI[Web Dashboard UI]
        CLI[Command Line Interface]
        SDK[Third-party Integrations via SDK]
    end

    subgraph "Services Layer (REST/WebSockets)"
        API[FastAPI Gateway]
    end

    subgraph "Chhaya Core Runtime"
        Kernel((Chhaya Kernel))
        EventBus{Event Bus}
    end

    subgraph "Packages & Capabilities"
        Agents[Agent Orchestration]
        MemSys[Memory System]
        RAG[Knowledge Base / RAG]
        ToolOrch[Tool Orchestrator]
    end

    subgraph "Provider Interfaces (Abstractions)"
        LLMIface[LLM Provider Interface]
        MemIface[Storage Interface]
        ToolIface[Tool Interface]
    end

    subgraph "Concrete Implementations (Plugins/Adapters)"
        Ollama[(Ollama - Local)]
        CloudLLM[(OpenAI/Anthropic)]
        VectorDB[(Local Vector DB)]
        MCPTools[MCP Tools]
        LocalTools[Local File System Tools]
    end

    %% Connections
    WebUI -->|REST / SSE| API
    CLI -->|REST| API
    SDK -->|REST / WebSockets| API

    API --> Kernel

    Kernel <--> EventBus

    Kernel --> Agents
    Kernel --> MemSys
    Kernel --> RAG
    Kernel --> ToolOrch

    Agents --> EventBus
    MemSys --> EventBus
    RAG --> EventBus
    ToolOrch --> EventBus

    Agents --> LLMIface
    MemSys --> MemIface
    RAG --> MemIface
    ToolOrch --> ToolIface

    LLMIface -.-> Ollama
    LLMIface -.-> CloudLLM
    MemIface -.-> VectorDB
    ToolIface -.-> MCPTools
    ToolIface -.-> LocalTools
```

## Description

The architecture is designed strictly around the **Chhaya Kernel** which sits at the center of the system. Clients (like the Next.js Dashboard or CLI) never talk directly to agents or providers; they route through the FastAPI Service layer into the Kernel.

The Kernel communicates with major components (Agents, Memory, RAG, Tools) often asynchronously via the **Event Bus**.

Crucially, the core logic never interacts directly with concrete implementations like Ollama or a specific Vector DB. It strictly utilizes the **Provider Interfaces**. This allows the concrete implementations to be swapped seamlessly (e.g., swapping local Ollama for Cloud-based OpenAI) without altering the internal business logic.