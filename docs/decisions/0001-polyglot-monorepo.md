# ADR 0001: Polyglot Monorepo Architecture

## Status
Accepted

## Context
The project requires building a robust AI core runtime (traditionally built in Python due to ecosystem dominance) and a modern web dashboard and SDK suite (best suited for TypeScript). Managing these ecosystems in separate repositories creates overhead in sharing contracts, API schemas, and deployment pipelines.

## Decision
We will use a polyglot monorepo structure managed by **Turborepo**.
- Node.js/TypeScript packages will use **pnpm** workspaces.
- Python packages will use **uv** workspaces.

## Alternatives Considered
- **Strictly Python:** Difficult to build a high-quality, modern web UI without a dedicated JavaScript/TypeScript framework.
- **Strictly TypeScript (LangChain.js):** Limits access to cutting-edge AI research and libraries which almost exclusively target Python first.
- **Multiple Repositories:** High maintenance overhead for keeping APIs and schemas in sync between frontend and backend.

## Trade-offs
- **Pros:** Unified CI/CD, easier schema sharing, unified versioning.
- **Cons:** Complex initial setup. Developers must be comfortable with both `pnpm` and `uv` commands depending on what part of the repository they touch.

## Long-term Implications
This sets the foundation for scaling independent teams working on UI vs AI runtime while sharing common infrastructure and CI processes.