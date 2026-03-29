# Testing Strategy

## 1. Testing goals

Production-ready v0 needs proof at four layers:

1. static quality gates
2. unit tests for pure logic and invariants
3. integration and fake-adapter end-to-end tests
4. opt-in live tests against the real Codex CLI

## 2. Release gates

The default release gates are:

```bash
uv run ruff check .
uv run mypy src tests
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e -m "not live"
AGENT_LUDENS_RUN_LIVE=1 uv run pytest tests/e2e/test_live_codex.py -m live
```

Live verification is required for production sign-off when a real Codex profile is
available. If the environment blocks it, record the blocker explicitly in release evidence.

## 3. Static quality scope

Static gates must cover the tracked Python surface for production-ready v0:

- `src/`
- `tests/`
- any tracked helper scripts that participate in runtime or release flows

## 4. Test layers

### 4.1 Unit tests

Purpose:

- verify pure logic quickly
- encode invariants before integration complexity appears

Required unit coverage:

- request validation and idempotency
- queue ordering
- lease expiry/reclaim logic
- prompt-header construction
- adapter event parsing and error classification
- namespace / activity mapping
- checkpoint generation and parsing

Property-based tests are preferred for queue/store/scheduler invariants.

### 4.2 Integration tests

Purpose:

- verify the FastAPI runtime, SQLite store, and filesystem work together
- verify observability surfaces without the real Codex CLI

Required integration coverage:

- request intake and queue persistence
- activity detail and summary visibility
- cancellation transitions
- peer registration and peer request plumbing
- recent event surface backed by runtime artifacts
- supervisor exclusivity / lock behavior

### 4.3 End-to-end tests with fake adapter

Purpose:

- validate the whole control plane deterministically
- prove recovery, preemption, and failure handling

Required fake-adapter scenarios:

1. human request happy path
2. two-runtime peer request happy path using accept+poll semantics
3. restart recovery with activity/session reuse or documented requeue behavior
4. free-time preemption
5. cancellation path
6. recoverable adapter failure
7. approval-blocked failure
8. lease expiry / reclaim path

### 4.4 Live tests with real Codex

Purpose:

- verify the installed Codex CLI matches the documented adapter contract
- prove fresh-turn and resume behavior on a real runtime

Required live scenarios:

1. adapter fresh turn + resume proof
2. runtime request completion with persisted session id and artifacts
3. final agreed live peer/runtime proof if the environment supports it

## 5. Live prerequisites

Live tests are opt-in because they depend on local environment state.

Required prerequisites:

- `AGENT_LUDENS_RUN_LIVE=1`
- `codex-cli 0.117.0` (or an intentionally updated, re-validated version)
- a Codex profile that can complete non-interactive turns without new approval prompts
- clean temporary `.task-memory/` roots for each live test

## 6. Scenario matrix

### S1. Human request happy path

- submit request
- supervisor leases it
- activity folder is created
- Codex adapter runs
- request reaches terminal success

### S2. Peer request happy path

- start Agent A and Agent B
- Agent A submits to Agent B
- Agent B returns a remote `request_id`
- Agent A polls Agent B until terminal success

### S3. Restart recovery

- queue request
- begin work
- interrupt runtime
- restart runtime
- verify activity is resumed or cleanly requeued per docs

### S4. Free-time preemption

- let free-time work start
- submit a real request
- verify free-time checkpoint/yield
- verify queued request runs next

### S5. Cancellation

- queue request
- begin work
- cancel request
- verify terminal cancellation state and persisted summary/checkpoint behavior

### S6. Approval-blocked failure

- force approval-blocked adapter behavior
- verify request failure code, stderr persistence, and inspectable summary

### S7. Lease expiry / reclaim

- create or simulate an expired lease
- restart or re-run scheduling
- verify the request becomes reclaimable and runnable again

### S8. Supervisor exclusivity

- attempt two runtimes against one `.task-memory/` root
- verify only one acquires the supervisor lock

### S9. Observability

- verify runtime state files exist and remain coherent
- verify recent events are visible via file/API surfaces
- verify activity summary/checkpoint artifacts explain the next action

## 7. Evidence checklist

Release evidence should include:

- command outputs for each release gate
- one completed activity folder containing `state.json`, `summary.md`, `checkpoint.json`, and Codex artifacts
- proof of peer accept+poll behavior with two runtimes
- proof of supervisor exclusivity and lease reclaim behavior
- confirmation that docs and actual commands match

## 8. Deferred testing work

Browser/UI tests and marketplace tests are explicitly deferred because those product surfaces
are not part of production-ready v0.
