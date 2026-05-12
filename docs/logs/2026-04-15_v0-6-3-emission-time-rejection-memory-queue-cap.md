---
id: log_20260415_v0-6-3-emission-time-rejection-memory-queue-cap
type: log
status: active
event_type: v0-6-4-spec-adversarial-codex-review
source: cli
branch: feat/trust-gated-surfacing-v0-6-4
created: 2026-04-15
---

# v0.6.4: trust-gated surfacing adversarial review

## Summary

Completed Codex adversarial spec review for
`docs/specs/v0.6.4_trust_gated_surfacing_spec.md` and wrote the findings to
`docs/validation/v0.6.4_spec_adversarial_codex.md`.

## Goal

Find failure modes in the v0.6.4 trust-gated surfacing spec for
`folio links review`, with emphasis on registry/frontmatter consistency,
malformed `review_status`, bypass paths, ordering with rejection-memory
suppression, silent-empty behavior, and revived plus flagged tag composition.

## Changes Made

- Ran Ontos activation and regenerated `Ontos_Context_Map.md`.
- Inspected the v0.6.4 spec, `folio/links.py`, `folio/cli.py` link command
  surfaces, registry review-status handling, and the Tier 4 parent contract
  sections 11 and 15.4.
- Added adversarial review artifact:
  `docs/validation/v0.6.4_spec_adversarial_codex.md`.
- Verdict: Needs Fixes.
- Main blockers:
  - Target trust gating uses stale registry state while source gating uses live
    frontmatter.
  - `folio links status` can silently report empty or zero while flagged
    proposals exist.
  - `confirm-doc` and `reject-doc` can return successful zero counts when
    flagged inputs are the real cause.
  - `suppression_counts["flagged_input"]` corrupts rejection-memory output
    unless policy counts are separated.

## Key Decisions

- Classified stale target registry trust state as a blocker because it can both
  fail open and falsely suppress clean proposals.
- Classified `links status`, `confirm-doc`, and `reject-doc` silent-empty
  behavior as blockers because they violate the parent rule forbidding silent
  empty results when flagged inputs are the real cause.
- Kept malformed `review_status` handling as should-fix rather than blocker:
  `None` and missing values can reasonably mean non-flagged, but malformed
  truthy values should not be silently equivalent to clean trust metadata.

## Alternatives Considered

- Treat registry as authoritative for target trust status. Rejected because the
  registry implementation documents `review_status` as frontmatter-authoritative
  and `load_registry()` does not reconcile before returning.
- Treat `--include-flagged` as read-only review only. Left as a possible design
  option, but the spec must state that included flagged proposals are blocked
  from confirm/reject if action commands do not get their own explicit override.

## Impacts

- The spec needs revision before implementation to prevent trust-gate bypasses,
  misleading status output, and contradictory suppression-count rendering.
- New tests should cover stale registry/frontmatter disagreement, malformed
  `review_status`, status and bulk-command silent-empty behavior, mixed
  rejection-memory plus flagged suppression counts, and revived plus flagged tag
  rendering.

## Testing

Static review only. No test suite was run because the task was to produce an
adversarial spec review artifact, not implement the spec.
