---
id: tier3_baseline_decision_memo_20260327
type: atom
status: active
ontos_schema: 2.2
curation_level: 0
generated_by: codex
created: 2026-03-27
depends_on:
  - doc_02_product_requirements_document
  - doc_04_implementation_roadmap
  - tier2_platform_model_comparison_report
  - tier2_real_library_rerun_report
  - tier2_real_vault_validation_report
  - tier3_kickoff_checklist
---

# Tier 3 Baseline Decision Memo

This memo records what changed across the product baseline after the last
shared PRD/roadmap sync at commit `6c9b25d` (`docs(product): reflect PR30
performance patch in PRD and roadmap`).

It exists to answer one practical question:

> What is materially true about Folio now, after PR #32, PR #34, PR #35, the
> finalized model-comparison package, the full-corpus rerun, and the real
> vault-validation pass?

The short answer is that the product is farther along in Tier 3 than the
shared product docs previously reflected, and the operational baseline for the
next slice is now stable enough to start PR C (`folio enrich`) from the
production `anthropic_sonnet4` library rather than the `anthropic_haiku45`
scratch rerun.

## 1. Baseline At The Prior Iteration

The last shared PRD/roadmap sync was commit `6c9b25d`, which updated the
product docs to reflect PR #30 only.

At that point, the shared product docs correctly captured:

- Tier 2 performance hardening from PR #30
- the existence of the `folio ingest` plan as upcoming Tier 3 work
- the entity system, enrichment, provenance, and context-doc work as future
  slices

But they did **not** yet capture:

- shipped `folio ingest`
- shipped entity registry / entity CLI
- shipped ingest-time entity resolution
- finalized Tier 2 model-comparison conclusions
- the full-corpus rerun result that overruled the smaller benchmark’s
  production-default implication
- the real vault-validation decision that passed the production library to
  PR C

In other words, the product docs were still describing a mostly planned Tier 3
state while the repo and validation artifacts had moved to a partially shipped
and operationally validated Tier 3 state.

## 2. What Shipped Since Then

### 2.1 PR #32 — `folio ingest` interaction baseline

- **Merge commit:** `490f2f9`

This shipped the first Tier 3 slice:

- new `folio ingest` CLI command
- ontology-native `type: interaction` notes
- interaction-specific frontmatter using `source_transcript` and `source_hash`
- subtype-aware interaction analysis for:
  - `client_meeting`
  - `expert_interview`
  - `internal_sync`
  - `partner_check_in`
  - `workshop`
- structured interaction markdown with:
  - `## Summary`
  - `## Key Findings`
  - `## Entities Mentioned`
  - `## Quotes / Evidence`
  - `## Impact on Hypotheses`
  - collapsed raw transcript callout
- degraded-output handling when analysis cannot run
- mixed-library support so `status` and `scan` include interaction documents
  while `refresh` skips them and tells the user to re-run `folio ingest`
- `routing.ingest` as a real task-routing path

This matters because it turned interactions into a shipped document family
rather than a future concept. From this point forward, Tier 3 is no longer
just “decks plus planned graph work”; it includes a real second content family
with its own frontmatter contract, note template, routing, and re-ingest
identity rules.

### 2.2 PR #34 — entity registry foundation

- **Merge commit:** `e322660`

This shipped the entity-system foundation:

- canonical `entities.json` registry
- first-shipped entity types:
  - `person`
  - `department`
  - `system`
  - `process`
- `folio entities` CLI surface
- `folio entities import <csv>` for org-chart style import
- confirmation / rejection workflow for entities awaiting review
- entity-aware summary output in `folio status`

This work made the entity layer real. Before PR #34, interaction notes could
mention names as unresolved wikilinks, but there was no canonical store, no
import path for known org structure, and no confirmation lifecycle. After PR
#34, the product had a persistent entity registry and a real operator workflow
for creating and reviewing entity data.

### 2.3 PR #35 — ingest-time entity resolution

- **Merge commit:** `2a61d02`

This shipped the second half of the entity system:

