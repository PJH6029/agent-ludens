# Product Spec

## 1. Purpose

Agent Ludens is a long-running local runtime built on top of Codex. Its job is to keep one
role-based agent alive on one machine, accept structured requests, execute them one at a
time with durable state, and use idle time productively.

## 2. Production-ready v0 boundary

Production-ready v0 is the **Stage 1 local control plane**, now including the **Stage 2 Owner Web Interface**.

Included:

- loopback-only HTTP API
- durable request queue and activity state
- single-slot supervisor and free-time scheduler
- Codex CLI fresh-turn and resume integration
- local peer-to-peer request submission using accept+poll semantics
- release-grade observability and verification gates
- integrated owner web interface and frontend event feed

Deferred:

- marketplace / job board / delegation economy
- token economics
- multi-machine networking or internet exposure

## 3. Problem statement

Raw Codex sessions are excellent for focused work, but they are usually session-shaped:

- a session starts for one task
- the task ends or stalls
- durable runtime state is left to ad hoc notes or memory

Agent Ludens provides the missing control plane for always-on local agent behavior:

- requests survive restarts
- work can be resumed safely
- idle time can be used productively
- peer requests use a documented local contract

## 4. Product goals

### G1. Always-on local agent

The agent runtime should run continuously in the background and be reachable through a
loopback API.

### G2. Single durable working context

The runtime should maintain one logical active activity at a time, even across restarts.

### G3. Safe task switching

The runtime should checkpoint enough state to requeue or resume work without guessing.

### G4. Productive idle behavior

When no real requests are queued, the runtime may spend one quantum on approved
free-time work.

### G5. Peer-to-peer local requests

One local runtime should be able to submit work to another local runtime via HTTP and poll
for the result.

## 5. Users and surfaces

### User A: human operator

Uses HTTP directly or through a thin wrapper to submit, inspect, and cancel work.

### User B: peer agent

Submits a structured request to another runtime and polls for terminal status.

### User C: maintainer / future agent

Inspects docs, `.task-memory/`, and test evidence to understand or extend the runtime.

## 6. Functional requirements

### FR-1. Agent identity and status

The runtime must expose:

- `agent_id`
- `role`
- `port`
- `status`
- `active_activity_id` if any
- `current_session_id` if any
- queue depth summary

### FR-2. Request intake

The runtime must accept structured requests with:

- `kind`
- `priority`
- `source`
- `summary`
- `details`
- optional `reply`, `deadline`, `idempotency_key`, `namespace_hint`, `activity_id`

Request acceptance must persist before the API returns success.

### FR-3. Durable queueing

Requests must be durably persisted in SQLite and support:

- enqueue
- lease
- running
- completion
- failure
- cancellation
- requeue / checkpoint continuation
- idempotent insert by key + payload

### FR-4. Lease semantics

Request leasing must use a real TTL model:

- `leased_until` is written as `now + TTL`
- lease ownership is visible in request detail
- expired leases are reclaimable on startup and before new leasing decisions
- tests prove lease reclaim behavior

### FR-5. Single active execution slot

Only one request-driven or free-time activity may actively drive Codex per runtime.
Supervisor exclusivity must be enforced by a concrete local lock for the selected
`.task-memory/` root.

### FR-6. Filesystem-backed activity state

Every activity must have a folder containing:

- `state.json`
- `summary.md`
- `checkpoint.json`
- `inbox.md`
- `artifacts/`
- `logs/`

### FR-7. Resume and recovery

After shutdown or crash, the supervisor must reconstruct:

- queued and leased request state
- activity state
- stored Codex session id, if any
- next safe action from the persisted checkpoint

### FR-8. Codex adapter

Production-ready v0 uses the Codex CLI as the primary adapter surface:

- `codex exec --json <prompt>`
- `codex exec resume <session_id> --json <prompt>`

The runtime must persist raw JSONL, final message, stderr, exit code, and session id.

### FR-9. Human operator surface

The normative human surface is HTTP-first. A GUI or rich CLI wrapper is not required for
production-ready v0.

### FR-10. Peer request contract

Peer request handling must support **accept + poll** semantics:

1. Agent A submits `POST /v1/requests` to Agent B.
2. Agent B returns `202 Accepted` with a remote `request_id`.
3. Agent A polls `GET /v1/requests/{request_id}` on Agent B until terminal.

`source.reply_to` may be carried for correlation, but callback delivery is not required.

### FR-11. Free-time work

When no real requests are queued, the runtime may run one free-time quantum in one of the
approved namespaces:

- `preparation`
- `community`
- `maintenance`

Free-time work must yield after each quantum so the queue can be re-checked.

### FR-12. Preemption and cancellation

- free-time work must checkpoint and yield promptly when a real request arrives
- request-driven work is only interrupted for cancellation or shutdown in v0
- cancellation status must be visible through the public API and persisted state

### FR-13. Observability

Operators and maintainers must be able to inspect:

- current runtime status
- queued/running request state
- activity summaries and checkpoints
- recent runtime events
- Codex artifacts and stderr

The canonical observability surfaces are the `.task-memory/runtime/` files, activity
folders, and the read-only API endpoints described in [API Spec](./api_spec.md).

## 7. Non-functional requirements

### NFR-1. Local-first

v0 must work entirely on one machine with loopback networking.

### NFR-2. Restart safety

Process death must not destroy accepted requests or the state needed to resume work.

### NFR-3. Explainability

A future agent or maintainer must be able to inspect persisted files and understand what
happened without relying on chat history.

### NFR-4. Explicit scheduling

Queue priority, free-time eligibility, and checkpoint behavior must be documented and
testable.

### NFR-5. Controlled Codex usage

The runtime must use a documented Codex CLI integration path, not hidden UI automation.

### NFR-6. Release proof

Production-ready claims require passing lint, typecheck, non-live tests, and the agreed
live verification path or recording an explicit live-environment blocker.

## 8. Acceptance criteria

Production-ready v0 is complete when all of the following are true:

1. the docs describe one unambiguous Stage 1-only contract
2. loopback request handling, activity persistence, recovery, and peer accept+poll work
3. supervisor exclusivity and lease reclaim behavior are implemented and tested
4. recent runtime state and events are inspectable through documented file/API surfaces
5. the release gates in [Release Checklist](./release_checklist.md) pass or any blocker is
   explicitly documented

## 9. Release posture

Production-ready v0 is **API-first, single-machine, and operator-visible**. It should be
shippable for local use without Stage 3 work.

## 10. Deferred roadmap

Stage 3 ideas remain valuable, but they are follow-on work after v0 ship:

- marketplace / delegation economy
- tokens, wallets, reputation ledger
