---
id: log_20260322_tier-3-ingest-kickoff-spec-approved-and-merged
type: log
status: complete
event_type: decision
source: codex
branch: codex/tier3-ingest-kickoff
created: 2026-03-22
concepts: [tier-3, ingest, specification, waiver, merge]
---

# Tier 3 ingest kickoff spec approved and merged

## Summary

Resolved the review cycle for the Tier 3 `folio ingest` kickoff materials,
captured the Tier 2 waiver and kickoff checklist, and prepared PR #31 for
merge as the approved implementation baseline for the first Tier 3 slice.

## Goal

- Finalize a review-ready `folio ingest` v0.5.0 kickoff specification
- Record the Tier 2-to-Tier 3 waiver and kickoff tracker in the repo
- Merge the approved Tier 3 kickoff docs into `main` as the new planning
  baseline

## Changes Made

- Added the Tier 2 waiver note at
  `docs/validation/tier2_to_tier3_waiver_note.md`
- Added the Tier 3 kickoff tracker at
  `docs/validation/tier3_kickoff_checklist.md`
- Drafted and iterated the detailed ingest spec at
  `docs/specs/v0.5.0_tier3_ingest_spec.md`
- Addressed reviewer feedback across multiple spec revisions, including
  ontology-native interaction frontmatter, source hashing, subtype-based IDs,
  rerun/versioning rules, transcript-aware fuzzy validation, degraded-output
  behavior, registry/validator changes, and expanded test/fixture plans
- Opened, reviewed, and prepared PR #31 for merge

## Key Decisions

- Tier 3 implementation will start with `folio ingest` only rather than a
  broad all-of-Tier-3 proposal
- The interaction document contract stays ontology-native instead of reusing
  evidence-style shim fields like `source_type: report` or `slide_count: 0`
- The spec explicitly includes unresolved wikilinks in the markdown body while
  deferring registry-backed entity mutation and enrichment workflows
- Large transcript handling, prompt design, grounding validation, and degraded
  provider-failure behavior are part of the kickoff spec and not left implicit

## Alternatives Considered

- Starting Tier 3 implementation without a formal Tier 2 waiver. Rejected
  because the roadmap and closeout checklist require an explicit go/waive
  decision.
- Writing one detailed master proposal for all of Tier 3. Rejected because it
  would lock in entity and enrichment behavior before the first ingest slice is
  proven.
- Reusing current evidence/frontmatter assumptions for interaction notes.
  Rejected because it would distort the ontology and create avoidable cleanup
  work later.

## Impacts

- The repo now has an approved, review-hardened implementation baseline for
  the first Tier 3 feature slice
- Tier 3 sequencing, machine ownership, and preconditions are documented in a
  live checklist rather than left implicit in chat
- Future implementation prompts can anchor to a concrete ingest contract,
  fixture plan, and validation strategy

## Testing

- GitHub Actions PR checks for PR #31
- Manual review against PR comments and requested revisions
