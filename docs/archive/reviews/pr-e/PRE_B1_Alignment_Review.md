# PR E Spec Review: Reviewer 2 — Alignment Review

**Spec:** `docs/specs/folio_context_docs_tier3_closeout_spec.md` (Rev 1, draft)
**Review date:** 2026-03-30
**Focus:** Compliance with approved documents, constraint verification, consistency with shipped baseline.

---

## Ontology Schema Audit

| Ontology Field | Required for `type: context`? | Present in Spec D5? | Match? | Notes |
|---|---|---|---|---|
| `id` | Yes (universal, Section 12.1) | Yes | MATCH | |
| `type` | Yes (universal) | Yes (`context`) | MATCH | |
| `subtype` | Yes (universal) | Yes (`engagement`) | MATCH | `engagement` is a legal context subtype per Section 4.1 |
| `status` | Yes (universal) | Yes (`active`) | MATCH | `active` is a legal status value |
| `authority` | Yes (universal) | Yes (`aligned`) | MATCH | `aligned` is a legal authority value; ontology example also uses `aligned` for context |
| `curation_level` | Yes (universal, Auto) | Yes (`L1`) | MATCH | L1 is legal per 12.1; ontology example also uses L1 |
| `tags` | Yes at L1+ (universal) | Yes | MATCH | |
| `review_status` | Yes (universal, Auto, Section 12.7) | **ABSENT from D5** | **MISMATCH** | Ontology 12.7 lists as universal with `clean` default. D5 explicitly excludes `review_flags` but does not mention `review_status` at all. |
| `review_flags` | Yes (universal, Auto, Section 12.7) | Explicitly excluded | PARTIAL | Ontology says universal; spec excludes arguing FR-700 applies only to generated content. |
| `extraction_confidence` | Auto, "all with LLM analysis" (12.7) | Explicitly excluded | ACCEPTABLE | Context docs have no LLM analysis. Spec should state `null`, not absent. |
| `client` | Yes at L1+ for context (12.2) | Yes | MATCH | |
| `engagement` | **Optional** for context (12.2) | Yes (required) | STRICTER | Ontology says optional for context. Acceptable for `subtype: engagement` but should be documented as subtype-scoped tightening. |
| `industry` | No (optional, 12.2) | Yes (optional) | MATCH | |
| `service_line` | No (optional, 12.2) | Yes (optional) | MATCH | |
| `created` | Yes (universal, Auto) | Yes | MATCH | |
| `modified` | Yes (universal, Auto) | Yes | MATCH | |
| `title` | Yes (universal) | Yes | MATCH | |
| `team` | Not in universal schema | ABSENT | DEVIATION | Ontology example includes `team` in context frontmatter; spec moves to body. Valid design choice (D6). |
| `sow_reference` | Not in universal schema | ABSENT | DEVIATION | Same rationale as `team`. |

**Key finding on `review_status`:** The ontology declares `review_status`, `review_flags`, and `extraction_confidence` as universal fields. The spec excludes all three. The rationale is reasonable but contradicts the ontology's universal declaration. Resolution: either amend the ontology to carve out human-authored types, or include `review_status: clean`, `review_flags: []`, `extraction_confidence: null`.

**Key finding on ID convention:** The ontology Section 8.2 shows `clienta_ddq126_context_engagement` with "(no date needed)." The spec D4 introduces a date-based pattern. The spec acknowledges this but does not include the ontology amendment in required deliverables.

---

## Constraint Verification Table

