---
id: tier2_real_vault_validation_report
label: tier2_real_vault_validation
created: 2026-03-27
status: complete
---

# Tier 2 Real Vault Validation — Final Report

## Executive Summary

Validated the **production Folio library** (115 registry decks, 160 evidence
notes, 1,524 diagram notes) in the **real Obsidian vault** on a managed macOS
laptop. The library was produced by the sonnet4 baseline with 12 LLM-validated
haiku45 merges, as documented in
`tier2_real_library_rerun_session_summary.md`.

**Result: PASS TO PR C**

The production library is usable in Obsidian for real engagement work and is
ready to serve as the input baseline for PR C (`folio enrich`).

## Run Context

| Field | Value |
|-------|-------|
| Run date | 2026-03-27 |
| Operator | Internal operator |
| Machine | Managed macOS laptop (Apple Silicon) |
| Obsidian version | 1.12.4 |
| Vault path | OneDrive-synced workspace root |
| Obsidian plugins | Core only (no Dataview) |
| Production library | `PRODUCTION_LIBRARY_ROOT/` (115 decks, 1,684 markdown files) |
| Library baseline | sonnet4 (148 notes) + 12 merged haiku45 (per LLM-as-judge validation) |
| Prior gate | `tier2_real_library_rerun_report.md` — PASS TO VAULT VALIDATION |

## Production Library Baseline

The production library was built in a 4-stage process documented in
`tier2_real_library_rerun_session_summary.md`:

1. **Full-corpus rerun** — 161 source files processed with `anthropic_haiku45`
   into a scratch library (116 decks, ~8.5 hours)
2. **Heuristic comparison** — production sonnet4 outperformed haiku45 on 53.5%
   of matched decks (avg score 46.0 vs 43.1)
3. **LLM-as-judge validation** — OpenAI gpt-4.1 blind-reviewed 15 top
   candidates; confirmed 12 as genuinely better
4. **Selective merge** — 12 LLM-confirmed-better haiku45 decks merged into
   production library

The result is a best-of-both library: 103 original sonnet4 decks + 12
targeted haiku45 improvements.

## Sample Composition

| Category | Count | Selection Rationale |
|----------|-------|-------------------|
| Simple narrative (1-2 slides) | 3 | Service list, org chart, access policy |
| Dense multi-page (44-137 slides) | 3 | DR change requests, BCP/SCP, failover testing |
| Diagram-heavy (architecture) | 3 | Representative architecture overview notes |
| Merged haiku45 | 4 | Representative selectively merged notes |
| Entity-heavy (73-119 components) | 2 | Large component/entity inventories |
| **Total evidence notes** | **15** | |

Additional checks:
- 0 interaction notes (none exist in the production library — recorded as fact)
- 4 deck directories checked for diagram note structure (37 diagram notes inspected)
- Library-wide metadata scan covering all 1,684 markdown files

## Check Area Results

### A. Vault Open / Navigation — PASS

- Vault opens cleanly, no errors or warnings
- `PRODUCTION_LIBRARY_ROOT/` folder tree fully visible and navigable
- All 8 top-level subdirectories present
- No OneDrive sync corruption detected

### B. Note Rendering Quality — PASS

Tested in Obsidian reading view:

| Note Type | Note | Rendering |
|-----------|------|-----------|
| Simple (1 slide) | SIMPLE_01.md | Frontmatter, image, sections all render correctly |
| Dense (90 slides) | DENSE_03.md | All images render, outline works, scrollable, no lag |
| Diagram (20 slides) | MERGED_01.md | Mermaid transclusions render, Components + Connections tables visible |

### C. Reviewability — PASS (with noted awkwardness)

- `review_status`, `review_flags`, and `extraction_confidence` are present in
  all evidence notes and visible in the properties panel
- Body structure is clear: consistent headings, slide-by-slide sections,
  diagram transclusions where applicable
- Body content ranges from 1,003 chars (simple) to 393,335 chars (137-slide
  dense document)

**Awkwardness:** 150 of 160 evidence notes (94%) are flagged. The most common
flags are `diagram_abstained_slide_*` (LLM abstained from diagram extraction)
and `confidence_below_threshold` (82 notes). The flagging is too broad to serve
as a useful triage filter — nearly everything is flagged. This is not a blocker
but reduces the signal-to-noise ratio of the review-state surface.

### D. Mixed-Library Usability — PASS

The 12 merged haiku45 notes are structurally indistinguishable from the 148
original sonnet4 notes:

- Identical frontmatter schema (all 19 required fields present)
- Same review_status/flags behavior
- Consistent body formatting
- No `_llm_metadata` exposed in frontmatter (provenance not directly visible)
- Only distinguishing signal: `created` date (2026-03-27 vs 2026-03-17)

A reviewer would not encounter confusion from mixed-library provenance.

### E. Query / Retrieval Practicality — PARTIAL

No Dataview community plugin is installed. Available discovery methods:

| Method | Works | Limitation |
|--------|-------|------------|
| Global search | Yes | Text search only; no structured query |
| Tag pane | Yes | Tags from frontmatter `tags:` are browsable |
| Properties panel | Yes | Per-note metadata visible |
| Graph view | Yes | Shows transclusion links between notes |
| Structured batch queries | No | Requires Dataview plugin |

