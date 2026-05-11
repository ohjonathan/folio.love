# PR E Spec Review: Reviewer 1 — Peer Review

**Spec:** `docs/specs/folio_context_docs_tier3_closeout_spec.md` (Rev 1, draft)
**Review date:** 2026-03-30
**Focus:** Completeness, quality, clarity, implementability.

---

## Review Framework Results

| Section | Assessment |
|---------|-----------|
| **Structural completeness** | The spec has: overview (1), scope/goals (3), non-goals (4), technical design (5-7), open questions (12), test strategy (8), and an exclusion list (8.7). **Missing:** No explicit risk assessment section. No explicit migration/compatibility section addressing the registry schema change itself — D9 describes the target state but not how to get there from the current dataclass. |
| **Developer test** | A developer would get stuck on registry generalization. The spec describes the desired registry row shape for context docs but does not address the current `RegistryEntry` dataclass constraints. A developer would immediately hit `TypeError` when trying to construct an entry without `source_relative_path`, `source_hash`, `version`, or `converted`. |
| **Template completeness** | The template at 7.3 is complete and well-structured. Body sections cover the obvious engagement-scaffolding concerns. No major gaps for a human editor. Minor: no guidance on how to handle multi-workstream engagements within a single engagement context doc. |
| **Test coverage** | Scenario steps (8.2) cover 9 steps. Assertions (8.6) cover 11 items. There are mapping gaps detailed below. The biggest gap: no assertion covers `folio scan` behavior with context docs present, though D10 specifies scan should ignore them. |
| **Closeout package** | The closeout report structure (9.2) is reasonably complete. Evidence expectations (9.3) are concrete enough to be actionable. Exit criteria mapping (9.4) is the weakest part — some criteria point to pre-existing evidence without a mechanism to verify it is still valid at closeout time. |

---

## Specific Investigation Results

### 1. Registry Generalization Gap Analysis

This is the most critical finding in the review.

The `RegistryEntry` dataclass at `folio/tracking/registry.py` lines 20-43 defines **four required, non-optional fields** that context docs cannot provide:

- `source_relative_path: str` (line 27) — no default value, required positional
- `source_hash: str` (line 28) — no default value, required positional
- `version: int` (line 29) — no default value, required positional
- `converted: str` (line 30) — no default value, required positional

The spec says at D9: "source_relative_path, source_hash, source_type, and converted are absent or null." But the current dataclass **cannot accept null for these fields** because they are typed as `str` and `int` with no `Optional` wrapper and no default value.

The following code paths will break or behave unexpectedly with null/absent source fields:

- **`rebuild_registry()`** (line 137): explicitly **skips** any note without source tracking fields. Context docs would be invisible to registry rebuilds.
- **`refresh_entry_status()`** (line 259): calls `check_staleness(md_path, entry.source_relative_path, entry.source_hash)` — if `source_relative_path` is null/empty, `resolve_source_path` will construct a nonsensical path.
- **`resolve_entry_source()`** (line 248): `(md_dir / entry.source_relative_path).resolve()` — will crash or produce garbage if `source_relative_path` is empty/null.
- **`folio scan`** (cli.py line 858): calls `resolve_entry_source` for every registry entry — will fail on context docs.
- **`folio scan` hash comparison** (cli.py line 900): `current_hash != entry.source_hash` — will compare against empty/null.
- **`folio refresh`** (cli.py line 1023): calls `resolve_entry_source` — will fail on context docs.
- **`folio status` missing-source display** (cli.py line 810): prints `entry.source_relative_path` — would print nonsense for context docs.

The spec says "scan ignores them; refresh skips them" (D10) but does not enumerate exactly which code paths need guards.

### 2. Integration Test Assertion Coverage vs. Scenario Steps

| Scenario Step | Corresponding Assertion(s) |
|--------------|---------------------------|
| Step 1: `folio context init` | Assertions 1, 2, 3 |
| Step 2: seed evidence notes | (Setup, no direct assertion) |
| Step 3: `folio entities import` | (Covered indirectly by assertions 6, 7, 8) |
| Step 4: confirm entities | (Setup for assertion 6) |
| Step 5: `folio ingest` | Assertion 6 |
| Step 6: `folio entities generate-stubs` | Assertions 7, 8 |
| Step 7: `folio enrich` | Assertion 9 |
| Step 8: `folio provenance` | Assertion 10 |
| Step 9: `folio status` | Assertion 4, 11 |

Gaps:

