# Agent Ludens Docs

This directory is the project contract for future agents.

The goal is to make the project implementable without re-deriving the design from chat history.
Later agents should be able to use this docs set to:

1. plan work
2. implement features
3. write code-level tests
4. run live end-to-end tests

## Decision Snapshot

The current v0 decisions are intentionally concrete:

- Language: Python 3.12 in the `agent-ludens` uv project
  - NOTE: you must build a new uv project via uv init
- Web stack: FastAPI + Uvicorn + Pydantic
- Storage: SQLite plus filesystem checkpoints under `.task-memory/`
- Codex integration: `codex exec --json` and `codex exec resume --json`
- Network model: loopback-only HTTP on `localhost:<port>`
- Concurrency model: one active Codex turn at a time per agent instance
- Peer communication model: HTTP request envelopes between local agents

Validated against the locally installed Codex CLI on 2026-03-29:

- `codex-cli 0.114.0`

## How To Use These Docs

- Start with [Project Structure](./project_structure.md) for the concept.
- Read [Product Spec](./product_spec.md) for scope, requirements, and acceptance criteria.
- Read [Architecture](./architecture.md) and [Runtime Loop](./runtime_loop.md) before coding.
- Read [API Spec](./api_spec.md) and [Persistence And Context](./persistence_and_context.md) before touching data models.
- Use [Implementation Plan](./implementation_plan.md) to choose the next delivery milestone.
- Use [Testing Strategy](./testing_strategy.md) for unit, integration, and live-test execution.

## Suggested Workflow For Future Agents

1. Confirm which milestone from [Implementation Plan](./implementation_plan.md) is in scope.
2. Implement only the contracts needed for that milestone.
3. Add or update tests from [Testing Strategy](./testing_strategy.md).
4. Validate contract conformance against:
   - [Product Spec](./product_spec.md)
   - [API Spec](./api_spec.md)
   - [Persistence And Context](./persistence_and_context.md)
   - [Runtime Loop](./runtime_loop.md)
5. Run live tests only after code-level tests pass.

## Document Index

- [Project Structure](./project_structure.md): concept and framing
- [Product Spec](./product_spec.md): goals, non-goals, requirements, success criteria
- [Architecture](./architecture.md): system decomposition and design decisions
- [API Spec](./api_spec.md): HTTP contracts and message schemas
- [Persistence And Context](./persistence_and_context.md): `.task-memory/` layout and state contracts
- [Runtime Loop](./runtime_loop.md): scheduler, preemption, prompt header, Codex adapter behavior
- [Testing Strategy](./testing_strategy.md): unit, integration, end-to-end, and live tests
- [Implementation Plan](./implementation_plan.md): milestone-by-milestone delivery plan