- confirmed-only exact canonical-name resolution during ingest
- alias-aware resolution against confirmed entities
- type-strict resolution
- bounded LLM soft-match proposals when exact/alias matching fails
- unresolved extracted entities auto-created as unconfirmed
- `proposed_match` surfaced in existing entity review flows
- canonical wikilink rendering for resolved mentions during ingest and re-ingest

This changed the meaning of entity mentions in interaction notes. They are no
longer just raw extracted names rendered as `[[Name]]`; they can now resolve
to canonical entities when Folio already knows who or what the note is
referring to.

The important product boundary here is that v1 entity resolution is simple and
deliberate:

- exact match
- alias match
- bounded LLM soft match
- human confirmation
- no algorithmic fuzzy matcher

That constraint is now shipped reality, not a planning note.

## 3. What Validation Happened

### 3.1 Tier 2 platform model-comparison package was finalized

The model-comparison package under `docs/validation/` was promoted into its
canonical, tracked form and now records five required conclusions:

1. best Pass 1 profile/model
2. best diagram-stage profile/model
3. best Pass 2 profile/model
4. best interim single current-`main` default
5. exact future code/config implications if per-stage winners differ

The finalized recommendation was:

- **Pass 1:** `openai_gpt53`
- **Diagram stage:** `anthropic_haiku45`
- **Pass 2:** `anthropic_haiku45` (best-defensible interim recommendation)
- **Current single-route default on `main`:** `anthropic_haiku45`

This was important, but it turned out not to be the full story.

### 3.2 The full-corpus rerun changed the production-baseline decision

The full real-library rerun in
`docs/validation/tier2_real_library_rerun_report.md` materially changed the
operational interpretation of the earlier benchmark.

What happened:

- full corpus rerun on the real engagement set
- **161 source files**
  - `149` PDFs
  - `12` PPTXs
- **93 source directories**
- **94 batch invocations**
  - `83` PDF batches
  - `11` PPTX batches
- runtime: roughly **8.5 hours**
- one initial timeout, recovered by retry
- final operational result: **94/94 batch invocations succeeded**

The rerun used `anthropic_haiku45` because that was the benchmark’s best
interim single-route recommendation. But at full-corpus scale, the library
comparison showed that the existing production `anthropic_sonnet4` library was
still better overall:

- matched decks: `114`
- production better: `61` (`53.5%`)
- rerun better: `22` (`19.3%`)
- ties: `31`
- average production score: `46.0`
- average scratch rerun score: `43.1`

The key lesson was that the smaller benchmark did **not** generalize cleanly
to dense, multi-page, real-library production use.

### 3.3 Blind LLM validation changed the merge strategy

The rerun session summary records an additional validation step:

- top rerun-vs-production candidates were reviewed by a neutral model
  (`OpenAI gpt-4.1`)
- `15` candidates were blind-judged
- results:
  - `12` scratch-rerun decks confirmed better
  - `2` production decks retained despite heuristic advantage for rerun
  - `1` tie

This produced a better operational policy than either blanket choice:

- do **not** switch production wholesale to `haiku45`
- do **not** ignore the rerun entirely
- instead, keep the production `sonnet4` baseline and selectively merge only
  the rerun decks that survive blinded review

### 3.4 Real vault validation passed the production library to PR C

The final late-March validation step was the real Obsidian vault review in
`docs/validation/tier2_real_vault_validation_report.md`.

That pass validated the actual production library in the real vault
environment and concluded:

- **Gate:** `PASS TO PR C`
- production library usable for real engagement work
- production library usable as the input baseline for PR C

The validated production library state at that point was:

- **115 registry decks**
- **160 evidence notes**
- **1,524 diagram notes**
- **1,684 total markdown files**
- **0 YAML parse errors**
- **0 broken inline images**

This was the final operational proof that the next slice should be PR C, not
another rerun or another model-default experiment.

## 4. What Changed In The Actual Product Baseline

The most important product-baseline changes are:

### 4.1 Tier 3 baseline now includes ingest plus the first shipped entity layer

The current shipped Tier 3 baseline already supports:

- interaction notes as a real document family
- entity registry management
- org-chart CSV import
- confirmed/unconfirmed entity review flow
- canonicalization of common entity mentions during ingest

