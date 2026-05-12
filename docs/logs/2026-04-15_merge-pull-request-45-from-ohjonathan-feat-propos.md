---
id: log_20260415_merge-pull-request-45-from-ohjonathan-feat-propos
type: log
status: active
event_type: v0-6-2-provenance-lifecycle-rename-adversarial-review
source: cli
branch: feat/provenance-lifecycle-rename-v0-6-2-C-author-claude
created: 2026-04-15
---

# v0.6.2 Provenance Lifecycle Rename Adversarial Review

## Summary

Wrote the Codex adversarial spec review for `docs/specs/v0.6.2_provenance_lifecycle_rename_spec.md`.

## Goal

Verify the provenance proposal lifecycle rename spec against `folio/provenance.py` and `folio/cli.py`, including the named proposal-status line references, pair-metadata exclusions, `_mark_enrich_stale()` behavior, `stale_pending` handling, and missed raw-dict-reader risks.

## Key Decisions

- Marked the review verdict as `Needs Fixes`.
- Treated pair-processing metadata `current_pair_meta["status"]` writes as out of scope because they represent pair execution state, not proposal lifecycle state.
- Identified a compatibility defect in the spec's raw-dict pending-state guidance: comparing fallback `status: pending_human_confirmation` directly to `queued` would drop legacy pending proposals.
- Confirmed the `_mark_enrich_stale()` dual-check pattern is correct for both legacy and renamed proposal dictionaries.

## Changes Made

- Added `docs/validation/v0.6.2_spec_adversarial_codex.md` with required frontmatter and adversarial findings.
- Ran Ontos activation attempts and used the existing context map after `ontos map` failed on pre-existing metadata issues and `python3 -m ontos map` was unavailable.

## Alternatives Considered

- Approving with a minor note was rejected because the raw-dict pending-reader issue can change behavior for legacy frontmatter.
- Treating all line-number drift as a blocker was rejected because the working tree already had partial PROV-1 edits; the spec's named line references matched the base semantic sites.

## Impacts

- The spec should be patched to require pending raw-dict readers to dual-check `("queued", "pending_human_confirmation")` or map fallback status values through `_STATUS_TO_LIFECYCLE`.
- Recommended tests should cover legacy pending proposals in `_has_pending_repair_proposals()` and `provenance_status_summary()`.

## Testing

- Static inspection only.
- Verified `folio/provenance.py` proposal-status and pair-metadata sites.
- Verified `folio/cli.py` `_mark_enrich_stale()` lines 96-135.
- Searched for additional provenance proposal raw-dict status readers in `folio/provenance.py` and `folio/cli.py`.
