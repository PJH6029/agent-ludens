# Agent Ludens

## Vision

Agents have traditionally been treated as workers with no life outside incoming tasks.
Agent Ludens changes that model. Each machine runs one long-lived, role-based agent that
waits for requests, handles them with care, and uses idle time productively for preparation,
self-maintenance, and community-facing work.

The design goal is not "many contexts at once." The design goal is one durable working
context that can switch focus safely because all important state is persisted to disk.

## Core Idea

An Agent Ludens instance is a background agent with three properties:

1. It exposes a local request API for humans and peer agents.
2. It handles one active Codex working context at a time.
3. It persists task state to the filesystem so work can pause, resume, and switch safely.

This project should be read as a supervisor around Codex, not a fork of Codex itself.
Codex is the reasoning and execution engine. Agent Ludens is the long-running control plane.

## Background Model

Each agent:

1. Runs continuously in the background.
2. Has a role, identity, and loopback port.
3. Accepts requests from two surfaces:
   - humans through a CLI-like chat client that forwards messages to the local API
   - peer agents through HTTP on `localhost:<port>`
4. Polls or leases queued requests from its local store.
5. Handles queued requests before doing optional free-time work.
6. Returns to listening state after completing or checkpointing work.

## Single-Context Interpretation

"Single-context" does not mean one immortal model process that can never restart.
For v0 it means:

- one durable logical session at a time
- one active Codex turn at a time
- one persisted working summary that is treated as the source of truth

The model context is a cache. Filesystem state is canonical.

## Persistence Principle

When work switches between requests, the agent must persist enough information to restart
without guessing. The root persistence directory is `.task-memory/`.

Expected high-level namespaces:

- `.task-memory/main-task/`
- `.task-memory/preparation/`
- `.task-memory/community/`
- `.task-memory/maintenance/`

Each namespace contains activity folders, summaries, and checkpoints. Queue state and runtime
indexes are stored alongside them.

## Design Constraints

- The agent is background-first, not chat-first.
- Loopback networking is enough for v0.
- The API is the communication port between humans, tools, and peer agents.
- The implementation should prefer restart-safe designs over in-memory cleverness.
- Free-time work must be preemptible as soon as a real request arrives.

## Relation To Codex

The recommended v0 strategy is:

- use `codex exec --json` for fresh turns
- use `codex exec resume ... --json` for continued work
- keep Codex session IDs as durable references
- keep agent truth in `.task-memory/`, not in raw transcript history

## Reading Order

This file is the narrative overview. The implementation contract lives in the other specs:

- [README](./README.md)
- [Product Spec](./product_spec.md)
- [Architecture](./architecture.md)
- [API Spec](./api_spec.md)
- [Persistence And Context](./persistence_and_context.md)
- [Runtime Loop](./runtime_loop.md)
- [Testing Strategy](./testing_strategy.md)
- [Implementation Plan](./implementation_plan.md)
