# ADR 0003: API Communication Protocol

## Status
Accepted

## Context
The Python backend (AI runtime) needs to communicate with the TypeScript frontend (Dashboard) and potentially CLI tools. We need a performant, strongly-typed way to handle standard requests and streaming AI responses.

## Decision
We will use **REST over FastAPI** for standard operations and **WebSockets/SSE** for streaming data.

## Alternatives Considered
- **gRPC:** Excellent for internal microservices, but introduces significant complexity (managing `.proto` files, compiling stubs) for early development, especially when communicating directly with a browser client.
- **GraphQL:** High overhead for a system that mostly needs straightforward command/response and streaming capabilities.

## Trade-offs
- **Pros:** FastAPI is industry standard, highly performant, and automatically generates OpenAPI specs which can be used to generate strict TypeScript clients. WebSockets handle the necessary real-time streaming for agent thoughts/actions.
- **Cons:** REST lacks the strict, binary efficiency of gRPC for inter-service backend communication.

## Long-term Implications
We design the API layer to be decoupled from the core business logic. If performance dictates breaking the backend into distributed microservices later, we can introduce gRPC internally without rewriting the underlying capabilities.