This is the baseline shift from “Tier 3 planning” to “Tier 3 already in
production use for ingest and entity management.”

### 4.2 Production library baseline is now “best-of-both,” not pure sonnet4

The production library should now be understood as:

- mostly `anthropic_sonnet4`
- plus **12 blind-validated `haiku45` merges**

That matters because future work should build on the best validated library,
not on a simplistic “one model owns everything” assumption.

### 4.3 PR C should start from the production library, not the rerun scratch library

This is the key late-March operational decision.

PR C should use:

- the production `anthropic_sonnet4` library
- with the 12 validated `haiku45` merges already incorporated

PR C should **not** use:

- the full `haiku45` scratch rerun library as its baseline

### 4.4 Per-stage routing is recorded, but it is not a prerequisite for PR C

The product now has a more nuanced routing picture than before:

- model-comparison package records different winners by stage
- current single-route runtime is still a separate practical reality
- full-corpus rerun disproved the idea that the benchmark alone should drive a
  blanket production switch

The result is that PR C should proceed from the validated production baseline
without waiting for per-stage routing implementation.

## 5. Known Non-Blocking Caveats

These items matter, but they do **not** change the decision to proceed to PR C.

### 5.1 Stale evidence-note source paths

The vault-validation package found that most evidence notes still point at an
older source-root layout rather than the current raw-architecture location.

This is a real metadata issue, but it is not a rendering or usability blocker.
It is exactly the kind of cleanup PR C can address.

### 5.2 Over-broad review-state surface

The vault-validation pass found that most evidence notes remain flagged, which
reduces the usefulness of review-status filtering as a practical triage tool.

This is real product friction, but it is not a blocker for reading,
navigation, or future enrichment work.

### 5.3 No Dataview plugin in the validated vault environment

The real vault validation was run in a core-Obsidian environment with no
Dataview plugin installed. That limits structured metadata discovery in real
use, but it is an environment gap rather than a product-structure defect.

### 5.4 Production vault still has no interaction notes in daily use

Even though `folio ingest` is shipped, the validated production vault does not
yet contain interaction notes in active use. So mixed-library behavior is
implemented and tested in code, but not yet richly exercised in day-to-day
engagement practice.

## 6. Why The Baseline Changed

The late-March validation cycle changed the baseline because the stronger
evidence came from the **bigger, more realistic run**, not the smaller
benchmark.

What changed conceptually:

- benchmark winner did not equal production winner
- full-corpus rerun revealed where `sonnet4` still had a quality advantage
- blind LLM review separated true rerun wins from heuristic-only wins
- vault validation proved the resulting mixed baseline was good enough for the
  next feature slice

So the late-March lesson is not just “which model won.” The real lesson is:

> Folio should choose downstream baselines from full-corpus validation plus
> targeted blind review, not from aggregate benchmark scores alone.

That is a product-learning change, not just a validation artifact.

## 7. Sequencing Status (Historical)

At the time of this memo, the next active feature slice was:

- **PR C: `folio enrich` core**

That recommendation has since been satisfied. PR C is now shipped and
production-tested. This memo remains authoritative for the late-March baseline
decision itself, but it is no longer the primary sequencing source for active
Tier 3 work. Current sequencing authority lives in:

- `docs/product/04_Implementation_Roadmap.md`
- `docs/validation/tier3_kickoff_checklist.md`
- `docs/specs/folio_provenance_spec.md` for PR D scope

## 8. Documents That Now Matter Most

For future planning and review, the most important current references are:

- `docs/product/02_Product_Requirements_Document.md`
- `docs/product/04_Implementation_Roadmap.md`
- `docs/validation/tier3_kickoff_checklist.md`
- `docs/validation/tier2_platform_model_comparison_report.md`
- `docs/validation/tier2_real_library_rerun_report.md`
- `docs/validation/tier2_real_vault_validation_report.md`
- `docs/validation/folio_enrich_production_test_report.md`

Together, these define the real late-March product baseline:

- shipped Tier 3 ingest
- shipped entity system
- validated production-library baseline
- PR C as the next active slice
