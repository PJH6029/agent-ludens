# Persistence And Context

## 1. Principle

Codex context is disposable cache.
Filesystem state is the durable truth.

All information required for task switching and restart recovery must be persisted under
`.task-memory/`.

## 2. Root Layout

Recommended v0 layout:

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
```

## 3. Activity Folder Contract

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

### 3.1 `state.json`

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

Optional fields:

- `deadline`
- `assigned_peer`
- `result_ref`
- `error_ref`

### 3.2 `summary.md`

Human-readable compact summary for restart and inspection.

Must answer:

- what this activity is
- why it exists
- what is done
- what remains
- what the next turn should do

### 3.3 `checkpoint.json`

Compact restart payload.

Recommended fields:

- `objective`
- `current_plan`
- `completed_steps`
- `pending_steps`
- `important_files`
- `known_constraints`
- `next_prompt_seed`

### 3.4 `inbox.md`

Chronological notes or incoming context relevant to the activity.

This is a compact working ledger, not a raw chat transcript.

## 4. Queue Store

`requests.sqlite` is the queue and index database.

Recommended tables:

- `requests`
- `request_events`
- `activities`
- `activity_requests`
- `peers`

### 4.1 `requests` table

Recommended columns:

- `request_id TEXT PRIMARY KEY`
- `status TEXT NOT NULL`
- `kind TEXT NOT NULL`
- `priority INTEGER NOT NULL`
- `source_json TEXT NOT NULL`
- `summary TEXT NOT NULL`
- `details_json TEXT NOT NULL`
- `reply_json TEXT`
- `namespace_hint TEXT`
- `activity_id TEXT`
- `lease_owner TEXT`
- `leased_until TEXT`
- `idempotency_key TEXT`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

### 4.2 `activities` table

Recommended columns:

- `activity_id TEXT PRIMARY KEY`
- `kind TEXT NOT NULL`
- `namespace TEXT NOT NULL`
- `status TEXT NOT NULL`
- `session_id TEXT`
- `folder_path TEXT NOT NULL`
- `summary_path TEXT NOT NULL`
- `checkpoint_path TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

## 5. Session Mapping

`session_map.json` is a convenience index from activity to Codex session.

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

The database may also store this. The JSON file exists for quick inspection and recovery.

## 6. Prompt Header Contract

Every Codex turn should be built from persisted state rather than from a full raw transcript.

The fixed header should contain:

- agent identity and role
- current queue summary
- current activity objective
- compact progress summary
- pending next steps
- important constraints
- file locations for durable state

Detailed runtime construction rules are defined in [Runtime Loop](./runtime_loop.md).

## 7. What Must Not Be Canonical

These may exist, but are not the source of truth:

- transient in-memory scheduler state
- raw stdout of prior Codex runs
- ad hoc notes outside `.task-memory/`
- human memory of what happened previously

## 8. Recovery Rules

On restart, the runtime must reconstruct state in this order:

1. queue database
2. activity folders
3. session map
4. latest Codex JSONL logs if needed for diagnosis

If these disagree, the order above wins unless a later source contains a newer timestamp and a
clearly more complete state.

## 9. Persistence Acceptance Criteria

The persistence model is correct if:

1. an accepted request survives process restart
2. an incomplete activity can be resumed from files alone
3. a maintainer can inspect one activity folder and understand the next action
4. free-time and request-driven activities use the same durable model
