<div style="text-align:right; color:#888; font-size:0.85em;">Created: 2026-03-29 00:15</div>

# `folio enrich` Production Library Test Report

**Prepared by:** Ada (Jonathan Oh)
**Date:** 2026-03-28
**Library:** US Bank Tech Resilience DD — 115 registered decks
**folio-love version:** 0.3.0
**Branch:** `enrich/production-test`

---

## Executive Summary

We ran `folio enrich` on the full production library (115 evidence notes) to validate the enrichment pipeline at scale and produce the relationship output needed for the retroactive provenance feature (PR D). The enrichment succeeded with zero failures. We then performed two post-enrichment interventions to improve Obsidian graph connectivity: confirming relationship proposals and generating 1,134 entity stub notes with organizational hierarchy data.

This report documents what we did, what we learned, and what the folio team should consider for the next iteration of `folio enrich`.

---

## 1. What We Did

### Phase 1: Prerequisites and Registry Fix

**Problem discovered:** The initial dry run returned `No eligible documents found.` — zero notes were eligible for enrichment despite 115 registered decks.

**Root cause:** All 115 entries in `registry.json` were missing the `type` field. The enrich eligibility filter (`entry.type not in ("evidence", "interaction")`) rejected every entry because `type` defaulted to `None`.

**Fix:** Ran `folio status --refresh`, which triggered `reconcile_from_frontmatter()`. This synced the `type` field from each note's YAML frontmatter (where `type: evidence` was correctly set) into the registry. After reconciliation, all 115 entries had `type: evidence`.

**Lesson for folio team:** The `rebuild_registry()` function at line 159 of `registry.py` does `type=fm.get("type", "evidence")`, so newly built registries get the field. But registries built by older versions of folio-love (pre-0.3.0) that were carried forward never had `type` populated. Any library upgraded from an older folio-love version will hit this same issue. Consider adding a startup check in `plan_enrichment()` that warns when registry entries lack `type`.

### Phase 2: Dry Run

| Metric | Value |
|--------|-------|
| Eligible documents | 115 |
| `would_analyze` | 115 |
| `would_skip` | 0 |
| `would_protect` | 0 |
| `would_conflict` | 0 |
| Diagram notes in output | 0 (correctly excluded) |

No issues. All notes eligible, no diagram note leakage.

### Phase 3: Scoped Test (Zelle — 6 notes)

Ran `folio enrich "Money Movement Doc Gathering/Zelle"` to validate output quality before full library run.

**Results:** 6 updated, 0 failed. Enrichment time: 53 seconds.

**Quality checks — all passed:**

| Check | Result |
|-------|--------|
| Tags additive, reasonable vocabulary | PASS — 8-30 tags added per note (e.g., `microservices`, `payment-processing`, `zelle`) |
| `_llm_metadata.enrich` block present | PASS — `status: executed`, fingerprints, per-axis results |
| Entity wikilinks in `### Analysis` only | PASS — `[[Money Movement]]`, `[[Kafka]]`, `[[Cassandra]]` in correct fields |
| `### Text (Verbatim)` untouched | PASS — exact byte-for-byte match before/after |
| Idempotency (re-run = all unchanged) | PASS — 0 updated, 6 unchanged, 0 LLM calls, 295ms |
| Human-edit safety (conflict detection) | PASS — edited `### Analysis`, re-ran, got `conflict; metadata only` |

### Phase 4: Full Library Run

| Metric | Value |
|--------|-------|
| Total eligible notes | 115 |
| Updated | 108 |
| Unchanged (pre-enriched Zelle) | 6 |
| Protected (metadata only) | 0 |
| Conflicted (test artifact) | 1 |
| **Failed** | **0** |
| Runtime | **17 minutes 7 seconds** |
| Notes with relationship proposals | 6 |
| LLM profile | `anthropic_sonnet4` (Claude Sonnet 4) via QuantumBlack gateway |

### Phase 5: Post-Enrichment — Graph Connectivity Improvements

After the enrichment run, we opened the library in Obsidian and observed that the graph view showed ~115 isolated star clusters (each evidence note connected only to its own diagram notes) with no cross-deck connectivity. We performed two interventions:

**Intervention 1: Relationship Confirmation**
- Reviewed and confirmed all 6 `supersedes` proposals
- Added `supersedes: [target_id]` to each source note's canonical frontmatter
- Re-ran `folio enrich` — generated `## Related` sections with `[[path/to/note|Title]]` wikilinks on 3 writable notes
- 3 body-protected notes got metadata updates but could not receive `## Related` body sections

