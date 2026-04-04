---
id: log_20260404_docs-product-close-tier-4-review-round-two
type: log
status: active
event_type: tier4-roadmap-prd-refresh-and-merge
source: cli
branch: codex/tier4-roadmap-prd-refresh
created: 2026-04-04
---

# docs(product): close Tier 4 review round two

## Summary

Completed the Tier 4 product-definition refresh and closed two full review
rounds on PR #41. The branch now aligns the roadmap, PRD, prioritization
matrix, handoff brief, ontology architecture, and a new digest design spec
around an implementation-ready first Tier 4 slice.

## Goal

Refresh Tier 4 planning docs so the feature set is consistent, `folio digest`
is the explicit first implementation slice, and the first Tier 4 PR has enough
contract detail to support implementation without reopening basic product
questions.

## Key Decisions

- Keep Tier 4 digest-first, with daily digest before weekly digest.
- Treat digest notes as source-less `type: analysis`, `subtype: digest`
  managed documents.
- Keep `folio digest` engagement-scoped and manual by default in the first
  slice.
- Keep `folio synthesize` pairwise-first and distinct from temporal digests.
- Defer `steerco` CLI support, cross-engagement pattern detection, automatic
  digest triggering, and deeper synthesis trust modeling beyond the initial
  review-required posture.
- Add `docs/specs/tier4_digest_design_spec.md` rather than overloading the PRD
  with every first-slice implementation detail.

## Alternatives Considered

- Expanding FR-801 / FR-802 only, without a separate digest spec.
  Rejected because the review correctly identified too many hidden decisions
  for a terse PRD section to carry cleanly.
- Making digest generation library-wide by default.
  Rejected because the first slice needs a bounded engagement scope to stay
  interpretable and operationally safe.
- Treating digest output like FR-700 extraction artifacts.
  Rejected because synthesis outputs are inferential and need a distinct trust
  posture.

## Changes Made

- Expanded the PRD Tier 4 requirement family with FR-800 through FR-809.
- Added explicit routing keys for `routing.digest` and `routing.synthesize`.
- Added the Tier 4 digest design spec covering CLI contract, input predicates,
  output path, registry integration, body template, rerun semantics, failure
  behavior, and interim trust/reviewability.
- Updated the roadmap to reflect Tier 3 completion, Tier 4 readiness, concrete
  Tier 4 gates, and current Tier 4 CLI signatures.
- Updated the ontology architecture examples so the digest example and weekly
  digest description match the Tier 4 trust posture and weekly-from-daily
  model.
- Aligned supporting product docs on `tag vocabulary`, pairwise synthesis, and
  engagement-scoped digest generation.

## Impacts

- The Tier 4 docs are now merge-ready with an implementation-ready contract for
  the first digest slice.
- The next implementation PR can focus on code, not baseline product decisions.
- Future Tier 4 work remains intentionally staged: digest first, broader
  synthesis/search/traversal later.

## Testing

Manual documentation validation only:

- `git diff --check`
- Targeted ripgrep consistency searches across roadmap, PRD, matrix, handoff
  brief, ontology architecture, and digest spec
- Two external review rounds via PR #41 with the final branch resolving the
  remaining ontology inconsistencies
