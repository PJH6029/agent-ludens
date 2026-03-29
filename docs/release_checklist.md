# Release Checklist

Use this checklist to decide whether Agent Ludens qualifies as production-ready v0.

## 1. Scope check

Confirm the release still targets **Stage 1 only**:

- [ ] loopback-only local runtime
- [ ] API-first human operator surface
- [ ] durable queue + activity persistence
- [ ] single active Codex slot with supervisor exclusivity
- [ ] peer accept+poll contract
- [ ] Stage 3 features still deferred

## 2. Environment prerequisites

- [ ] `uv init` confirmed the dedicated project environment
- [ ] `uv sync` completed successfully
- [ ] `codex-cli 0.117.0` (or intentionally re-validated replacement) is installed
- [ ] real Codex profile is available for live verification, or a blocker is recorded
- [ ] Playwright/browser tooling is available for the browser-driven live proof
- [ ] clean `.task-memory/` root is available for verification runs

## 3. Static and automated gates

Run and capture output for:

```bash
uv run ruff check .
uv run mypy src tests
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e -m "not live"
AGENT_LUDENS_RUN_LIVE=1 uv run pytest tests/e2e/test_live_codex.py -m live
```

Also capture one required **Playwright/browser-driven live verification** artifact against the
running local runtime.

Checklist:

- [ ] lint passes
- [ ] typecheck passes
- [ ] unit tests pass
- [ ] integration tests pass
- [ ] non-live e2e tests pass
- [ ] live tests pass, or the blocker is explicitly documented
- [ ] Playwright/browser-driven live verification evidence is captured

## 4. Contract checks

- [ ] README and `docs/` agree on the Stage 1-only scope
- [ ] docs mention the same commands that were actually used
- [ ] Codex CLI command shapes match the runtime adapter implementation
- [ ] peer semantics are documented as accept+poll, not callback-required
- [ ] lease reclaim and supervisor lock behavior are documented and tested

## 5. Manual inspectability checks

Inspect one completed run and confirm:

- [ ] request detail shows durable status/result/error data
- [ ] activity folder contains `state.json`, `summary.md`, `checkpoint.json`, `inbox.md`
- [ ] `.task-memory/runtime/agent_state.json` and `scheduler_state.json` are coherent
- [ ] `.task-memory/runtime/event-log.jsonl` explains recent runtime decisions
- [ ] `.task-memory/codex/<activity_id>/` contains JSONL, final message, stderr, and metadata
- [ ] a future maintainer could determine the next action without chat history

## 6. Scenario proof

Confirm evidence exists for:

- [ ] human request happy path
- [ ] two-runtime peer request happy path
- [ ] restart recovery
- [ ] free-time preemption
- [ ] cancellation
- [ ] approval-blocked failure
- [ ] lease expiry / reclaim
- [ ] supervisor exclusivity / lock contention
- [ ] live fresh-turn + resume proof
- [ ] Playwright/browser-driven live verification

## 7. Release notes

Record:

- verification date
- Codex CLI version used
- exact commands run
- known limitations still inside Stage 1 scope
- any explicit live-test blocker if present

## 8. Ship decision

Agent Ludens is ready to ship as production-ready v0 only when every required item above is
checked or any exception is documented with a concrete blocker and next action.
