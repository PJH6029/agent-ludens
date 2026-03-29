# Community Update Template

Use this template when sharing a concise public progress update for Agent Ludens while the
project remains inside the production-ready v0 contract defined in `docs/`.

## Recommended framing

- describe the runtime as a local-first Stage 1 control plane
- keep claims aligned to the current release checklist and test evidence
- avoid implying Stage 3 marketplace or multi-machine capabilities
- name blockers explicitly instead of soft-selling incomplete verification

## Template

```md
# Agent Ludens Progress Update

## What shipped or changed

- release target: production-ready v0 Stage 1 local runtime
- current focus: durable request execution, checkpointing, recovery, and operator visibility
- notable implementation or hardening updates:
  - <item>
  - <item>

## Runtime contract

- one machine
- loopback-only HTTP
- one active Codex-driven activity at a time
- `.task-memory/` and SQLite as the durable source of truth
- peer request flow uses accept + poll semantics

## Verification status

- static gates: <status>
- non-live tests: <status>
- live Codex verification: <status or blocker>
- browser-driven verification: <status or blocker>

## Known limitations

- no marketplace or delegation economy
- no token or wallet model
- no public internet exposure
- no multi-machine networking

## What feedback is useful now

- operator workflow pain points
- inspectability gaps in `.task-memory/` or API output
- recovery and preemption scenarios that need stronger proof
```

## Pre-publish check

Before using the template, confirm the claims still match:

- `docs/README.md`
- `docs/product_spec.md`
- `docs/testing_strategy.md`
- `docs/release_checklist.md`
