# ADR 0005: OS Kernel Architecture

## Status
Accepted

## Context
Initial designs for Chhaya favored a simple message-router pattern. However, the vision of the project is to build an "AI Operating System" capable of managing hardware constraints, process lifecycles, and security boundaries.

## Decision
We will adopt a multi-manager OS Architecture for the Chhaya Kernel. This includes discrete subsystems such as a Boot Manager, Lifecycle Manager, Resource Manager, Agent Manager, and Permission Manager.

## Alternatives Considered
- **Monolithic Router:** A single class that receives API requests and directly calls LangChain/Agent logic.
- **Microservices:** Breaking the managers into separate Docker containers.

## Trade-offs
- **Pros:** The OS architecture ensures excellent separation of concerns. It handles the 4GB VRAM constraint elegantly by allowing the Resource Manager to interrupt the Agent Manager.
- **Cons:** Higher initial engineering complexity and abstraction overhead compared to a simple script.

## Long-term Implications
This sets the foundation for true multi-agent orchestration. By treating agents like OS processes, we can easily add features like process priority, memory swapping, and strict permission sandboxing in the future.