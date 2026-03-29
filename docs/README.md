# Agent Ludens Docs

This directory is the **normative contract** for Agent Ludens production-ready v0.
The contract is intentionally scoped to the **Stage 1 local runtime only**.

Use this docs set to:

1. understand the shipped v0 boundary
2. implement or harden the Stage 1 runtime
3. write tests and release evidence against one stable contract
4. defer Stage 2/3 work without re-deriving what is required for v0

## Scope boundary

Production-ready v0 means:

- one machine
- loopback-only HTTP
- one active Codex-driven activity at a time
- SQLite-backed queue and activity records
- `.task-memory/` as the durable source of truth
- peer-to-peer request submission using accept+poll semantics
- release gates for lint, typecheck, non-live tests, and opt-in live tests

Production-ready v0 does **not** mean:

- marketplace delegation
- tokens or wallets
- multi-machine networking
- any other Stage 3 roadmap work

## Current Codex CLI contract

Validated locally on **March 29, 2026**:

- `codex-cli 0.117.0`
- `codex exec --json <prompt>`
- `codex exec resume <session_id> --json <prompt>`

## How to use the docs

Recommended reading order:

1. [Project Structure](./project_structure.md)
2. [Product Spec](./product_spec.md)
3. [Architecture](./architecture.md)
4. [API Spec](./api_spec.md)
5. [Persistence And Context](./persistence_and_context.md)
6. [Runtime Loop](./runtime_loop.md)
7. [Testing Strategy](./testing_strategy.md)
8. [Implementation Plan](./implementation_plan.md)
9. [Release Checklist](./release_checklist.md)

## Local environment baseline

Before running the Stage 1 runtime or release gates, initialize and sync the dedicated
project environment with `uv`:

```bash
uv init
uv sync
```

Treat `uv init` as the explicit project bootstrap step even when the repository is already
initialized and the local `.venv` already exists.

## Document index

- [Project Structure](./project_structure.md): runtime framing and vocabulary
- [Product Spec](./product_spec.md): product boundary, requirements, acceptance criteria
- [Architecture](./architecture.md): component model and exclusivity rules
- [API Spec](./api_spec.md): HTTP envelopes, status semantics, peer contract
- [Persistence And Context](./persistence_and_context.md): canonical filesystem and SQLite contract
- [Runtime Loop](./runtime_loop.md): scheduler, checkpointing, resume, shutdown, recovery
- [Testing Strategy](./testing_strategy.md): release gates, scenario matrix, live prerequisites
- [Implementation Plan](./implementation_plan.md): Stage 1 milestones and deferred roadmap
- [Release Checklist](./release_checklist.md): final operator/release sign-off steps

## Maintenance And Community Docs

These docs support idle-time maintenance and public-facing preparation without widening the
Stage 1 contract:

- [Free-Time Maintenance](./free_time_maintenance.md): safe rules for one bounded maintenance quantum
- [Community Update Template](./community_update_template.md): factual public update seed for Stage 1 progress
- [Community Publish Checklist](./community_publish_checklist.md): claim-discipline checks before posting
- [Release Evidence Template](./release_evidence_template.md): capture format for verification notes
- [Scope Alignment Note](./scope_alignment_note.md): short guardrail note for Stage 1-only messaging

## Guiding rules

- Prefer the smallest implementation that fully satisfies the Stage 1 contract.
- Treat `.task-memory/` and SQLite as canonical state; model context is cache.
- Keep docs aligned to shippable behavior, not aspirational roadmap work.
- If a requirement is deferred, label it as deferred instead of leaving it ambiguous.
