# Free-Time Maintenance

This document defines safe, low-priority work for one free-time quantum in the Stage 1 runtime.

Use it when the queue is empty and the scheduler selects maintenance work.

## Goals

A free-time maintenance turn should improve operator clarity, release readiness, or project
communication without changing the Stage 1 product boundary.

Good outcomes for one quantum:

- tighten or add documentation that clarifies an existing contract
- prepare release evidence or checklists without claiming unverified results
- draft community-facing notes that reflect already-decided scope
- record small maintenance observations for future request-driven work

## Safety rules

Each maintenance quantum must stay inside these limits:

- no destructive actions
- no approval-requiring actions
- no dependency on hidden chat history
- no changes that assume Stage 2 or Stage 3 scope
- no long-running migrations or broad refactors
- no interruption of queued or active request work

If a task would need operator input, network access, or a broad product decision, stop at
preparation notes instead of forcing execution.

## Preferred maintenance task types

Choose one small task from this list:

1. Docs alignment

- add or refine a doc that clarifies existing runtime, API, persistence, or release behavior
- capture an ambiguity as an explicit deferred item instead of leaving it implicit

2. Release preparation

- prepare a checklist, evidence template, or operator note for an existing release gate
- confirm that a release step is documented, while leaving the checkbox unchecked until verified

3. Community-facing preparation

- draft a short update template, changelog seed, or scope note based on current docs
- keep statements factual and limited to the shipped Stage 1 contract

4. Maintenance observations

- record a concise follow-up note about inspectability, testing gaps, or operator ergonomics
- point back to the relevant normative doc instead of inventing new scope

## Completion standard

One quantum is complete when all of the following are true:

- exactly one bounded maintenance task was advanced
- the result is durable on disk
- the result helps a future maintainer without requiring prior chat context
- the activity summary states what was explored or prepared

## Non-goals

Do not use free-time maintenance to:

- implement new product capabilities without a queued request
- silently widen the release target
- rewrite large sections of docs for style alone
- perform cleanup that risks conflicting with in-flight user changes

## Suggested operator check

After a maintenance quantum, a maintainer should be able to answer:

1. What small project artifact improved?
2. Why was it safe to do during idle time?
3. What remains for a request-driven or operator-approved follow-up?
