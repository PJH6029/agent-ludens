# Implementation Plan

## 1. Delivery philosophy

Build production-ready v0 in small vertical slices and keep the contract limited to the
Stage 1 local runtime. The goal is to finish a shippable local control plane before adding
any Stage 2/3 product work.

Guiding rules:

- docs must match the shippable product
- prefer deletion and clarification over roadmap ambiguity
- encode invariants in tests before hardening risky runtime behavior
- keep release gates explicit and repeatable

## 2. Normative Stage 1 milestones

These milestones define the production-ready v0 scope.

### M0. Project skeleton

Deliverables:

- package layout
- app entrypoints
- config loading
- logging/test harness bootstrap

Exit criteria:

- runtime starts
- `GET /healthz` works
- tests boot

### M1. Durable request queue

Deliverables:

- SQLite schema
- request insertion
- queue inspection
- request status transitions
- idempotent insert behavior

Exit criteria:

- requests persist across restart
- queue ordering is test-covered

### M2. Activity persistence

Deliverables:

- activity folder creation
- `state.json`, `summary.md`, `checkpoint.json`, `inbox.md`
- activity table and request-to-activity linkage
- Codex artifact persistence

Exit criteria:

- one accepted request creates one inspectable activity folder

### M3. Supervisor and scheduler

Deliverables:

- single active execution slot
- request leasing
- free-time candidate selection
- checkpoint/requeue transitions

Exit criteria:

- queued requests outrank free-time work
- free-time work runs only when the queue is empty

### M4. Codex CLI adapter

Deliverables:

- `codex exec --json` integration
- `codex exec resume <session_id> --json` integration
- JSONL parsing
- session id extraction
- final message + stderr persistence

Exit criteria:

- a request can complete through the real adapter
- a stored session can resume

### M5. Recovery and lease reclaim

Deliverables:

- boot reconciliation
- interrupted work normalization
- lease expiry/reclaim handling
- session map reuse

Exit criteria:

- restart recovery scenario passes
- expired lease reclaim scenario passes

### M6. Free-time workflow

Deliverables:

- bounded free-time activity generation
- quantum-based yielding
- checkpoint on queued-request arrival

Exit criteria:

- free-time work never blocks queued real requests
- preemption scenario passes

### M7. Hardening and observability

Deliverables:

- supervisor lock / exclusivity
- better error envelopes
- runtime event log and recent-event read surface
- optional local auth token
- release checklist and release-gate evidence

Exit criteria:

- runtime state is inspectable without private internals
- release gates pass with documented commands

## 3. Release phase

Before calling v0 production-ready:

1. run the release gates from [Testing Strategy](./testing_strategy.md)
2. run the operator checklist from [Release Checklist](./release_checklist.md)
3. confirm the docs still describe only Stage 1 scope
4. record live-test evidence or an explicit live blocker

## 4. Deferred roadmap (non-normative)

These ideas remain intentionally deferred after v0 ship.

### Stage 2 — Owner web interface

Potential follow-on work:

- backend/static asset serving for a UI
- live activity feed for owners
- browser task submission surface
- visual event timeline

### Stage 3 — Delegation economy and marketplace

Potential follow-on work:

- agent identity registry
- job board / bidding / assignment flows
- review ledger / reputation
- token or escrow ideas

None of the Stage 2/3 items block production-ready v0.