| Constraint Source | Constraint | Spec Compliance | Status |
|---|---|---|---|
| Ontology 12.1 | `status` values: `active`, `complete`, `stale`, `archived` | Spec uses `active` | PASS |
| Ontology 12.1 | `authority` values: `captured`, `analyzed`, `aligned`, `decided` | Spec uses `aligned` | PASS |
| Ontology 12.1 | `curation_level` values: `L0`, `L1`, `L2`, `L3` | Spec uses `L1` | PASS |
| Ontology 12.2 | `engagement` optional for context | Spec requires for `subtype: engagement` | PASS (subtype-scoped) |
| Ontology 4.1 | Context subtypes: `engagement`, `client_profile`, `workstream` | Spec uses `engagement` | PASS |
| Ontology 8.2 | Context IDs: "no date needed" | Spec adds date | DEVIATION |
| Ontology 12.7 | `review_status` universal | Spec excludes | DEVIATION |
| PRD FR-403 | Registry tracks all managed docs | Spec adds context to registry | PASS |
| PRD FR-505 | Refresh skips interaction with rerun guidance | Spec adds similar context skip | CONSISTENT |
| Roadmap Week 21-22 | Context docs + end-to-end test | Spec delivers both | PASS |
| Roadmap Tier 3 Exit | "Context documents provide engagement scaffolding" | Spec delivers | PASS |
| Roadmap Tier 3 Exit | "Full engagement lifecycle tested end-to-end" | Spec delivers integration test | PASS |
| Baseline memo | PR #39 provenance merged baseline | Spec treats as merged (Section 5.1) | PASS |
| Enrich spec D1 | Enrich processes `evidence` or `interaction` only | Spec D11 consistent | CONSISTENT |
| Provenance spec D2 | Provenance is evidence-only via `supersedes` | Spec D11 consistent | CONSISTENT |

---

## Registry Contract Comparison

| Field | Evidence Entry | Interaction Entry | Context Entry (D9) | Notes |
|---|---|---|---|---|
| `id` | Required (positional) | Required | Required | Same |
| `title` | Required (positional) | Required | Required | Same |
| `markdown_path` | Required (positional) | Required | Required | Same |
| `deck_dir` | Required (positional) | Required | Required | Same |
| `source_relative_path` | Required (`str`) | `source_transcript` | **"absent or null"** | **CRITICAL**: Positional required field in `RegistryEntry`. Cannot be `None` without dataclass change. |
| `source_hash` | Required (`str`) | Required | **"absent or null"** | Same problem — positional required field. |
| `version` | Required (`int`) | Required | **Unspecified** | Positional required field. Context docs have no version. Spec omits from both stored and absent lists. |
| `converted` | Required (`str`) | Required | **Unspecified** | Positional required field. Context docs are not converted. Same omission. |
| `source_type` | Optional | Optional | **"absent or null"** | OK — already Optional in dataclass. |
| `type` | Optional (inferred) | Optional | `"context"` | Consistent |
| `subtype` | Not in dataclass | Not in dataclass | Spec says stored | **GAP**: `RegistryEntry` has no `subtype` field. Schema addition needed. |
| `client` | Optional | Optional | Stored | Same |
| `engagement` | Optional | Optional | Stored | Same |
| `authority` | Optional | Optional | Stored | Same |
| `curation_level` | Optional | Optional | Stored | Same |
| `modified` | Optional | Optional | Stored | Same |
| `staleness_status` | Default `"current"` | Default `"current"` | `current`/`missing` | Consistent |

---

## Enrich/Provenance Scope Analysis

**Enrich eligibility** (`enrich.py:286`):
```python
if entry.type not in ("evidence", "interaction"):
    continue
```
Explicit allowlist. Context docs excluded. **Spec D11 is correct.**

**Provenance eligibility** (`provenance.py:850`):
```python
if entry.type != "evidence":
    continue
```
Explicit allowlist. Context docs excluded. **Spec D11 is correct.**

**Refresh eligibility** (`cli.py:992`):
```python
if entry.type == "interaction":
    skipped_interactions.append(entry)
    continue
```
**Blocklist pattern, not allowlist.** Only blocks `interaction`. Context entries fall through to `refresh_entry_status()` → `check_staleness()` → crash on null source path. **Spec D10 correctly identifies skip behavior needed, but current code would crash.**

**Registry rebuild** (`registry.py:137`):
```python
if source_field is None or "source_hash" not in fm:
    continue
```
Context docs silently skipped during rebuild. **Section 7.4 correctly requires change but spec should emphasize this is a required code modification.**

---

## Tier 3 Exit Criteria Cross-Reference

