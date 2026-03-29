# Runtime Loop

## 1. Runtime contract

The runtime owns one active working slot. At any given time it is in one of these high-level
states:

- `boot`
- `idle`
- `handling_request`
- `checkpointing`
- `free_time`
- `error_backoff`

## 2. Boot and recovery sequence

On startup the runtime must:

1. ensure `.task-memory/` layout exists
2. acquire the supervisor lock
3. open the SQLite store
4. reconcile interrupted leases and activities
5. write runtime state files
6. start the supervisor loop

Recovery must not assume that any in-memory state survived.

## 3. Lease semantics

Request leasing is part of the runtime contract, not documentation-only language.

Rules:

- leasing writes `lease_owner` and `leased_until = now + TTL`
- only queued or reclaimable requests may be leased
- expired leases are reclaimable on startup and before new lease decisions
- request detail must expose lease metadata
- tests must prove reclaim behavior

## 4. Scheduling rules

### 4.1 Priority order

1. queued request work that already has a persisted activity/checkpoint
2. newly queued requests ordered by priority then creation time
3. free-time activities when the queue is empty

### 4.2 Free-time eligibility

Free-time may run only when:

- no queued request exists
- no cancellation needs immediate handling
- the supervisor is healthy and owns the lock

### 4.3 Free-time quanta

Free-time work runs one Codex turn at a time. After each turn the scheduler must re-check
the queue before continuing.

## 5. Request execution flow

For a leased request, the runtime should:

1. reuse an existing `activity_id` if one is already linked
2. otherwise create a new activity scaffold
3. mark the request running and the activity active
4. build the prompt header from persisted state
5. choose `exec` vs `resume` based on `session_id`
6. persist Codex artifacts and update session mapping
7. finalize the request as completed, failed, cancelled, or requeued

## 6. Prompt construction

Each turn prompt has two parts:

1. fixed header generated from persisted state
2. turn-specific instruction for request work or one free-time quantum

The fixed header must stay compact and reproducible from the persistence layer alone.

## 7. Checkpoint policy

Checkpoint at least:

- before switching activities
- before shutdown
- after each meaningful turn
- after recoverable failures
- before yielding a free-time activity back to queued work

Checkpoints must be sufficient for a new process to continue without reading full history.

## 8. Cancellation and preemption

### 8.1 Request cancellation

If a queued request is cancelled, it becomes terminal immediately.

If an active request is cancelled:

- record `cancellation_requested`
- interrupt or safely finish the active turn as appropriate
- write final checkpoint/summary state
- mark the request terminal

### 8.2 Free-time preemption

If a real request appears while free-time work is running:

1. finish or safely interrupt the current quantum boundary
2. checkpoint the free-time activity
3. mark it pending
4. release the working slot
5. process the queued request next

Request-driven work is not otherwise preempted in v0.

## 9. Error handling

### 9.1 Codex subprocess failure

If Codex exits non-zero:

- persist JSONL/stderr/exit metadata
- classify the error when possible (`approval_blocked`, recoverable failure, generic exec failure)
- requeue only when the failure is explicitly recoverable
- otherwise persist terminal failure state

### 9.2 Approval-blocked behavior

Production-ready v0 must surface approval-blocked failures clearly in request state,
activity summary, and diagnostics.

## 10. Event logging

The runtime must append compact events to `.task-memory/runtime/event-log.jsonl` for
scheduling, recovery, request lifecycle, and checkpoint behavior. The read-only API event
surface may be derived directly from that log.

## 11. Shutdown behavior

On graceful shutdown the runtime must:

1. stop accepting new work or mark itself draining
2. checkpoint any active work
3. flush runtime state and event logs
4. release the supervisor lock

On ungraceful shutdown, restart recovery must infer incomplete work from persisted state.

## 12. Runtime acceptance criteria

The runtime loop is correct if:

1. only one activity owns the Codex slot at a time
2. lease reclaim works after interruption
3. free-time work yields to queued work at quantum boundaries
4. restart recovery can resume or safely requeue persisted work
5. prompt headers can be rebuilt from files alone
6. recent events are inspectable through the documented file/API surfaces
