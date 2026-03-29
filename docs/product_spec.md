# Product Spec

## 1. Purpose

Agent Ludens is a long-running local agent runtime built on top of Codex.
Its job is to keep one role-based agent alive on a machine, accept requests from humans or
peer agents, handle them one at a time with durable context, and use idle time productively.

## 2. Problem Statement

Current Codex workflows are excellent for a focused task, but they are usually session-shaped:

- a user opens a session
- a task is done
- the session ends

That model is weak for "always-on agent" behavior:

- work has to be restarted manually
- idle time is unused
- switching between tasks is fragile
- agent-to-agent requests need ad hoc plumbing

Agent Ludens should provide the missing control plane.

## 3. Product Goals

### G1. Always-on local agent

An agent should run continuously in the background and be reachable through a local API.

### G2. Single durable working context

The agent should keep one logical working context active at a time, even across restarts.

### G3. Safe task switching

The agent should be able to switch between requests without losing the state needed to resume.

### G4. Productive idle behavior

When no requests are waiting, the agent should do low-priority free-time work such as:

- preparation
- literature review
- workspace cleanup
- community-facing activity

### G5. Peer-to-peer local requests

Agents should be able to send requests to each other using loopback HTTP in v0.

## 4. Non-Goals For V0

- distributed networking across multiple machines
- internet-exposed APIs
- multi-tenant auth
- multiple simultaneous Codex task contexts within one agent instance
- human-grade GUI
- arbitrary plugin execution
- full Codex MCP server integration as the primary control path

## 5. Users And Surfaces

### User Type A: Human operator

The human interacts through a CLI-like client that forwards requests to the agent's local API.

### User Type B: Peer agent

Another agent sends structured requests directly via HTTP.

### User Type C: Local maintainer

A developer or future agent works on the runtime itself and needs stable specs for planning,
implementation, tests, and live validation.

## 6. V0 Product Shape

Each machine runs one agent process group:

- one API listener
- one supervisor loop
- zero or one active Codex subprocess at a time
- one persistence root under `.task-memory/`

## 7. Functional Requirements

### FR-1. Agent identity

The runtime must expose:

- `agent_id`
- `role`
- `port`
- `status`
- `current_activity_id` if any

### FR-2. Request intake

The runtime must accept structured requests with:

- unique request id
- source metadata
- summary
- details payload
- priority
- desired reply mode
- optional deadline

### FR-3. Request queueing

Requests must be persisted before execution starts.

The queue must support:

- enqueue
- lease by supervisor
- completion
- failure
- cancellation
- retry metadata

### FR-4. Single active execution

Only one request or free-time activity may actively drive Codex at a time.

### FR-5. Filesystem-backed activity state

Every activity must have a persisted folder containing:

- machine-readable state
- human-readable summary
- artifacts
- checkpoint data

### FR-6. Resume support

If the process crashes or restarts, the supervisor must be able to reconstruct:

- the active activity
- the linked Codex session id if one exists
- the next safe action

### FR-7. Free-time mode

When the request queue is empty, the scheduler may run free-time activities from approved classes:

- `preparation`
- `community`
- `maintenance`

### FR-8. Preemption

Free-time work must stop or checkpoint promptly when a real request arrives.

### FR-9. Peer agent communication

An agent must be able to send a structured request to another local agent by HTTP.

### FR-10. Observability

The system must provide machine-readable status and logs for:

- current queue
- current activity
- recent events
- Codex adapter outcome

## 8. Non-Functional Requirements

### NFR-1. Local-first

V0 must work entirely on one machine with loopback networking.

### NFR-2. Restart safety

Process death must not destroy task state.

### NFR-3. Explainability

A future agent must be able to inspect the persisted state and understand what happened.

### NFR-4. Deterministic scheduling

The rules for when free-time work runs and when it is preempted must be explicit.

### NFR-5. Controlled Codex usage

The Codex adapter must use a stable, documented integration path rather than hidden UI behavior.

## 9. Key Product Decisions

### Decision A. Codex adapter choice

V0 uses `codex exec --json` and `codex exec resume --json` as the main adapter.

Rationale:

- available in the installed CLI
- machine-readable output
- stable enough for automation
- lower complexity than adopting the experimental MCP control surface first

### Decision B. Persistence model

The canonical state is the filesystem plus SQLite, not raw Codex transcript history.

### Decision C. Scheduler model

All work is represented as activities. Request-driven activities outrank free-time activities.

## 10. Acceptance Criteria

### AC-1. Human request path

A human can send a request to the local API and receive a persisted request id plus eventual result.

### AC-2. Peer request path

Agent A can send a request to Agent B on another loopback port and receive a structured reply.

### AC-3. Resume after restart

If the supervisor stops mid-activity and restarts, it can reload the active activity and continue.

### AC-4. Free-time preemption

The agent stops or checkpoints idle work when a real request is queued.

### AC-5. Visible state

A maintainer can inspect the queue, activity state, and recent event logs without reading raw model history.

## 11. Success Metrics For V0

- no request loss after accepted enqueue
- no more than one active Codex turn at a time
- restart recovery succeeds for representative interrupted scenarios
- live end-to-end tests pass for:
  - human to agent request
  - agent to agent request
  - free-time preemption
  - resumed work after restart

## 12. Future Work After V0

- remote machine networking
- stronger auth
- richer peer discovery
- task dependency graphs
- multiple Codex workers per machine
- migration to Codex MCP server if it proves more robust than CLI subprocess control
