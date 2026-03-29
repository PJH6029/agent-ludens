# Persistence And Context

## 1. Principle

Codex context is disposable cache. Filesystem and SQLite state are the durable truth.
Everything required for restart recovery, inspection, or task switching must be persisted.

## 2. Root layout

Production-ready v0 uses this canonical layout:

```text
.task-memory/
  requests.sqlite
  session_map.json
  runtime/
    agent_state.json
    scheduler_state.json
    supervisor.lock
    event-log.jsonl
  main-task/
    <activity_id>/
  preparation/
    <activity_id>/
  community/
    <activity_id>/
  maintenance/
    <activity_id>/
  peers/
    peers.json
  codex/
    <activity_id>/
      latest.jsonl
      last_message.txt
      stderr.log
      metadata.json
```

## 3. Canonical sources

Canonical state, in priority order:

1. SQLite request/activity rows
2. activity folders under `.task-memory/`
3. `session_map.json`
4. Codex JSONL/stderr artifacts for diagnosis

Raw chat history or ad hoc notes outside `.task-memory/` are not canonical.

## 4. Activity folder contract

Each activity folder must contain:

```text
<activity_id>/
  state.json
  summary.md
  checkpoint.json
  inbox.md
  artifacts/
  logs/
```

### 4.1 `state.json`

Machine-readable activity state.

Required fields:

- `activity_id`
- `kind`
- `namespace`
- `status`
- `request_ids`
- `session_id`
- `checkpoint_version`
- `created_at`
- `updated_at`

### 4.2 `summary.md`

Human-readable compact summary.

It must answer:

- what this activity is
- why it exists
- what is done
- what remains
- what the next turn should do

### 4.3 `checkpoint.json`

Compact restart payload.

Required or strongly expected fields:

- `objective`
- `current_plan`
- `completed_steps`
- `pending_steps`
- `important_files`
- `known_constraints`
- `next_prompt_seed`

### 4.4 `inbox.md`

Compact chronological notes relevant to the activity. This is a working ledger, not a raw
chat transcript.

## 5. Runtime state files

`.task-memory/runtime/` must provide:

- `agent_state.json` — current runtime identity/status/session summary
- `scheduler_state.json` — queue depth + currently scheduled request summary
- `supervisor.lock` — exclusive runtime ownership marker
- `event-log.jsonl` — append-only recent event stream for operator inspection

## 6. Codex artifact contract

`.task-memory/codex/<activity_id>/` must persist:

- `latest.jsonl` — raw Codex JSONL stream for the latest turn
- `last_message.txt` — extracted final assistant message
- `stderr.log` — subprocess stderr
- `metadata.json` — at least `exit_code` and last update time

## 7. Queue store contract

`requests.sqlite` is the durable request/activity index.

Required tables:

- `requests`
- `request_events`
- `activities`
- `activity_requests`
- `peers`

### 7.1 Requests table responsibilities

Must support storage for:

- request identity and status
- source/reply/details payloads
- `activity_id`
- `lease_owner`
- `leased_until`
- `idempotency_key`
- result and error payloads
- created/updated timestamps

### 7.2 Activities table responsibilities

Must support storage for:

- activity identity and namespace
- activity status
- `session_id`
- filesystem paths for summary/checkpoint folders
- checkpoint version
- created/updated timestamps

## 8. Session mapping

`session_map.json` is a convenience index from activity to Codex session id.

Example:

```json
{
  "activities": {
    "act_abc123": {
      "session_id": "7f9f9a2e-1b3c-4c7a-9b0e-aaaa",
      "last_used_at": "2026-03-29T02:10:00Z"
    }
  }
}
```

## 9. Prompt header contract

Every Codex turn prompt must be regenerated from persisted state rather than from a raw
transcript. The header should include:

- agent identity and role
- current queue summary
- active activity objective
- compact progress summary
- pending next steps
- important constraints
- durable state file locations

## 10. Recovery rules

On restart, recovery should consult the canonical sources in order and normalize interrupted
work. If sources disagree, prefer the newer and more complete persisted state, not memory.

## 11. Persistence acceptance criteria

The persistence model is correct if:

1. accepted requests survive restart
2. incomplete activities can be resumed from files alone
3. a maintainer can inspect one activity folder and understand the next action
4. request-driven and free-time activities share the same durable model
5. runtime events and status are inspectable without chat history
