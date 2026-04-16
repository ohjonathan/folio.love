---
id: tier4_digest_design_spec
type: spec
status: draft
ontos_schema: 2.2
created: 2026-04-04
revision: 4
revision_note: |
  Rev 4: Add the explicit `--include-flagged` override, excluded-count
  disclosure, and empty-result behavior required by the narrowed Tier 4 trust
  contract.
  Rev 3: Align the first-slice digest contract to the shared Tier 4 graph-ops
  foundation and shared proposal review surface.
  Rev 2: Clarify digest rerun, registry, and source-less analysis behavior.
  Rev 1: Initial draft.
depends_on:
  - doc_02_product_requirements_document
  - doc_04_implementation_roadmap
  - doc_06_prioritization_matrix
  - folio_ontology_architecture
  - folio_feature_handoff_brief
  - tier4_discovery_proposal_layer_spec
---

# Tier 4 Digest Design Spec

## 1. Overview

This spec defines the first implementation slice for `folio digest`:

1. daily digest generation
2. weekly digest generation from daily digests
3. source-less `analysis/digest` registry behavior that does not break
   `scan`, `refresh`, `status`, or `enrich`

This spec exists because the Tier 4 roadmap and PRD define the feature
direction, but the first implementation PR still needs a concrete contract for
scope, inputs, output path, rerun semantics, and failure behavior.
It also aligns the digest slice to the shared Tier 4 graph-ops foundation so
later relationship suggestions flow through `folio links` instead of a
digest-specific review workflow, using the shared proposal review hardening
contract defined in
`docs/specs/tier4_discovery_proposal_layer_spec.md`.

## 2. Goals

The first `folio digest` implementation must:

1. create a deterministic daily digest for one explicit engagement scope
2. create a deterministic weekly digest from existing daily digests
3. register digest notes as source-less managed `analysis` docs
4. avoid breaking current Tier 2/Tier 3 command behavior
5. fail safely without creating ambiguous partial outputs
6. respect the default Tier 4 trust gate for source-backed inputs

## 3. Non-Goals

The following are out of scope for the first digest slice:

| Item | Why deferred |
|------|--------------|
| `--steerco` CLI flag | The typed digest contract keeps `steerco`, but the first implementation slice is daily + weekly only. |
| Automatic file-watcher triggering | Manual trigger remains the v1 default. |
| Cross-engagement digest generation | The first slice is engagement-scoped to avoid accidental library-wide synthesis. |
| Digest-specific enrich pass | Current `folio enrich` continues to skip `analysis` docs. |
| Digest grounding parity with FR-700 extraction outputs | Digest claims are inferential synthesis, not single-source extraction. |
| N-way synthesis | Covered by later `folio synthesize` evolution, not `folio digest`. |
| Digest-specific proposal lifecycle or relationship confirmation UX | Later relationship suggestions must use the shared proposal layer and `folio links`, not a digest-only flow. |

## 4. CLI Contract

```bash
folio digest <scope> [--date YYYY-MM-DD] [--week] [--include-flagged] [--llm-profile <profile>]
```

Rules:

1. `<scope>` is required in the first slice and must resolve under one
   engagement subtree within `library_root`.
2. Omitted `--date` means the current local date.
3. Without `--week`, the command generates a daily digest.
4. With `--week`, the command generates a weekly digest for the ISO week that
   contains `--date`.
5. `--include-flagged` widens the daily source-backed input set to include
   notes whose `review_status` is `flagged`.
6. `--llm-profile` overrides `routing.digest` for one invocation.

Examples:

```bash
folio digest ClientA/DD_Q1_2026 --date 2026-04-04
folio digest ClientA/DD_Q1_2026 --week --date 2026-04-04
```

## 5. Daily Input Predicate

For a daily digest, eligible inputs are registry-backed managed docs that meet
all of the following:

1. under the requested `<scope>`
2. `type` is `evidence` or `interaction`
3. the effective activity date matches the requested digest day
4. `review_status` is not `flagged`, unless `--include-flagged` is supplied

Effective activity date is defined as:

1. `modified` when present
2. otherwise `converted`
3. otherwise the note is not eligible

The first slice does not attempt to infer activity from filesystem mtimes.
Context docs and existing analysis docs are excluded from the daily input set
to keep the first slice deterministic and to avoid recursive digest-of-digest
behavior.

If no eligible inputs exist, the command exits successfully and writes no note.
If flagged source-backed inputs were excluded and that exclusion is the reason
the candidate set is empty, the output must say so explicitly, report the
excluded count, and point the operator to `--include-flagged`.

`extraction_confidence` remains surfaced trust metadata, not a second hard
exclusion rule in the first digest slice.

## 6. Weekly Discovery Predicate

Weekly digests consume existing daily digests rather than raw evidence and
interaction notes.

Weekly eligible inputs are registry-backed managed docs that meet all of the
following:

1. under the requested `<scope>`
2. `type: analysis`
3. `subtype: digest`
4. `digest_type: daily`
5. `digest_period` falls within the ISO week anchored by `--date`

