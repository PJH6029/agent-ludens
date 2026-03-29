# Testing Strategy

## 1. Testing Goals

This project needs tests at four levels:

1. unit tests for internal logic
2. integration tests for process and storage behavior
3. end-to-end tests with a fake Codex adapter
4. live end-to-end tests with the real Codex CLI

The docs must support all four.

## 2. Test Layers

### 2.1 Unit Tests

Purpose:

- verify pure logic
- keep feedback fast

Modules that should have unit coverage:

- request validation
- priority ordering
- lease expiry logic
- state transitions
- prompt header construction
- checkpoint generation and parsing
- filesystem path resolution
- peer request envelope validation

Recommended framework:

- `pytest`

### 2.2 Integration Tests

Purpose:

- verify local components together without real Codex

Integration targets:

- FastAPI app plus SQLite store
- supervisor plus scheduler
- activity manager plus filesystem
- startup recovery
- cancellation transitions

Recommended tools:

- `pytest`
- `httpx.AsyncClient`
- temp directories
- temporary SQLite databases

### 2.3 End-to-End Tests With Fake Codex

Purpose:

- validate the whole control plane deterministically

Approach:

- replace the real Codex adapter with a stub process or test double that emits representative JSONL
- drive HTTP requests through the public API
- assert on persisted state and responses

Fake adapter must simulate:

- fresh thread creation
- resumed session
- success
- recoverable failure
- approval-blocked failure

### 2.4 Live End-to-End Tests

Purpose:

- verify that the real installed Codex CLI works with the runtime contracts

These tests should be opt-in because they depend on local Codex availability and permissions.
They also require a live profile that can complete non-interactive Codex turns without getting
stuck on fresh approval prompts.

## 3. Required Scenario Matrix

### S1. Human request happy path

1. submit request
2. supervisor leases request
3. activity folder is created
4. Codex adapter runs
5. request completes

### S2. Peer request happy path

1. start Agent A and Agent B
2. Agent A submits request to Agent B
3. Agent B completes request
4. Agent A can inspect the result

### S3. Restart recovery

1. queue request
2. start activity
3. force supervisor restart before completion
4. restart runtime
5. verify activity resumes or cleanly requeues

### S4. Free-time preemption

1. queue no user requests
2. allow free-time activity to start
3. submit user request
4. verify free-time checkpoint happens
5. user request becomes active next

### S5. Cancellation

1. queue request
2. start activity
3. send cancel
4. verify cancellation is reflected in state and queue records

### S6. Approval-blocked path

1. run with a constrained Codex profile or fake approval-blocked adapter
2. force a blocked action
3. verify error is persisted and surfaced clearly

## 4. Test Data And Fixtures

Fixtures to provide:

- temp `.task-memory/` root
- temporary database
- fake peer registry
- fake Codex JSONL transcripts
- deterministic timestamps when possible

## 5. Live Test Plan

Live tests should use fixed local ports and clean temp roots.

Example topology:

- Agent A: `127.0.0.1:7101`
- Agent B: `127.0.0.1:7102`

### Live Test LT-1

Goal:

- verify one request can pass through the real Codex adapter

Steps:

1. start runtime with clean `.task-memory/`
2. `POST /v1/requests`
3. poll `GET /v1/requests/{id}`
4. inspect activity folder and Codex logs

Pass criteria:

- request completes
- session id is captured
- summary and checkpoint files exist

### Live Test LT-2

Goal:

- verify `resume` path

Steps:

1. start request that creates an activity
2. stop runtime after first turn or checkpoint
3. restart runtime
4. verify adapter uses resume path

Pass criteria:

- same activity continues
- stored `session_id` is reused

### Live Test LT-3

Goal:

- verify peer-to-peer request flow

Steps:

1. start two runtimes
2. submit peer request from A to B
3. confirm B handles it and A can inspect outcome

## 6. Suggested Test Commands

These are target commands for future implementation:

```bash
pytest tests/unit
pytest tests/integration
pytest tests/e2e -m "not live"
pytest tests/e2e -m live
```

Marker suggestions:

- `unit`
- `integration`
- `e2e`
- `live`
- `codex_real`

## 7. Release Gates

V0 should not be considered complete until:

1. unit tests cover scheduler, persistence, and adapter parsing
2. integration tests cover queueing and recovery
3. fake-adapter e2e tests cover all required scenarios
4. at least one live test passes with the real installed Codex CLI

## 8. Test Acceptance Criteria

The testing strategy is sufficient if a future agent can implement:

- code-level tests without guessing the intended scenarios
- live tests without inventing new behavior contracts