**Intervention 2: Entity Stub Generation + Org Hierarchy Merge**
- Wrote `ada-folio/scripts/generate_entity_stubs.py` to extract all entities from `_llm_metadata.enrich.axes.entities` across all enriched notes
- Generated 1,134 entity stub `.md` files in `library/_entities/`
- Matched person entities against the proxy org chart (`org_chart.json` — 1,531 people with L2-L6 hierarchy)
- Person stubs with org matches include `reports_to: "[[Manager Name]]"` wikilinks creating org hierarchy edges in the graph
- Added 32 additional chain manager stubs to complete reporting chains from L6 up to L2 (CTO)

---

## 2. What We Achieved

### Library State After Enrichment

| Metric | Before | After |
|--------|--------|-------|
| Total `.md` files in library | 1,684 | 2,818 |
| Evidence notes with `_llm_metadata.enrich` | 0 | 115 |
| Evidence notes with `## Related` sections | 0 | 3 |
| Evidence notes with `supersedes` in frontmatter | 0 | 6 |
| Entity stub notes | 0 | 1,134 |
| Entity stubs with org hierarchy (`reports_to`) | 0 | 60 |
| Wikilinks in evidence note bodies | ~2,000 (diagram embeds) | 3,150 |
| Unique wikilink targets across library | ~1,200 | 1,928 |

### Entity Stub Breakdown

| Category | Count |
|----------|-------|
| People (total) | 217 |
| — with org hierarchy (L2-L6) | 60 |
| — L2 (CTO / EVP) | 7 |
| — L3 (SVP / business line heads) | 12 |
| — L4 (VP / domain leads) | 21 |
| — L5 (Director / team leads) | 20 |
| — L6 (Manager / senior engineers) | 7 |
| Systems (Kafka, Hogan, SinglePoint, etc.) | 529 |
| Processes (Money Movement, Payment Processing, etc.) | 271 |
| Other (departments, etc.) | 117 |
| **Total** | **1,134** |

### Enrichment Quality Assessment

**Tags:** Consistently reasonable consulting/technology vocabulary. Range of 3-75 tags added per note. Examples: `microservices`, `disaster-recovery`, `payment-processing`, `car-id-25`, `batch-processing`, `treasury-management`. No garbage, no removed tags.

**Entity mentions:** Correctly identified systems (`[[Kafka]]`, `[[SinglePoint]]`, `[[Hogan]]`, `[[Cassandra]]`), people (`[[Rachel Hansen]]`, `[[Rob Cheek]]`, `[[Rick Arnold]]`), and processes (`[[Money Movement]]`, `[[Payment Processing]]`). ~193 unique person names, ~549 system names, ~277 process names identified.

**Wikilink placement:** Entity wikilinks inserted only in managed `### Analysis` sections (`**Visual Description:**`, `**Key Data:**`, `**Main Insight:**`). Protected content (`### Text (Verbatim)`, `**Evidence:**` blocks) verified unchanged.

**Relationship proposals:** 6 `supersedes` proposals, all high confidence (5 high, 1 medium), all plausible. No `impacts` proposals (no interaction notes in library). No false positives observed.

### Sample Relationship Proposal

```yaml
# ftmv4-prod supersedes 3.2_ftmv4_data_flow_diagram_v1
relation: supersedes
target_id: us_bank_tech_resilience_dd_evidence_20260317_3.2_ftmv4_data_flow_diagram_v1
confidence: high
rationale: "Both notes are FTMV4 architecture diagrams from the same engagement.
  The source note 'Ftmv4 Prod' appears to be a production-specific version
  that would supersede the general 'Ftmv4 Data Flow Diagram V1'."
status: pending_human_confirmation
```

### Sample Entity Stub (Person with Org Hierarchy)

```yaml
---
id: entity/person/rob-cheek
title: "Rob Cheek"
type: entity
entity_type: person
org_level: L4
reports_to: "[[Rachel D Hansen]]"
portfolios:
  - "Treasury & Payment Solutions"
  - "Technology"
  - "Corporate & Commercial Banking"
app_count: 56
incident_count: 15
---
# Rob Cheek

**Level:** L4 | **Reports to:** [[Rachel D Hansen]]
**Portfolios:** Treasury & Payment Solutions, Technology, Corporate & Commercial Banking
**Applications owned:** 56 | **Incidents:** 15
```