The weekly digest's `digest_period` is the Monday date of that ISO week.

If no daily digests exist for the requested week, the command exits
successfully with a clear message and writes no weekly digest.

## 7. Output Path And Identity

Digest outputs live under the scoped engagement root at:

```text
<engagement-root>/analysis/digests/<digest-id>/<digest-id>.md
```

ID convention:

```text
{client}_{engagement-short}_analysis_{digest-period-compact}_{digest-label}
```

Examples:

```text
usbank_techresilience2026_analysis_20260404_daily-digest
usbank_techresilience2026_analysis_20260330_weekly-digest
```

This keeps digest notes:

1. engagement-local
2. clearly distinct from evidence and interaction notes
3. path-stable for idempotent reruns

## 8. Frontmatter And Registry Contract

Daily and weekly digests are source-less managed docs with:

```yaml
type: analysis
subtype: digest
status: complete
authority: analyzed
curation_level: L1
review_status: flagged
review_flags:
  - synthesis_requires_review
digest_period: 2026-04-04
digest_type: daily
draws_from:
  - some_source_doc_id
```

Required behavior:

1. omit `source`, `source_hash`, `source_type`, and `source_transcript`
2. register the note in `registry.json` as a source-less managed row
3. preserve `client` and `engagement`
4. populate `draws_from` with the exact input document IDs used
5. carry `modified` and version metadata on rerun

Registry compatibility requirements:

1. `status` must include `analysis` rows in per-type summaries
2. `scan` must ignore digest rows because they have no backing source
3. `refresh` must skip `analysis` rows with rerun guidance to use
   `folio digest` or `folio synthesize`
4. `rebuild_registry()` must retain source-less `analysis` docs in addition to
   existing source-less `context` docs
5. `enrich` continues to skip `analysis` rows in the first digest slice

## 9. Body Template

Daily digest body sections:

1. `## Summary`
2. `## What Moved Today`
3. `## Emerging Risks / Open Questions`
4. `## Documents Drawn From`
5. `## Suggested Follow-Ups`
6. `## Trust Notes`

Weekly digest body sections:

1. `## Weekly Summary`
2. `## What Changed This Week`
3. `## Cross-Cutting Themes`
4. `## Decisions / Risks To Track`
5. `## Daily Digests Drawn From`
6. `## Next Week Lookahead`
7. `## Trust Notes`

`## Documents Drawn From` and `## Daily Digests Drawn From` must list the exact
input note wikilinks so the reader can audit the synthesis scope.
`## Trust Notes` must:

1. state whether flagged source-backed inputs were excluded or included via
   override
2. report the excluded flagged-input count when any were omitted
3. remind the reader that digest notes remain review-required synthesis
   artifacts in the first slice

## 10. Rerun, Atomicity, And Correction Path

Rerun semantics:

1. same `<scope>` + same digest period + same digest type resolves to the same
   note path and ID
2. rerun updates the existing note instead of creating a duplicate
3. successful rerun increments `version` and updates `modified`

Write safety:

1. write to a temp file first, then replace the target atomically
2. if synthesis fails, keep the existing digest unchanged
3. never leave a truncated partial digest in place

Correction path:

1. operators may rerun the digest after upstream notes change
2. operators may delete a bad digest and regenerate it
3. manual edits to digest notes are not preserved across rerun in the first
   slice; digest notes remain generated artifacts until a dedicated synthesis
   override model is specified

## 11. Failure Behavior

If the LLM call or prompt execution fails after input selection:

1. exit non-zero
2. write no new digest note
3. preserve any existing digest note for that target period
4. surface the failing scope, digest type, and period in the error output

This differs intentionally from `convert` / `ingest` degraded-output behavior.
For the first digest slice, "no digest" is safer than a half-generated
synthesis artifact with no stable trust model.

## 12. Trust And Reviewability

Digest notes are synthesis artifacts, not source-grounded extraction artifacts.
They therefore do not inherit FR-700 verbatim-quote grounding semantics.

The first digest slice uses a conservative interim trust posture:

1. digest notes default to `review_status: flagged`
2. digest notes carry `review_flags: [synthesis_requires_review]`
3. digest notes are intended as analyst-facing prep aids until a dedicated
   Tier 4 synthesis review model is defined
4. daily digest input selection excludes flagged source-backed notes by default
   unless `--include-flagged` is supplied
5. weekly digest generation continues to consume existing daily digests as the
   designated first-slice synthesis intermediate

This keeps the output visible while making the review requirement explicit.

## 13. Deferred Follow-Ons

The following remain later Tier 4 work:
1. digest-generated relationship suggestions routed through `folio links`
2. `--steerco` output mode
3. automatic trigger / watcher behavior
4. digest inclusion of context or prior analysis docs
5. digest-specific enrichment and link refinement
6. broader Tier 4 synthesis trust modeling beyond the conservative
   `synthesis_requires_review` placeholder
