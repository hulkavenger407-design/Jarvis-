# Memory Architecture

The Memory subsystem is responsible for handling ephemeral conversational context and long-term semantic knowledge.

## Architecture Diagram

```mermaid
graph TD
    subgraph "Agent"
        Ag[Agent Instance]
    end

    subgraph "Memory Subsystem"
        MemOrch[Memory Orchestrator]
        STM[Short-Term Memory<br/>(Working Context)]
        LTM[Long-Term Memory<br/>(Semantic / Episodic)]
    end

    subgraph "Storage Providers (Interfaces)"
        KV[Key-Value Store<br/>e.g. SQLite / Redis]
        Vector[Vector Database<br/>e.g. Chroma / Qdrant]
    end

    Ag -->|Query/Store Context| MemOrch
    MemOrch -->|Recent Chat History| STM
    MemOrch -->|RAG / Semantic Search| LTM

    STM --> KV
    LTM --> Vector
```

## Description

1. **Short-Term Memory (STM):** Stores the immediate conversational context, the "scratchpad" of the agent, and recent tool outputs. Typically backed by a fast, local Key-Value store like SQLite or an in-memory dictionary.
2. **Long-Term Memory (LTM):** Stores facts, historical decisions, and embedded documents (RAG). Backed by a Vector Database interface.
3. **Orchestrator:** The Agent does not interact with the databases directly. It asks the Memory Orchestrator to "recall facts about X" or "store this preference." The orchestrator handles embedding the text and querying the correct underlying provider.