# Scope Alignment Note

This note records a small documentation-preparation finding from a free-time
maintenance turn on March 29, 2026.

## Observed inconsistency

The docs set does not describe the release boundary consistently:

- `README.md` says production-ready v0 is intentionally Stage 1 only, but its
  included-features list also names an integrated Owner Web Interface.
- `docs/README.md` still defines the normative contract as Stage 1 local runtime
  only and says a dedicated owner web UI is deferred.
- `docs/project_structure.md` still says a dedicated owner web UI is deferred.
- `docs/release_checklist.md` still asks maintainers to confirm a Stage 1-only
  release.
- `docs/api_spec.md` still defers owner-UI-specific routes and browser-facing
  event feed surfaces from v0.
- `docs/testing_strategy.md` still says browser/UI tests are deferred because
  those surfaces are not part of production-ready v0.
- `docs/product_spec.md` says production-ready v0 now includes the Stage 2 Owner
  Web Interface.
- `docs/implementation_plan.md` says Stage 2 has since been integrated.

## Repo evidence checked in this turn

The current code and assets support a shipped local UI surface:

- `src/agent_ludens/app.py` mounts `StaticFiles` at `/ui`
- `src/agent_ludens/app.py` redirects `/` to `/ui/index.html`
- `src/agent_ludens/ui/index.html` exists in the runtime package

The current release docs also treat browser access as part of sign-off:

- `docs/testing_strategy.md` requires Playwright/browser-driven live
  verification
- `docs/release_checklist.md` requires browser-driven live verification
- `docs/api_spec.md` still says owner-UI-specific routes and streaming
  browser-facing event feeds are deferred, which is compatible with a static UI
  shell but not with "UI fully deferred" wording elsewhere

## Why it matters

Release and implementation decisions depend on one stable scope statement.
When the docs disagree, maintainers cannot tell whether the owner UI is:

- part of the production-ready contract
- implemented but non-normative
- or still intentionally deferred

## Recommended alignment decision

Pick one of these positions and apply it consistently across the docs set:

1. `Stage 1 only`: move owner UI language back to deferred/non-normative status.
2. `Stage 1 + integrated owner UI`: update the README, project structure, and
   release checklist to treat the UI as part of the shipped contract.

### Working recommendation from current evidence

Based on the checked repo state, the least-surprising contract is:

- Stage 1 local runtime remains the core boundary
- the local owner UI is implemented and ship-visible
- the API remains the primary operator contract
- Stage 3 marketplace work stays deferred

This is effectively `Stage 1 + integrated owner UI`, not "UI deferred".
That recommendation is an inference from the code, packaged assets, and current
browser-verification release gates.

## File-by-file alignment map

This is the smallest practical change map for the next docs pass.

| File | Current stance | If `Stage 1 only` wins | If `Stage 1 + integrated owner UI` wins |
| --- | --- | --- | --- |
| `docs/README.md` | Normative contract says Stage 1 only | Keep as-is, remove any UI-in-scope drift elsewhere | Update the scope boundary, reading guide, and guiding rules |
| `README.md` | Says "Stage 1 only" but includes the integrated Owner Web Interface | Remove UI from included scope | Clarify that Stage 1 is the core runtime boundary and the owner UI is integrated locally |
| `docs/project_structure.md` | Says dedicated owner web UI is deferred | Keep deferred wording | Change runtime surfaces and deferred roadmap wording |
| `docs/product_spec.md` | Says v0 includes Stage 2 Owner Web Interface | Revert UI from included to deferred | Keep, then align acceptance criteria and operator surface wording |
| `docs/implementation_plan.md` | Says Stage 2 has since been integrated | Move Stage 2 back to non-normative/deferred | Keep, but stop calling the roadmap purely deferred |
| `docs/api_spec.md` | Defers owner-UI/browser-facing routes | Keep deferred API surface | Promote browser/UI routes to normative if they are release-blocking |
| `docs/testing_strategy.md` | Requires browser live proof but later says browser/UI tests are deferred | Remove browser-live requirement if UI is deferred | Keep browser-live proof and delete deferred-browser language |
| `docs/release_checklist.md` | Release target is Stage 1 only but still requires browser proof | Keep Stage 1 language and remove UI-specific gate | Change scope check and contract checks to include UI |

## Decision criteria

The release boundary should be chosen by evidence, not by aspiration:

- pick `Stage 1 only` if the owner UI exists but is not required to operate,
  verify, or explain the runtime
- pick `Stage 1 + integrated owner UI` if release sign-off depends on browser
  access, browser evidence, or UI-specific routes behaving correctly
- treat a mounted `/ui` surface plus browser-release proof as evidence of an
  integrated operator surface, even if the API stays primary
- avoid mixed wording like "deferred but required for sign-off"; that creates an
  untestable contract

## Proposed next patch order

Once the intended boundary is confirmed, the lowest-risk edit order is:

1. update `README.md` and `docs/README.md` so the top-level contract is
   unambiguous in both entrypoints
2. update `docs/product_spec.md` and `docs/project_structure.md` to match it
3. update `docs/testing_strategy.md` and `docs/release_checklist.md` so release
   evidence matches the chosen scope
4. update `docs/api_spec.md` only if browser/UI routes change normative status
5. reread the full docs index once to catch any remaining deferred/included drift

## Suggested follow-up files

If the intended release is `Stage 1 + integrated owner UI`, update:

- `README.md`
- `docs/README.md`
- `docs/project_structure.md`
- `docs/architecture.md`
- `docs/api_spec.md`
- `docs/release_checklist.md`
- `docs/testing_strategy.md`

If the intended release is still `Stage 1 only`, update:

- `docs/product_spec.md`
- `docs/implementation_plan.md`
- any UI-facing release evidence requirements

## Status

No normative contract file was changed in this turn. This note was tightened
with current-code evidence so the next documentation pass can align scope
without re-deriving the same facts.
