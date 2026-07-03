# ADR 0002: Local First AI Strategy

## Status
Accepted

## Context
The primary hardware constraint is a Windows machine with a Ryzen 7 CPU, 32GB RAM, and crucially, only **4GB of VRAM**. Modern LLMs easily exceed this VRAM footprint.

## Decision
Chhaya will adopt a strictly "Local-First" methodology.
- **Ollama** will serve as the default inference backend.
- The system will prioritize small, quantized GGUF models that can utilize CPU offloading when VRAM is exhausted.
- The architecture must support lazy-loading models to ensure multiple specialized agents can take turns without causing Out-of-Memory (OOM) errors.

## Alternatives Considered
- **Cloud-First (OpenAI/Anthropic):** Defeats the purpose of the local-first mandate and introduces ongoing costs.
- **Requiring High-End GPUs:** Restricts the user base and violates the core hardware constraint.

## Trade-offs
- **Pros:** Maximum privacy, no recurring costs, works completely offline.
- **Cons:** Inference will be slower than cloud alternatives or high-end local GPUs. Managing memory aggressively increases complexity in the orchestration engine.

## Long-term Implications
By proving the system works on constrained hardware, scaling up to more powerful local GPUs or attaching cloud providers as optional enhancements becomes trivial.