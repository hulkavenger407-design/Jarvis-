# Provider Abstraction Layer

The Provider Abstraction Layer (PAL) enforces dependency inversion. The core logic depends on abstract interfaces, never on concrete external libraries.

## Architecture Diagram

```mermaid
classDiagram
    %% Core Interfaces
    class LLMProvider {
        <<interface>>
        +generate(prompt: str) str
        +stream(prompt: str) Iterator
    }

    class MemoryProvider {
        <<interface>>
        +save(key: str, value: Any)
        +load(key: str) Any
    }

    class ToolProvider {
        <<interface>>
        +execute(tool_name: str, args: dict) Any
        +get_schema() dict
    }

    %% Concrete Implementations
    class OllamaProvider {
        -endpoint: str
        +generate(prompt: str) str
    }
    class OpenAIProvider {
        -api_key: str
        +generate(prompt: str) str
    }

    class SQLiteMemoryProvider {
        -db_path: str
        +save(key, value)
    }

    class ChromaVectorProvider {
        -collection: str
        +save(key, value)
    }

    class MCPToolProvider {
        -mcp_client: Any
        +execute(tool_name, args)
    }

    %% Relationships
    LLMProvider <|-- OllamaProvider
    LLMProvider <|-- OpenAIProvider

    MemoryProvider <|-- SQLiteMemoryProvider
    MemoryProvider <|-- ChromaVectorProvider

    ToolProvider <|-- MCPToolProvider

    %% Core usage
    class AgentLogic {
        -llm: LLMProvider
        -memory: MemoryProvider
        +run()
    }

    AgentLogic --> LLMProvider : depends on
    AgentLogic --> MemoryProvider : depends on
```

## Description

By ensuring `AgentLogic` only ever accepts instances of `LLMProvider` or `MemoryProvider`, Chhaya achieves:
1. **Testability:** Mock providers can be injected during testing.
2. **Extensibility:** A developer can add a `GeminiProvider` simply by implementing the `LLMProvider` protocol, without needing to change a single line of the core agent orchestration code.