---

## 3. Things We Learned

### 3.1 Registry `type` field gap (critical for folio team)

**Issue:** Registries built by older folio-love versions lack the `type` field. The `RegistryEntry` dataclass defaults `type` to `None`. The `to_dict()` method at line 54 skips `None` fields (`{k: v for k, v in asdict(self).items() if v is not None}`), so `type` is never serialized. On next load, `entry_from_dict()` constructs a `RegistryEntry` with `type=None`, and the enrich filter rejects it.

**Recommendation:** Add a migration step or a warning. Options:
1. In `plan_enrichment()`, if zero eligible notes are found, log a warning suggesting `folio status --refresh`
2. In `entry_from_dict()`, default `type` to `"evidence"` when the field is missing (matches `rebuild_registry()` behavior at line 159)
3. Add a `folio doctor` or `folio migrate` command that detects and fixes registry gaps

### 3.2 Body protection is aggressive but correct

26 of 115 notes (23%) were body-protected because their `### Analysis` sections were "not identifiable" — the section parser could not find the expected managed section markers. These notes still received tag enrichment and entity metadata in frontmatter, but no wikilinks were inserted into their body text.

**Impact:** These 26 notes participate in the knowledge graph only through their existing diagram links, not through entity wikilinks. If the section parser were more lenient (or if these notes were re-converted with the current folio version), they would gain entity wikilinks.

**Recommendation:** Consider a `folio enrich --diagnose` mode that reports which notes have unidentifiable managed sections and why, so the operator can decide whether to re-convert or manually tag those sections.

### 3.3 Relationship proposals are sparse but high quality

Only 6 of 115 notes (5%) produced relationship proposals. All were `supersedes` (evidence notes only emit `supersedes`; `impacts` requires interaction notes). All 6 were plausible and confirmed.

The low proposal rate is likely because:
- Many notes in this library are architecturally distinct (different payment rails, different systems) — they don't have clear supersession relationships
- The relationship pass requires `client` and `engagement` fields to match, which is correct but limits cross-engagement proposals
- No interaction notes exist, so `impacts` proposals cannot be generated

**Recommendation:** The proposal quality is excellent — the team should not try to increase quantity at the expense of precision. For libraries with interaction notes (meeting summaries, interview transcripts), the `impacts` axis should produce more cross-cutting relationships.

### 3.4 Entity wikilinks create graph connectivity only when stub notes exist

After enrichment, the Obsidian graph view still showed isolated star clusters. Entity wikilinks (`[[Kafka]]`, `[[SinglePoint]]`) were present in the note bodies, but without corresponding `.md` files, Obsidian renders them as phantom (unresolved) nodes that barely affect the graph topology.

**Post-enrichment step needed:** Generating entity stub notes is essential for the enrichment to produce visible graph connectivity in Obsidian. Without stubs, the wikilinks are there but structurally inert.

**Recommendation for folio team:** Consider adding a `folio entities generate-stubs` command (or integrating it into `folio enrich --generate-stubs`) that creates lightweight `.md` files for all resolved entities. This is the single highest-impact post-enrichment step for Obsidian users.

### 3.5 Person entity deduplication needs work

The enrichment identified ~193 person entity mentions, but many are duplicates with name variants:
- `Rachel Link` / `Link, Rachel` / `Rachel J Link` / `Link, Rachelrjlink`
- `Joel Menard` / `Joel T Menard` / `Menard, Joel` / `Menard, Joeljtmenar`
- `Bradley Satchell` / `Bradley A Satchell` / `Satchell, Bradley` / `Satchell, Bradleybasatch`

The entity resolution system marks all of these as `confirmed:person/...` but with different canonical names. Our stub generation script collapsed some of these via org chart matching, but ~15-20 variants still produced separate stubs.

**Recommendation:** The entity resolution layer should normalize person names more aggressively — at minimum, handle `Last, First` ↔ `First Last` transposition and strip ID suffixes (e.g., `Rachelrjlink` appears to be a name concatenated with a user ID).

### 3.6 Cross-dataset merge (org chart + knowledge graph) is high value

Merging the proxy org chart (1,531 people, L2-L6, with `reports_to`, portfolios, app counts, incident counts) with the folio entity mentions created a knowledge graph with organizational hierarchy as its backbone. This answers questions that neither dataset can answer alone:

