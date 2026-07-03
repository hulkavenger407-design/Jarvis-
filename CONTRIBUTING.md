# Contributing to Chhaya Agent Factory

Thank you for your interest in contributing! This project is designed to be an open-source AI Operating System.

## Development Environment Setup

This project uses a polyglot monorepo structure.

### Prerequisites
1. **Node.js** (v20+)
2. **pnpm** (v9+)
3. **Python** (v3.11+)
4. **uv** (latest)

### Getting Started
1. Clone the repository.
2. Install Node dependencies: `pnpm install`
3. Install Python dependencies: `uv sync`
4. Run tests: `pnpm run test`

## Architectural Guidelines
* **Read the ADRs:** Before proposing major changes, review `docs/decisions/` to understand historical context.
* **Interface First:** If you are adding a new capability, define its interface in `packages/interfaces/` first.
* **Test Everything:** PRs without tests will not be accepted.

## Pull Request Process
1. Ensure `pnpm run build`, `pnpm run lint`, and `pnpm run test` all pass.
2. Update the `CHANGELOG.md`.
3. Request a review.