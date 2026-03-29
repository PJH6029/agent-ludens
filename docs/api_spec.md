# API Spec

## 1. API Principles

- Loopback-only in v0: bind to `127.0.0.1`
- JSON request and response bodies
- Stable envelope shapes
- Request acceptance must persist before returning success

## 2. Versioning

All runtime endpoints use `/v1`.

## 3. Authentication Model For V0

Default mode:

- loopback-only
- no mandatory auth for local development

Optional hardening mode:

- require `X-Agent-Token`
- configure token from environment or local config file

The implementation should support both modes without changing endpoint shapes.

## 4. Resource Model

Core resources:

- agent
- request
- activity
- peer
- queue

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

### 5.2 Agent Info

`GET /v1/agent`

Response fields:

- `agent_id`
- `role`
- `port`
- `status`
- `active_activity_id`
- `queue_depth`
- `current_session_id`

### 5.3 Queue Snapshot

`GET /v1/queue`

Response fields:

- `queued_count`
- `leased_count`
- `items`

Each item summary:

- `request_id`
- `kind`
- `priority`
- `status`
- `created_at`
- `source`

### 5.4 Create Request

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
  "summary": "Summarize recent literature on memory agents",
  "details": {
    "instructions": "Prepare a short background memo for future work."
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

Success response:

```json
{
  "request_id": "req_01HQ...",
  "status": "queued",
  "accepted_at": "2026-03-29T02:00:00Z"
}
```

### 5.5 Request Detail

`GET /v1/requests/{request_id}`

Response fields:

- `request_id`
- `status`
- `kind`
- `priority`
- `source`
- `summary`
- `details`
- `activity_id`
- `result`
- `error`
- `created_at`
- `updated_at`

### 5.6 Cancel Request

`POST /v1/requests/{request_id}/cancel`

Rules:

- queued requests become `cancelled`
- leased or running requests become `cancellation_requested`
- the supervisor performs the actual stop or checkpoint

Response:

```json
{
  "request_id": "req_01HQ...",
  "status": "cancellation_requested"
}
```

### 5.7 List Activities

`GET /v1/activities`

Query params:

- `status`
- `namespace`
- `limit`

### 5.8 Activity Detail

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

### 5.9 List Peers

`GET /v1/peers`

Returns the configured peer list known to this agent.

### 5.10 Register Peer

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

This endpoint is optional in v0 if peers are file-configured. If implemented, it should persist
the peer list locally.

### 5.11 Send Peer Request

This is not a public endpoint shape difference. Peer-to-peer requests use the same
`POST /v1/requests` contract as human requests, with a different `source.type`.

Peer source example:

```json
{
  "type": "agent",
  "id": "planner-7102",
  "reply_to": {
    "base_url": "http://127.0.0.1:7102",
    "request_id": "req_origin_123"
  }
}
```

## 6. Schema Definitions

### 6.1 Request Status

Allowed values:

- `queued`
- `leased`
- `running`
- `checkpointing`
- `completed`
- `failed`
- `cancelled`
- `cancellation_requested`

### 6.2 Priority

Integer range:

- `0` to `100`

Suggested bands:

- `80-100`: urgent
- `50-79`: normal request
- `20-49`: background but user-visible
- `0-19`: free-time work

### 6.3 Request Kind

Suggested v0 values:

- `human_task`
- `agent_task`
- `preparation_task`
- `community_task`
- `maintenance_task`

## 7. Error Envelope

All non-2xx responses use:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "priority must be between 0 and 100",
    "details": {}
  }
}
```

Recommended error codes:

- `invalid_request`
- `not_found`
- `conflict`
- `unauthorized`
- `unavailable`
- `internal_error`

## 8. Idempotency Rules

If `idempotency_key` is provided, the server should:

- return the original accepted request if the payload is equivalent
- reject with `conflict` if the same key is reused with meaningfully different payload

## 9. Streaming

Do not introduce SSE or WebSocket APIs in v0.

Polling is enough for v0 and keeps the runtime simpler.

## 10. API Acceptance Criteria

The API is correct for v0 if:

1. requests are durable before acknowledgment
2. request status can be inspected externally
3. peer agents can submit the same request envelope humans use
4. cancellation and activity inspection work without reading raw local files
