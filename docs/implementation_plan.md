# Implementation Plan

## 1. Delivery Philosophy

Build the control plane in small vertical slices.
Each milestone should leave the project in a runnable and testable state.

## 2. Milestones

### M0. Project skeleton

Deliverables:

- Python package layout
- app entrypoints
- config loading
- logging setup
- test harness

Exit criteria:

- runtime starts
- `GET /healthz` works
- test suite bootstraps

### M1. Durable request queue

Deliverables:

- SQLite schema
- request insertion
- queue inspection
- request status transitions

Exit criteria:

- requests persist across restart
- idempotent request insertion works

### M2. Activity persistence

Deliverables:

- activity folder creation
- `state.json`, `summary.md`, `checkpoint.json`
- activity table and request-to-activity linking

Exit criteria:

- one accepted request can produce one activity folder with valid files

### M3. Supervisor and scheduler

Deliverables:

- single active execution slot
- request leasing
- free-time candidate selection
- state transitions for running and checkpointing

Exit criteria:

- queued requests are processed in priority order
- free-time work does not run when requests are queued

### M4. Codex CLI adapter

Deliverables:

- `codex exec --json` integration
- `codex exec resume --json` integration
- JSONL event parser
- session id extraction
- last-message extraction

Exit criteria:

- a request can complete through the real adapter
- an existing activity can resume

### M5. Recovery and restart

Deliverables:

- supervisor boot reconciliation
- incomplete activity recovery
- lease cleanup
- persisted session map

Exit criteria:

- restart recovery scenario passes

### M6. Peer-to-peer requests

Deliverables:

- peer registry
- outbound peer client
- source and reply metadata propagation

Exit criteria:

- one agent can request work from another local agent

### M7. Free-time workflow

Deliverables:

- free-time activity generation
- preemption checkpoints
- configurable free-time categories

Exit criteria:

- free-time work runs only when the queue is empty
- preemption scenario passes

### M8. Hardening and observability

Deliverables:

- better error envelopes
- event JSONL
- status endpoints
- optional local auth token

Exit criteria:

- operational state is inspectable without reading private internals

## 3. Recommended Build Order

Recommended order:

1. M0
2. M1
3. M2
4. M3
5. M4
6. M5
7. M6
8. M7
9. M8

Do not start peer-to-peer work before the local single-agent path is stable.

## 4. Implementation Guidance For Future Agents

### 4.1 Prefer adapter abstraction early

Define a `CodexAdapter` interface before implementing the real CLI adapter.
This makes the fake adapter easy to use in tests.

### 4.2 Keep queue and activity writes explicit

Avoid hidden side effects. State transitions should be easy to audit in code and tests.

### 4.3 Make summaries first-class

The project depends on compact persisted summaries, so do not treat them as optional extras.

### 4.4 Keep free-time work simple in v0

Do not over-design preparation and community logic initially.
Represent them as ordinary low-priority activities with strict preemption.

## 5. Milestone Acceptance Map

- [Product Spec](./product_spec.md) defines the product-level acceptance criteria.
- [API Spec](./api_spec.md) defines endpoint contracts.
- [Persistence And Context](./persistence_and_context.md) defines durable-state requirements.
- [Runtime Loop](./runtime_loop.md) defines scheduler and adapter behavior.
- [Testing Strategy](./testing_strategy.md) defines the minimum verification bar.

## 6. Definition Of Done For V0

V0 is done when:

1. the local human request path works
2. activity persistence and resume work
3. peer request flow works on loopback
4. free-time work is preemptible
5. unit, integration, and fake-adapter e2e tests pass
6. at least one real live Codex test passes