Core Obsidian features are sufficient for individual note review but
insufficient for metadata-driven batch discovery (e.g., "list all flagged notes
where source_type = pdf"). Installing Dataview would significantly improve
usability.

### F. Known Tier 2 Risks — PASS (no blockers)

| Risk | Status | Detail |
|------|--------|--------|
| Broken inline images | RESOLVED | 0 broken inline image refs across all 160 evidence notes. The 405 broken images from the accelerated precloseout are no longer present. |
| Confusing review-state surface | AWKWARD | 94% flagged — too broad for triage. Flag reasons are meaningful but the volume makes filtering impractical without Dataview. |
| Diagram rendering regressions | CLEAR | Mermaid renders in Obsidian reading view (confirmed). 140/1,524 diagram notes have Mermaid code. |
| Mixed-library confusion | CLEAR | 12 merged notes are structurally indistinguishable from 148 originals. |
| Entity-link noise | MINOR | `diagram_components` lists can be very long (up to 119 items) but are contained in frontmatter metadata, not in the body as wiki-links. |
| Stale source paths | KNOWN | 148/160 notes reference a defunct legacy source root. Metadata-only; does not affect rendering. Fixable in PR C. |

## Library-Wide Health Summary

| Metric | Value |
|--------|-------|
| Evidence notes | 160 |
| Diagram notes | 1,524 |
| Total markdown files | 1,684 |
| YAML parse errors | 0 (100%) |
| Slide images (PNG) | 1,700 |
| Broken inline images | 0 |
| Extraction confidence >= 0.8 | 76 (48%) |
| Extraction confidence 0.5-0.8 | 82 (51%) |
| Notes with diagram_types | 74 |
| Diagram notes with Mermaid | 140 (9.2%) |
| Diagram notes with transclusion | 1,524 (100%) |

## What Worked

1. **Vault opens cleanly and performs well** — no errors, no lag, even on the
   90-slide and 137-slide notes
2. **Frontmatter is 100% parseable** — zero YAML errors across 1,684 files
3. **All required metadata fields present** — every evidence note has all 19
   required fields
4. **Slide images render correctly** — 1,700 PNGs present and rendering
5. **Mermaid transclusion works** — diagram notes with Mermaid code render in
   Obsidian reading view via `![[note#section]]` transclusion
6. **Mixed-library provenance is invisible** — the 12 merged haiku45 notes are
   indistinguishable from the 148 sonnet4 notes in normal use
7. **Zero broken inline images** — the 405-image issue from the accelerated
   precloseout is no longer present

## What Was Awkward

1. **Review-state surface is too broad** — 94% of notes are flagged, making
   the flag signal nearly useless for triage without structured queries
2. **Stale source paths** — 148/160 notes point to a defunct legacy source
   root. The source files exist at the current architecture source root, but
   the frontmatter references are stale.
   This is metadata-only (no rendering impact) and fixable in PR C.
3. **No Dataview plugin** — limits metadata-driven discovery to manual search.
   Not a library issue but an environment gap.
4. **No interaction notes** — the production library is evidence-only. This is
   a library limitation (the engagement has not yet produced interaction notes),
   not a rendering issue.

## What Would Block Real Daily Use

**Nothing is blocking.** All critical rendering, navigation, and metadata
features work. The awkward issues (broad flagging, stale source paths, no
Dataview) are real friction points but none prevent a reviewer from opening,
reading, and reasoning about evidence notes in the production vault.

## Gate Decision

### PASS TO PR C

**Explicit answers to the gate questions:**

1. **Is the production library usable enough in Obsidian for real engagement
   work right now?**
   Yes. The vault opens cleanly, all note types render correctly (including
   Mermaid transclusion), frontmatter is 100% parseable, and all 1,700 slide
   images are present. A reviewer can open any note and understand its contents.

2. **Is it usable enough to serve as the input baseline for PR C
   (`folio enrich`)?**
   Yes. The library has clean metadata, consistent structure across both
   provenance types (sonnet4 and haiku45), and no structural defects that would
   complicate enrichment. PR C can fix the two awkward issues (stale source
   paths, over-broad flagging) as part of its enrichment pass.

3. **If not, what is the minimum blocking fix set?**
   N/A — no blocking issues identified.

## Next Steps

1. **Start PR C (`folio enrich`)** using the production library as input
2. **PR C should fix stale source paths** — rewrite the 148 legacy-root
   references to point to the current architecture source root
3. **PR C should consider recalibrating review flags** — the current 94%
   flagged rate is too broad for useful triage
4. **Install Dataview plugin** (independent of PR C) — would significantly
   improve metadata-driven workflows in the vault

## Artifacts Produced

| File | Description |
|------|-------------|
| `tier2_real_vault_validation_prompt.md` | Task specification |
| `tier2_real_vault_validation_report.md` | This report |
| `tier2_real_vault_validation_session_log.md` | Chronological check log |
| `tier2_real_vault_validation_chat_log.md` | Decision and rationale log |
| `_vault_validation_sample.json` | Per-note programmatic validation data |
| `_vault_validation_library_health.json` | Library-wide metadata health scan |
