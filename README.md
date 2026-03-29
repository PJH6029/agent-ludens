# Agent Ludens

Agent Ludens is a local, always-on control plane around Codex. It provides:

- a FastAPI loopback API for human and peer requests
- a durable SQLite request queue
- filesystem-backed activity state under `.task-memory/`
- a single-slot supervisor that runs queued work before free-time tasks
- pluggable Codex adapters (fake by default, real CLI opt-in)

## Quick start

```bash
uv sync
uv run agent-ludens
```

## Test commands

```bash
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e -m "not live"
AGENT_LUDENS_RUN_LIVE=1 uv run pytest tests/e2e/test_live_codex.py -m live
```

## Configuration

Runtime settings are loaded from environment variables with the `AGENT_LUDENS_` prefix. Useful ones include:

- `AGENT_LUDENS_TASK_MEMORY_ROOT`
- `AGENT_LUDENS_PORT`
- `AGENT_LUDENS_ENABLE_FREE_TIME`
- `AGENT_LUDENS_ADAPTER_MODE=fake|real`
- `AGENT_LUDENS_CODEX_PROFILE`
- `AGENT_LUDENS_AUTH_TOKEN`

The docs in `docs/` remain the source of truth for the runtime contract.
