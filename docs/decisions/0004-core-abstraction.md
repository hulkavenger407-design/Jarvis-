# ADR 0004: Core Abstraction and Kernel

## Status
Accepted

## Context
AI frameworks like LangChain and LangGraph evolve rapidly. Tightly coupling the application logic to these frameworks leads to high technical debt when paradigms shift.

## Decision
We will build a central **Chhaya Kernel** with an **Event Bus**. All external capabilities (LLMs, Memory, Vector DBs, tools) will sit behind strict interfaces.

## Alternatives Considered
- **Direct integration with LangChain:** Quick to build initially but traps the system within LangChain's specific data structures and update cycles.

## Trade-offs
- **Pros:** Highly testable, extremely extensible. We can swap a LangChain tool wrapper for a native MCP tool without changing agent logic.
- **Cons:** Higher initial development cost to build adapters for every service.

## Long-term Implications
This guarantees the software functions as an Operating System. Features become plugins, and the core remains stable, allowing for a healthy open-source ecosystem to grow around it.