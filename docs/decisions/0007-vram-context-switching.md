# ADR 0007: VRAM Context Switching & Ephemeral Agents

## Status
Accepted

## Context
The system has a strict 4GB VRAM constraint, but must support multiple agents.

## Decision
Agents must be treated as ephemeral processes. The `AgentManager` and `ResourceManager` will implement "Context Switching."
- When an agent is waiting for a tool or human input, it is transitioned to a `SUSPENDED` state.
- Its memory is flushed to disk, and the LLM context is unloaded from VRAM.

## Alternatives Considered
- **Keep-Alive:** Keeping the model context in VRAM for speed.
- **Cloud Fallback:** Automatically sending overflow requests to OpenAI.

## Trade-offs
- **Pros:** Guarantees the system will never crash due to OOM on constrained hardware.
- **Cons:** Swapping models into and out of VRAM introduces significant latency (seconds) when switching between active agents.

## Long-term Implications
This forces developers to write stateless, resumable agent logic. This is highly beneficial for eventual distributed execution (Phase 6), where an agent might suspend on Node A and resume on Node B.