| Roadmap Criterion | Spec Coverage | Evidence Required | Sufficient? |
|---|---|---|---|
| `folio ingest` converts transcript in <60s | Existing baseline | Real timed ingest on McKinsey machine | YES |
| Entity registry tracks people, departments, systems | Existing baseline | `folio entities` output and counts | YES |
| Name resolution works for common cases | Existing baseline | Existing evidence plus validation | YES |
| `folio enrich` adds tags and links | Existing baseline | Production test report plus spot checks | YES |
| Retroactive provenance works on `supersedes` pairs | Existing baseline (PR #39) | PR #39 baseline plus production/closeout evidence | YES |
| Context documents provide engagement scaffolding | **PR E deliverable** | Real populated context doc | YES |
| Full lifecycle tested end-to-end | **PR E deliverable** | Integration test plus closeout narrative | YES |

All PRD exit criteria are covered. No unauthorized additions.

---

## Deviation Report

| # | Document | Section | Expected | Actual | Severity |
|---|----------|---------|----------|--------|----------|
| 1 | Ontology | 8.2 (ID) | "no date needed" | Spec D4 adds date | Minor |
| 2 | Ontology | 12.7 (Trust) | `review_status`, `review_flags`, `extraction_confidence` universal | Spec excludes all three | **Major** |
| 3 | Ontology | 4.1 (Example) | `team`, `sow_reference` in frontmatter | Spec moves to body | Minor |
| 4 | Code | `registry.py:20-30` | `source_relative_path`, `source_hash`, `version`, `converted` required | Spec says "absent or null" | **Critical** |
| 5 | Code | `registry.py:137` | `rebuild_registry` requires `source_hash` | Spec 7.4 says rebuild must recognize context docs | **Critical** |
| 6 | Code | `cli.py:992` | Refresh only skips `interaction` | Spec D10 says refresh skips context | **Major** |
| 7 | Code | `RegistryEntry` | No `subtype` field | Spec D9 stores `subtype` | **Major** |
| 8 | PRD | FR-403 | Registry tracks source-backed docs | Spec adds source-less docs | Minor (11.1 addresses) |
| 9 | Roadmap | Status table | "PR D is next slice" | PR D is merged | Minor (5.2 addresses) |
| 10 | Spec | D5 vs 7.2 | Date formats | Evidence uses ISO-8601; context uses YYYY-MM-DD | Minor |
| 11 | Kickoff | Line 94 | "PR D: Next feature slice" | PR D shipped | Minor (5.2 addresses) |

---

## Issues by Severity

**Critical:**

1. **RegistryEntry dataclass incompatibility (Deviation #4).** Four positional required fields cannot be null without changing the dataclass signature. The spec must explicitly call out the schema migration.

2. **Registry rebuild drops context docs (Deviation #5).** `rebuild_registry()` filter is a hard gate on `source_hash`. The spec identifies the requirement but must emphasize this as a required code change.

**Major:**

3. **Ontology universal fields excluded (Deviation #2).** `review_status`, `review_flags`, `extraction_confidence` declared universal. Either amend ontology or include with clean defaults.

4. **Refresh would crash on context entries (Deviation #6).** Blocklist pattern, not allowlist. Context entries fall through to crash.

5. **RegistryEntry lacks `subtype` field (Deviation #7).** `entry_from_dict()` silently drops unknown keys.

**Minor:**

6. Context ID date convention (Deviation #1). Ontology amendment should accompany PR E.
7. Stale governance surfaces (Deviations #9, #11). Acknowledged but sync not committed as deliverable.
8. `team`/`sow_reference` absent from frontmatter (Deviation #3). Defensible per D6.
9. Date format inconsistency (Deviation #10). Minor cross-type mismatch.

---

## Verdict

**Request Changes.**

The product design is sound and the Tier 3 exit criteria mapping is complete. However, the two critical issues (RegistryEntry incompatibility and rebuild_registry) represent real implementation risks that must be explicitly acknowledged as required code changes. The ontology deviation on universal review fields must be resolved before implementation begins.
