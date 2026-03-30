---
id: log_20260329_rev6-provenance-unblock-doc-reconciliation
type: log
status: active
event_type: decision
source: cli
branch: main
created: 2026-03-29
---

# rev6-provenance-unblock-doc-reconciliation

## Context

Goal: Implement the Rev 6 provenance unblock plan by reconciling the live
Tier 3 governance docs with the provenance spec and removing the remaining
review blockers around stale repair trustworthiness, target anchoring, and
CLI clarity.

Reviewed inputs:
- `docs/specs/folio_provenance_spec.md`
- `docs/specs/folio_enrich_spec.md`
- `docs/product/02_Product_Requirements_Document.md`
- `docs/product/04_Implementation_Roadmap.md`
- `docs/architecture/Folio_Ontology_Architecture.md`
- `docs/validation/tier3_kickoff_checklist.md`
- `docs/product/tier3_baseline_decision_memo.md`
- Current enrich implementation notes confirming that `### Analysis` is
  enrich-managed while `**Evidence:**` remains the stable source-grounded
  structure

## Decision

Key decisions:
- Reconcile the authoritative live docs directly instead of relying on
  appendix-only amendment text inside the provenance spec.
- Re-anchor target-side provenance from enrich-managed `### Analysis` prose
  to structured target `**Evidence:**` entries using `target_slide` +
  `target_claim_index`.
- Make `folio provenance review` a read-only listing command and move all
  mutations to explicit CLI commands.
- Keep stale repair non-destructive: `re-evaluate` creates replacement
  proposals with `replaces_link_id`, never auto-confirms, and uses
  `re_evaluate_pending` on the confirmed link as the canonical repair state.
- Surface blocked repairs explicitly through pair-level `repair_error`
  metadata and status/review output instead of silently retrying forever.

## Rationale

Alternatives considered:
- Keep the Rev 5 appendix package approach and leave the live roadmap/PRD/
  ontology/kickoff surfaces unchanged until implementation.
- Continue anchoring target provenance to `### Analysis` passages because
  they are already present in evidence notes.
- Preserve the mixed interactive review model instead of switching fully to
  explicit CLI mutations.
- Auto-promote same-coordinate re-evaluation matches back to confirmed links.

Why rejected:
- Appendix-only governance text was the remaining approval blocker because
  the authoritative corpus still disagreed with the spec.
- `### Analysis` is enrich-managed and mutable; it is not a reliable anchor
  for stale verification.
- The interactive review contract and auto-promotion logic both left repair
  behavior under-specified and too easy to mistrust operationally.

## Consequences

Impacts:
- The live Tier 3 corpus now describes the same PR D v1 scope, seed model,
  CLI family, and refresh durability story.
- The provenance spec now defines a safer v1 contract: immutable evidence-entry
  anchoring, exact persisted snapshots, deterministic proposal IDs, and
  explicit blocked-repair surfacing.
- The remaining follow-on work is implementation and seeded real-library
  validation, not another round of document-governance reconciliation.
