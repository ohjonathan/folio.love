---
id: log_20260322_entity-system-kickoff-spec-approved
type: log
status: complete
event_type: decision
source: claude-code
branch: docs/v0.5.1-entity-system-spec
pr: 33
created: 2026-03-22
concepts: [tier-3, entity-system, specification, review, merge]
---

# Entity system kickoff spec approved and merged

## Summary

Drafted, reviewed, revised, and merged the v0.5.1 Tier 3 entity-system kickoff
spec (PR #33). Three revisions addressed all blocking and should-fix issues
from consolidated review. The spec is now the approved implementation baseline
for the entity-system slice (Week 16–18).

## Goal

- Draft a review-ready entity-system kickoff spec grounded in the shipped
  v0.5.0 ingest baseline
- Address all review feedback across two rounds
- Merge approved spec to `main` as the planning baseline for PR A and PR B

## Changes Made

- Added `docs/specs/v0.5.1_tier3_entity_system_spec.md` (the spec)
- Added `docs/prompts/CA_META_PROMPT_tier3_entity_system_kickoff.md` (the
  prompt that produced the spec)
- Updated `docs/product/02_Product_Requirements_Document.md` (v1.2: shipped
  ingest baseline, mixed-library behavior)
- Updated `docs/product/04_Implementation_Roadmap.md` (PR #32 shipped status)
- Updated `docs/validation/tier3_kickoff_checklist.md` (live tracker with
  entity-system sequencing)
- Updated `Ontos_Context_Map.md` (new documents indexed)

## Key Decisions

- **JSON registry** (`entities.json`), not markdown directory
- **Type-strict resolution**, no cross-type fallback
- **LLM soft match required** for PR B, not stretch
- **Unconfirmed entities excluded from resolution** to prevent junk
  reinforcement
- **Advisory locking** via `fcntl.flock` matching `registry.py` pattern
- **No `folio entities resolve`** — retroactive note mutation deferred to
  enrich per governing docs; re-ingest is the sole update mechanism
- **Two-pass import** for row-order-independent `reports_to` resolution

## Review Cycle

- Rev 1: Initial draft — 6 blocking, 7 should-fix from consolidated review
- Rev 2: Addressed all 13 issues — 3 residual findings from round-2 review
- Rev 3: Removed `folio entities resolve`, fixed locking model, cleaned
  references — approved
