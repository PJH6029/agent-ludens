# Release Evidence Template

Use this template to capture production-ready v0 release evidence without expanding the
Stage 1 scope. Keep every field factual. If a gate is blocked or intentionally skipped,
record the blocker instead of implying success.

This template supplements:

- `docs/release_checklist.md`
- `docs/testing_strategy.md`
- `docs/README.md`

## Template

```md
# Release Evidence

## Release snapshot

- verification date: <YYYY-MM-DD>
- release target: production-ready v0 Stage 1 local runtime
- verifier: <name or team>
- repository revision: <commit or working-tree note>

## Environment

- project bootstrap: `uv init`
- dependency sync: `uv sync`
- Codex CLI version: <version or blocker>
- live Codex profile available: <yes/no + note>
- Playwright/browser tooling available: <yes/no + note>
- verification `.task-memory/` root: <path or note>

## Commands run

```bash
uv run ruff check .
uv run mypy src tests
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e -m "not live"
AGENT_LUDENS_RUN_LIVE=1 uv run pytest tests/e2e/test_live_codex.py -m live
```

Record the actual command output locations or summaries below.

## Gate results

- lint: <pass/fail/not run + evidence>
- typecheck: <pass/fail/not run + evidence>
- unit tests: <pass/fail/not run + evidence>
- integration tests: <pass/fail/not run + evidence>
- non-live e2e: <pass/fail/not run + evidence>
- live tests: <pass/fail/blocked + evidence>
- browser-driven live verification: <pass/fail/blocked + evidence>

## Contract alignment checks

- README and `docs/` agree on Stage 1 scope: <yes/no + note>
- documented commands match actual commands used: <yes/no + note>
- adapter command shapes match the documented Codex CLI contract: <yes/no + note>
- peer flow remains accept + poll: <yes/no + note>
- lease reclaim and supervisor lock behavior are documented and tested: <yes/no + note>

## Scenario evidence

- human request happy path: <evidence>
- two-runtime peer request happy path: <evidence>
- restart recovery: <evidence>
- free-time preemption: <evidence>
- cancellation: <evidence>
- approval-blocked failure: <evidence>
- lease expiry / reclaim: <evidence>
- supervisor exclusivity / lock contention: <evidence>
- live fresh-turn + resume proof: <evidence or blocker>
- Playwright/browser-driven verification: <evidence or blocker>

## Inspectability spot check

- completed activity folder reviewed: <activity_id/path>
- `state.json`, `summary.md`, `checkpoint.json`, `inbox.md` present: <yes/no>
- runtime state files coherent: <yes/no + note>
- event log explains recent runtime decisions: <yes/no + note>
- Codex artifacts persisted for inspected activity: <yes/no + note>
- next action understandable without chat history: <yes/no + note>

## Known blockers or exceptions

- <blocker>
- <blocker>

## Ship decision

- ship status: <ready/not ready>
- rationale: <short explanation tied to checklist results>
- next required action: <short action>
```

## Usage notes

- Leave unchecked work as `not run` or `blocked`; do not silently convert it into a pass.
- If the Codex CLI version differs from the validated version in `docs/README.md`, note the
  re-validation status explicitly.
- Keep evidence references concrete enough that another maintainer can locate them later.
