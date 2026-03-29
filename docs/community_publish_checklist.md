# Community Publish Checklist

Use this checklist before posting a community-facing update about Agent Ludens.
It is intended for production-ready v0 messaging only and should stay aligned to
the Stage 1 local-runtime contract in `docs/`.

This checklist complements:

- `docs/community_update_template.md`
- `docs/release_checklist.md`
- `docs/release_evidence_template.md`
- `docs/README.md`

## Goal

Prevent public updates from overstating verification status, widening scope, or
mixing implemented experiments with the normative release contract.

## Pre-publish inputs

Confirm these sources exist and are current before drafting:

- the latest release evidence note or draft
- the latest release checklist status
- the current `docs/README.md` scope statement
- any inspected activity artifacts referenced as examples

If any input is missing, publish a narrower status note or defer the update.

## Claim discipline

Only state items that are backed by current evidence:

- current release target
- implemented runtime behaviors already described in `docs/`
- verification steps actually run
- blockers that are concrete and still unresolved
- known limitations that remain inside the documented Stage 1 boundary

Do not claim or imply:

- multi-machine or marketplace behavior
- delegation economy, wallets, or token mechanics
- public internet exposure
- browser or live verification success unless evidence is recorded
- that an item is shipped when it is only planned, drafted, or locally explored

## Required checks

- [ ] update stays within the Stage 1 local-runtime scope
- [ ] wording matches `docs/README.md` and `docs/product_spec.md`
- [ ] verification claims match `docs/release_checklist.md` or recorded blockers
- [ ] any live-test mention includes status as pass, blocked, or not yet run
- [ ] any browser-driven proof mention is backed by saved evidence or a blocker
- [ ] limitations are stated plainly, without roadmap inflation
- [ ] feedback request asks for Stage 1-relevant operator or runtime input

## Safe phrasing patterns

Prefer wording like:

- "current release target"
- "documented runtime contract"
- "verification is still in progress"
- "blocked on live environment prerequisites"
- "feedback is most useful on operator workflow and inspectability"

Avoid wording like:

- "fully shipped platform"
- "production network"
- "browser UI is complete" unless that is explicitly part of the chosen release contract
- "verified" without naming what was verified

## Output rule

A publish-ready update should let a future maintainer answer:

1. what is implemented now
2. what was actually verified
3. what remains blocked or deferred

If those answers are not obvious from the draft, tighten the draft before posting.