- Which org subtrees have the most architecture documentation? (Rachel Hansen's L4 reports dominate)
- Which leaders own critical systems but have no architecture evidence? (gap analysis)
- What is the management chain for a specific payment rail? (trace from architecture note → person → reports_to chain)

**Recommendation:** The folio team should consider a generic "external data merge" hook — a way to enrich entity stubs with data from external sources (org charts, CMDB, ServiceNow, etc.) without requiring custom scripts.

### 3.7 Diagram notes dominate the graph visual

The library has 1,524 diagram notes vs. 115 evidence notes. In Obsidian's graph view, the diagram-to-evidence star topology visually overwhelms all other connections. Entity hub connections and org hierarchy chains are present but invisible at the global zoom level.

**Recommendation for Obsidian users:** Filter diagram notes out of the graph view (`-path:diagram`) to see the entity/relationship topology. Or use local graph view on specific entity hubs.

**Recommendation for folio team:** Consider adding a `.obsidian/graph.json` configuration file to the library that pre-sets useful graph filters (exclude diagrams, color-code by entity type, etc.).

---

## 4. Post-Enrichment Checklist (for other libraries)

Based on this production test, here is the recommended post-enrichment workflow:

1. **Run `folio status --refresh`** before enrichment if the library was built by an older folio-love version (ensures `type` field is populated in registry)
2. **Run `folio enrich --dry-run`** to verify eligible count and check for diagram note leakage
3. **Scoped test** on 5-15 notes before full library run
4. **Full library run** — budget ~10 seconds per note at current API throughput
5. **Review relationship proposals** — confirm plausible ones by adding canonical frontmatter fields, then re-run `folio enrich` to generate `## Related` sections
6. **Generate entity stubs** — essential for Obsidian graph connectivity. Use the script at `ada-folio/scripts/generate_entity_stubs.py` as a template
7. **Merge external data** (optional) — if org charts, CMDB data, or other identity sources are available, merge them into person entity stubs for organizational hierarchy edges
8. **Configure Obsidian graph filters** — exclude diagram notes to see the entity/relationship topology

---

## 5. Files and Commits

| Artifact | Path |
|----------|------|
| Entity stub generation script | `ada-folio/scripts/generate_entity_stubs.py` |
| Entity stubs | `ada-folio/library/_entities/` (1,134 files) |
| Enriched evidence notes | `ada-folio/library/` (115 notes with `_llm_metadata.enrich`) |
| Proxy org chart data | `ada-output/export-data/org_chart.json` |
| This report | `ada-output/learnings/folio_enrich_production_test_report.md` |

| Commit | Description |
|--------|-------------|
| `fd65fa1` | `folio enrich: production library first pass (115 notes)` |
| `8acf57f` | `graph connectivity: entity stubs + relationship confirmation + org hierarchy` |

---

## Appendix: Data Lineage

### Source Files

- `ada-folio/library/registry.json` — 115 registered decks, schema version 1
- `ada-folio/folio.yaml` — library config with LLM routing (default: `anthropic_sonnet4`)
- `ada-output/export-data/org_chart.json` — 1,531 people proxy org chart from ITSM data
- `ada-folio/library/**/*.md` (excluding `_entities/` and `*-diagram-p*.md`) — 115 evidence notes (after enrichment: 160 `.md` files at non-diagram, non-entity level)

### Joins

1. **Entity mentions → Entity stubs:** Entity names from `_llm_metadata.enrich.axes.entities.mentions[].text` matched to stub filenames in `library/_entities/`
2. **Person entities → Org chart:** Fuzzy name matching (case-insensitive, `Last, First` transposition, partial last-name match) against `org_chart.json` `people` keys and `name_variants`
3. **Org chain completion:** Recursive `reports_to` traversal up to L2, creating stubs for all managers in the chain

### Filters

- Enrichment eligibility: `registry.type in ("evidence", "interaction")`, excludes diagram notes
- Entity noise filter: names < 2 characters or in noise list (N/A, TBD, Unknown, etc.) excluded
- Org chart match: ambiguous matches (multiple candidates for a last name) excluded; only unique matches accepted

### Calculations

- **Enrichment rate:** 115 eligible / 115 registered = 100% (after registry fix)
- **Body protection rate:** 26 / 115 = 23% (managed sections not identifiable)
- **Relationship proposal rate:** 6 / 115 = 5%
- **Person-to-org match rate:** 60 / 217 = 28% (35 direct folio matches + 32 chain completions, some stubs serve both roles; denominator includes chain-only stubs)
