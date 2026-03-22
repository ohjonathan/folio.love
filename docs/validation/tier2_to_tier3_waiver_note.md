---
id: tier2_to_tier3_waiver_note
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
---

# Tier 2 to Tier 3 Waiver Note

**Date:** 2026-03-21  
**Decision Owner:** Jonathan Oh  
**Scope:** Tier 3 implementation start authorization

## Decision

**WAIVE OPEN TIER 2 ITEMS FOR A NARROW TIER 3 START.**

Tier 3 implementation may begin now, but only under the scope constraints in
this note.

This is **not** a declaration that Tier 2 is formally complete. It is a narrow
authorization to begin the first Tier 3 implementation slice while formal Tier
2 closeout remains open.

## Why This Waiver Is Being Granted

The current baseline supports a narrow Tier 3 start because:

- Tier 2 implementation is already on `main`.
- The accelerated pre-closeout run found the command loop operationally sound.
- No systematic Tier 2 product blockers were identified in the accelerated
  validation.
- Tier 3 planning was already judged safe to proceed in parallel.

Primary reference:

- [tier2_accelerated_precloseout_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_accelerated_precloseout_report.md)

## Open Tier 2 Items Being Explicitly Waived

The following Tier 2 items remain open or partial and are **not** being treated
as complete by this waiver:

- multi-client library scale / navigability at the formal target
- full Obsidian real-vault validation on the production library
- empty `target_prefix` source-root validation
- the 2+ week real-engagement daily-use criterion

These remain Tier 2 work. They are being waived only to allow a narrow Tier 3
start.

## Scope Allowed Under This Waiver

The waiver authorizes:

- Tier 3 planning and spec work
- Tier 3 implementation of the **first slice only: `folio ingest`**
- fixture assembly and tests needed to support `folio ingest`
- work on the personal Folio development laptop

## Scope Not Allowed Under This Waiver

This waiver does **not** authorize:

- declaring Tier 2 formally closed
- treating the 2-week daily-use criterion as satisfied
- starting broad Tier 3 implementation across ingest + entities + enrich at
  once
- starting `folio enrich` / retroactive provenance work without the recommended
  rerun and vault-validation steps
- using this waiver as evidence that the real engagement library is already in
  final Tier 3-ready condition

## Operating Constraints

While this waiver is active:

1. The first Tier 3 PR must remain **`folio ingest` only**.
2. Entities and `folio enrich` should not start before the ingest slice is
   scoped, implemented, and landed cleanly.
3. The real engagement/library rerun on the McKinsey laptop remains a serious
   prerequisite before enrichment/provenance-heavy Tier 3 work.
4. Real-vault validation on the McKinsey laptop remains expected before later
   Tier 3 enrichment work.

## Machine / Owner Split

- **Personal Folio dev laptop:** Tier 3 planning, prompt/spec drafting,
  implementation, unit/integration tests
- **McKinsey laptop:** real engagement corpus reruns, real vault validation,
  ongoing daily-driver validation
- **Decision owner:** Jonathan Oh
- **Drafting / implementation support:** AI agents

## Next Required Steps

1. Freeze the first Tier 3 implementation slice as `folio ingest` only.
2. Draft the Tier 3 kickoff prompt/spec.
3. Assemble initial transcript/context/entity fixtures.
4. Implement `folio ingest`.
5. Keep Tier 2 closeout open and continue tracking the waived items separately.

## Status

**Effective now for a narrow Tier 3 start.**

The waiver remains valid until replaced by either:

- formal Tier 2 closeout, or
- a later written decision that changes Tier 3 scope or sequencing

