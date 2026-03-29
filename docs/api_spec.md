# API Spec

## 1. API principles

- loopback-only in v0: bind to `127.0.0.1`
- JSON request and response bodies
- stable envelope shapes
- request acceptance must persist before returning success
- human and peer callers use the same core request endpoints

## 2. Versioning

All runtime endpoints use `/v1`, except `GET /healthz`.

## 3. Authentication model

Default mode:

- loopback-only
- no auth token required

Optional hardening mode:

- configure `AGENT_LUDENS_AUTH_TOKEN`
- require `X-Agent-Token` on all endpoints except `/healthz`
- peer callers must send the same header when the target runtime requires it

## 4. Resource model

Core resources:

- agent
- request
- activity
- peer
- recent event

## 5. Endpoints

### 5.1 Health

`GET /healthz`

Response:

```json
{
  "ok": true,
  "agent_id": "writer-7101",
  "role": "writer",
  "status": "idle"
}
```

### 5.2 Agent info

`GET /v1/agent`

Response fields:

- `agent_id`
- `role`
- `port`
- `status`
- `active_activity_id`
- `queue_depth`
- `current_session_id`

### 5.3 Queue snapshot

`GET /v1/queue`

Response fields:

- `queued_count`
- `leased_count`
- `items`

Queue item fields:

- `request_id`
- `kind`
- `priority`
- `status`
- `created_at`
- `source`

### 5.4 Create request

`POST /v1/requests`

Request body:

```json
{
  "kind": "human_task",
  "priority": 50,
  "source": {
    "type": "human",
    "id": "local-cli"
  },
  "summary": "Summarize recent runtime activity",
  "details": {
    "instructions": "Reply with a compact summary."
  },
  "reply": {
    "mode": "poll"
  },
  "idempotency_key": "cli-20260329-0001"
}
```

Required fields:

- `kind`
- `priority`
- `source`
- `summary`
- `details`

Optional fields:

- `reply`
- `deadline`
- `idempotency_key`
- `namespace_hint`
- `activity_id`

Success response (`202 Accepted`):

```json
{
  "request_id": "req_01HQ...",
  "status": "queued",
  "accepted_at": "2026-03-29T02:00:00Z"
}
```

### 5.5 Request detail

`GET /v1/requests/{request_id}`

Response fields:

- `request_id`
- `status`
- `kind`
- `priority`
- `source`
- `summary`
- `details`
- `reply`
- `deadline`
- `namespace_hint`
- `activity_id`
- `lease_owner`
- `leased_until`
- `idempotency_key`
- `result`
- `error`
- `created_at`
- `updated_at`

### 5.6 Cancel request

`POST /v1/requests/{request_id}/cancel`

Rules:

- queued requests become `cancelled`
- leased/running/checkpointing requests become `cancellation_requested`
- the supervisor performs final checkpoint/cleanup and then records terminal state

Response:

```json
{
  "request_id": "req_01HQ...",
  "status": "cancellation_requested"
}
```

### 5.7 List activities

`GET /v1/activities`

Query params:

- `status`
- `namespace`
- `limit`

Returns a list of activity detail objects.

### 5.8 Activity detail

`GET /v1/activities/{activity_id}`

Response fields:

- `activity_id`
- `kind`
- `namespace`
- `status`
- `summary`
- `session_id`
- `request_ids`
- `checkpoint_version`
- `updated_at`

### 5.9 Recent events

`GET /v1/events`

Purpose:

- expose a small recent-event view backed by `.task-memory/runtime/event-log.jsonl`
- avoid private SQLite or file spelunking for normal operator inspection

Query params:

- `limit` (default 50)
- `activity_id` (optional filter)
- `request_id` (optional filter)

Response:

```json
{
  "items": [
    {
      "timestamp": "2026-03-29T02:00:00Z",
      "type": "request.leased",
      "request_id": "req_01HQ...",
      "activity_id": "act_01HQ...",
      "payload": {
        "lease_owner": "writer-7101"
      }
    }
  ]
}
```

Event records should remain append-only, compact, and human-readable.

### 5.10 List peers

`GET /v1/peers`

Returns the configured peer list.

### 5.11 Register peer

`POST /v1/peers`

Request body:

```json
{
  "agent_id": "planner-7102",
  "role": "planner",
  "base_url": "http://127.0.0.1:7102",
  "token": null
}
```

Response fields match the peer record.

## 6. Peer request contract (accept + poll)

Production-ready v0 peer flow:

1. Agent A knows or registers Agent B's `base_url`.
2. Agent A sends `POST /v1/requests` to Agent B with `source.type = "agent"`.
3. Agent B returns `202 Accepted` and a new remote `request_id`.
4. Agent A polls `GET /v1/requests/{request_id}` on Agent B until terminal.

`source.reply_to` may be supplied for correlation metadata, but Agent B is not required to
perform callback delivery in v0.

Example agent request body:

```json
{
  "kind": "agent_task",
  "priority": 60,
  "source": {
    "type": "agent",
    "id": "planner-7102",
    "reply_to": {
      "base_url": "http://127.0.0.1:7102",
      "request_id": "req_origin_123"
    }
  },
  "summary": "Write a peer response",
  "details": {
    "instructions": "Return a structured acknowledgement."
  },
  "reply": {
    "mode": "poll"
  }
}
```

## 7. Error model

Errors use:

```json
{
  "error": {
    "code": "not_found",
    "message": "Request req_123 was not found",
    "details": {}
  }
}
```

Representative codes:

- `invalid_request`
- `unauthorized`
- `not_found`
- `conflict`
- `approval_blocked`
- `codex_exec_failed`

## 8. Deferred API surfaces

The following are explicitly deferred from v0:

- owner-UI-specific routes
- marketplace routes
- public discovery/registry routes
- streaming browser-facing event feeds