- **Assertion 5 ("folio refresh skips context doc") has NO corresponding scenario step.** The scenario never calls `folio refresh`.
- **Assertion 10 is vague.** What specifically should the test assert about provenance output in a synthetic test? The provenance pipeline requires canonical confirmed `supersedes` in frontmatter (per provenance spec D2).
- **`folio scan` behavior is unasserted** despite D10 specifying scan behavior and scan being a crash risk.

### 3. Closeout Exit Criteria Honesty

| Criterion | Rubber-stamp risk |
|-----------|-------------------|
| "folio ingest converts transcript in <60s" | **Concrete and falsifiable.** Good. |
| "Entity registry tracks people, departments, systems" | **Moderate risk.** "Existing shipped behavior plus validation evidence" could mean pointing to PR #34 tests. |
| "Name resolution works for common cases" | **Moderate risk.** Same concern — pre-existing evidence, not new closeout-time validation. |
| "folio enrich adds tags and links" | **Low risk.** Points to the concrete production test report. |
| "Retroactive provenance infrastructure works" | **Moderate risk.** The word "or" in "production or closeout-time provenance validation evidence" is doing a lot of work. |
| "Context documents provide engagement scaffolding" | **Concrete.** "A real populated context doc." |
| "Full lifecycle tested end-to-end" | **Concrete.** Integration test plus production closeout narrative. |

Criteria 2, 3, and 5 could pass by pointing to already-merged PRs without any new validation.

### 4. Missing Risk Assessment

The spec has no risk assessment section. Unacknowledged risks:

1. Registry schema change breaking existing code paths (at least 7 code paths)
2. Integration test too synthetic to catch real problems
3. Closeout package as ceremony rather than quality gate
4. Context doc ID convention conflicts with ontology (ontology says "no date needed"; spec adds date)
5. `version` and `converted` fields for context docs — required fields not mentioned in D9

---

## Issues by Severity

**Critical (max 3):**

- **[C1] `RegistryEntry` dataclass requires `source_relative_path: str`, `source_hash: str`, `version: int`, and `converted: str` as non-optional fields with no defaults.** Context docs cannot provide these. The spec describes the target row shape (D9) but does not address the dataclass change required, nor does it enumerate the 7+ downstream code paths needing null guards. `registry.py` lines 27-30.

- **[C2] `rebuild_registry()` explicitly skips notes without `source_hash` (line 137).** Context docs will be invisible to registry rebuilds — directly contradicting Section 7.4. The spec does not acknowledge this existing code behavior.

- **[C3] No risk assessment section.** The spec has no risk section despite introducing a structural change to the core data model, a new document type interacting with 5+ CLI commands, and a closeout package that could be ceremonial.

**Major:**

- **[M1] Assertion 5 has no corresponding scenario step in 8.2.** The scenario never calls `folio refresh`.
- **[M2] Assertion 10 is underspecified.** Does not specify whether seeded notes have canonical `supersedes` or merely proposed.
- **[M3] `folio scan` crash risk is unaddressed.** `scan` calls `resolve_entry_source()` on every entry (cli.py:858). No type filter. Context docs will crash it.
- **[M4] `version` and `converted` are required `RegistryEntry` fields not mentioned in D9.** Silent omission in the schema specification.

**Minor:**

- **[m1]** Context doc ID convention diverges from ontology without amendment.
- **[m2]** Exit criteria 2, 3, 5 can pass from pre-existing evidence without new closeout-time validation.
- **[m3]** Template "Engagement type: TBD" has no guidance on valid values.
- **[m4]** `folio status` per-type summary line is new functionality not called out as a status implementation change.
- **[m5]** Closeout prompt artifact (9.1) has no described content or purpose.

---

## Positive Observations

1. Non-goals table (Section 4) is exceptionally well-defined.
2. Decision documentation (D1-D12) is thorough with clear rationale.
3. Template example at 7.3 is complete and directly implementable.
4. Baseline and governance documentation (Section 5) is honest about stale surfaces.
5. Closeout package includes "what was awkward" section — signals maturity.
6. Choice to seed evidence notes rather than calling `folio convert` (8.3) is well-reasoned.

---

## Verdict

**Request Changes.**

The spec cannot be implemented as written without the developer independently discovering and solving the `RegistryEntry` dataclass incompatibility. The four required non-optional fields and the `rebuild_registry()` skip logic represent a structural gap between the spec's described target state and the actual code. The missing risk assessment, `folio scan` crash risk, and scenario/assertion mapping gaps are secondary but meaningful.
