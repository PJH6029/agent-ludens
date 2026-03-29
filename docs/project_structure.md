# Project Structure

Agent Ludens is a **background-first local control plane around Codex**.
It is not a web app, not a distributed platform, and not a marketplace in v0.

## Core idea

One machine runs one long-lived role-based agent runtime that:

1. exposes a loopback-only HTTP API
2. persists queue and activity state durably
3. runs one active Codex-driven activity at a time
4. uses idle time for bounded free-time work
5. can accept structured requests from humans or peer agents

The design goal is **one durable logical working context**, not many concurrent model
sessions. Filesystem and SQLite state make task switching safe; model context is cache.

## Runtime surfaces

### Human operator surface

Production-ready v0 is **API-first**. Operators may use:

- `curl`
- `httpx` or another HTTP client
- tests or local scripts
- a future thin wrapper, if added later

A dedicated owner web UI is deferred.

### Peer surface

Peer agents communicate over loopback HTTP. In v0 the supported interaction is:

1. submit request to another runtime
2. receive `202 Accepted` with remote `request_id`
3. poll `GET /v1/requests/{request_id}` on the remote runtime until terminal

`source.reply_to` is correlation metadata, not a required callback transport.

## Persistence layout

All durable state lives under `.task-memory/`.

High-level namespaces:

- `.task-memory/runtime/`
- `.task-memory/main-task/`
- `.task-memory/preparation/`
- `.task-memory/community/`
- `.task-memory/maintenance/`
- `.task-memory/codex/`
- `.task-memory/peers/`

Queue state and indexes live in SQLite. Activity folders hold the restart-safe human and
machine summaries for each unit of work.

## Process model

Production-ready v0 targets one Python runtime with two long-lived concerns:

- the FastAPI listener
- the supervisor loop

A local supervisor lock must prevent two runtimes from owning the same `.task-memory/`
root at once.

## Relation to Codex

The Codex CLI is the primary automation backend in v0:

- fresh turn: `codex exec --json <prompt>`
- resume turn: `codex exec resume <session_id> --json <prompt>`

Agent Ludens owns scheduling, persistence, recovery, and observability. Codex owns the
individual reasoning/execution turn.

## Deferred roadmap

The following remain visible but **non-normative** for v0:

- Stage 2 owner web interface
- Stage 3 marketplace / delegation economy / token ideas
- multi-machine or internet-facing deployment

For the normative contract, continue with [Product Spec](./product_spec.md).
