# Agent Ludens

Agent Ludens is the **production-ready v0 Stage 1 local control plane around Codex**.
It keeps one role-based agent alive on one machine, exposes a loopback-only HTTP API,
persists request and activity state under `.task-memory/`, and runs exactly one
Codex-driven activity at a time.

Production-ready v0 is intentionally **Stage 1 only**.

- **Included in the production-ready v0 contract:** local API, durable SQLite queue +
  filesystem activity state, single-slot supervisor loop, fake and real Codex adapters,
  peer request submit+poll, and file-backed observability.
- **Deferred:** owner web UI, frontend event feed, marketplace/delegation economy,
  token system, and multi-machine networking.

Validated against the locally installed Codex CLI on **March 29, 2026**:

- `codex-cli 0.117.0`
- fresh turns: `codex exec --json <prompt>`
- resumed turns: `codex exec resume <session_id> --json <prompt>`

## Production-ready v0 scope

Agent Ludens v0 must provide:

- a loopback-only FastAPI runtime for health, agent info, queue, requests, activities,
  peers, and recent event inspection
- durable queue and activity state in SQLite plus `.task-memory/`
- one active Codex execution slot guarded by supervisor exclusivity
- free-time quanta that yield to queued work
- peer-to-peer local request handling using **accept + poll** semantics
- explicit release gates for lint, typecheck, non-live tests, and opt-in live tests

Agent Ludens v0 does **not** include:

- an owner-facing web dashboard
- a marketplace / job board / delegation economy
- public internet exposure
- multiple simultaneous Codex turns inside one runtime

## Quick start

Install dependencies and start the loopback runtime:

```bash
uv sync
uv run agent-ludens
```

By default the runtime uses the **fake** Codex adapter for deterministic local
development and tests.

To run against the real Codex CLI:

```bash
export AGENT_LUDENS_ADAPTER_MODE=real
export AGENT_LUDENS_CODEX_PROFILE=<non-interactive-profile>
uv run agent-ludens
```

Useful environment variables:

- `AGENT_LUDENS_AGENT_ID`
- `AGENT_LUDENS_ROLE`
- `AGENT_LUDENS_PORT`
- `AGENT_LUDENS_TASK_MEMORY_ROOT`
- `AGENT_LUDENS_AUTH_TOKEN`
- `AGENT_LUDENS_ENABLE_FREE_TIME`
- `AGENT_LUDENS_ADAPTER_MODE=fake|real`
- `AGENT_LUDENS_CODEX_PROFILE`
- `AGENT_LUDENS_CODEX_MODEL`
- `AGENT_LUDENS_CODEX_SKIP_GIT_REPO_CHECK`

## API-first operator workflow

Human operation is HTTP-first in v0. `curl`, `httpx`, tests, or a thin wrapper are all
acceptable operator surfaces.

Example request submission:

```bash
curl -X POST http://127.0.0.1:7101/v1/requests \
  -H 'Content-Type: application/json' \
  -d '{
    "kind": "human_task",
    "priority": 50,
    "source": {"type": "human", "id": "cli"},
    "summary": "Summarize recent activity",
    "details": {"instructions": "Reply with a compact summary."},
    "reply": {"mode": "poll"}
  }'
```

Poll with `GET /v1/requests/{request_id}` until the request reaches a terminal status.

## Release gates

The production-ready v0 release gates are:

```bash
uv run ruff check .
uv run mypy src tests
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e -m "not live"
AGENT_LUDENS_RUN_LIVE=1 uv run pytest tests/e2e/test_live_codex.py -m live
```

Plus one required **Playwright/browser-driven live verification** against the running local
runtime (for example via the FastAPI docs/operator surface) with saved evidence.

Use the live gates only when a real Codex profile is available. A production release
should either pass them or record a specific live-environment blocker in the release notes.

## Documentation map

`docs/` is the normative contract for production-ready v0:

- [`docs/README.md`](docs/README.md) — how to read the docs set
- [`docs/project_structure.md`](docs/project_structure.md) — concept and runtime framing
- [`docs/product_spec.md`](docs/product_spec.md) — scope, requirements, acceptance criteria
- [`docs/architecture.md`](docs/architecture.md) — component and lifecycle design
- [`docs/api_spec.md`](docs/api_spec.md) — loopback API contracts and peer semantics
- [`docs/persistence_and_context.md`](docs/persistence_and_context.md) — `.task-memory/` contract
- [`docs/runtime_loop.md`](docs/runtime_loop.md) — scheduler, checkpoint, resume, and recovery rules
- [`docs/testing_strategy.md`](docs/testing_strategy.md) — release-grade verification matrix
- [`docs/implementation_plan.md`](docs/implementation_plan.md) — Stage 1 delivery plan + deferred roadmap
- [`docs/release_checklist.md`](docs/release_checklist.md) — final ship checklist

## Roadmap boundary

Stage 2 (owner UI) and Stage 3 (marketplace/delegation economy) remain visible as roadmap
ideas, but they are **not** part of the production-ready v0 contract.
