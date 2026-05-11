# PR E Spec Review Consolidation (Round 1)

**Spec:** `docs/specs/folio_context_docs_tier3_closeout_spec.md` (Rev 1, draft)
**Review date:** 2026-03-30

---

## 1. Verdict Summary Table

| Reviewer | Role | Verdict | Blocking Issues |
|----------|------|---------|-----------------|
| Reviewer 1 | Peer | Request Changes | RegistryEntry dataclass incompatibility; rebuild_registry drops context docs; no risk assessment |
| Reviewer 2 | Alignment | Request Changes | RegistryEntry dataclass incompatibility; rebuild_registry drops context docs |
| Reviewer 3 | Adversarial | Request Changes | RegistryEntry dataclass contract break; rebuild_registry silently drops context docs |

---

## 2. Blocking Issues

All three reviewers independently flagged the same two critical defects. This is the strongest consensus signal in the review.

| Issue ID | Description | Flagged By | Category | Action Required for CA |
|---|---|---|---|---|
| B-1 | **`RegistryEntry` dataclass incompatibility.** `source_relative_path: str`, `source_hash: str`, `version: int`, and `converted: str` are required positional fields with no defaults at `registry.py:21-43`. Context docs cannot provide these. The spec says "absent or null" (D9) without acknowledging the dataclass break. At least 6 crash points: `refresh_entry_status()`, `resolve_entry_source()`, `check_staleness()`, `folio scan`, `folio status --refresh`, and `folio refresh`. | R1 (C1), R2 (Critical #1), R3 (Critical #1) | Registry schema | Add a "Required Schema Changes" subsection listing: (a) which `RegistryEntry` fields become `Optional` with defaults, (b) every downstream code path that accesses source fields and needs null guards, (c) the `entry_from_dict()`/`to_dict()` round-trip behavior for source-less entries. |
| B-2 | **`rebuild_registry()` silently drops context docs.** Lines 136-137 require `source`/`source_transcript` + `source_hash`. Context docs have neither and will be skipped. Directly contradicts Section 7.4. Called from recovery paths in `upsert_entry()`, `status`, `scan`, and `refresh`. | R1 (C2), R2 (Critical #2), R3 (Critical #2) | Registry rebuild | Spec must explicitly call out this as a required code change to the rebuild filter, not just a behavioral expectation. The rebuild is the corruption-recovery path — losing context docs on rebuild is data loss. |

---

## 3. Should-Fix Issues

| Issue ID | Description | Flagged By | Action |
|---|---|---|---|
| S-1 | **`folio scan` crash on context entries.** `scan` calls `resolve_entry_source()` on every registry entry (cli.py:858). No type filter. D10 says "scan unchanged" but scan cannot be unchanged. | R1 (M3), R3 (FM-2) | Add to schema changes subsection — scan needs type skip or guard. |
| S-2 | **`folio refresh` crash before type check.** Current code only blocks `interaction` (cli.py:992). Context entries fall through to `refresh_entry_status()` → crash. | R2 (Major #4), R3 (FM-3) | Add context skip matching the interaction skip pattern. |
| S-3 | **`RegistryEntry` lacks `subtype` field.** D9 says context entries store `subtype`. Dataclass has no such field. `entry_from_dict()` silently drops it. | R2 (Major #5) | Add to schema changes subsection. |
| S-4 | **Ontology universal fields excluded without amendment.** `review_status`, `review_flags`, `extraction_confidence` declared universal (Section 12.7). Spec D5 excludes all three. | R2 (Major #3) | Either include with clean defaults (`review_status: clean`, `review_flags: []`, `extraction_confidence: null`) or commit to ontology amendment. |
| S-5 | **No risk assessment section.** Structural change to core data model with no risk register. | R1 (C3), R3 (Blind Spot #3) | Add risk subsection: registry generalization crash points, synthetic test gap, closeout-as-ceremony. |
| S-6 | **No unit test plan.** Provenance spec had 15 test plan subsections. PR E has one integration test with 11 assertions and zero unit test requirements. | R3 (Major #3) | Add unit test plan for: registry round-trip, `check_staleness` bypass, `rebuild_registry` context discovery, refresh skip, `validate_frontmatter` context branch, status type counting, context CLI edge cases. |
| S-7 | **Assertion 5 has no scenario step.** "folio refresh skips context doc" is asserted but `folio refresh` never called in scenario 8.2. | R1 (M1) | Add step 10 to scenario. |
| S-8 | **Assertion 10 underspecified.** "folio provenance produces or maintains expected provenance metadata" — what specifically? Does not specify canonical vs proposed `supersedes` on seeded notes. | R1 (M2) | Specify `supersedes` state on seeded notes and what provenance assertion checks. |
| S-9 | **Unfalsifiable gate semantics.** Gate allows PARTIAL with waiver on every criterion. No FAIL threshold. | R1 (m2), R3 (Major #5) | Define at least one hard-fail condition (e.g., lifecycle test must pass). |
| S-10 | **`validate_frontmatter.py` will reject context docs.** `BASE_REQUIRED_FIELDS` includes `source_hash` (line 18). D12 correctly says add context branch but doesn't enumerate exemptions. | R3 (Major #6) | Enumerate which base required fields need context exemption. |
| S-11 | **`version` and `converted` omitted from D9.** Required non-optional dataclass fields not in D9's stored or absent lists. | R1 (M4), R2 (Registry table) | Add to D9 field enumeration. |
| S-12 | **Self-referential validation.** Closeout evaluates deliverables from the same PR using a test from the same PR. No external anchor. | R3 (Major #4) | Require at least one assertion exercising pre-existing code (e.g., `folio status --refresh` on context entry). |

---

## 4. Minor Issues

| Issue ID | Description | Flagged By |
|---|---|---|
| m-1 | Context ID convention diverges from ontology example (date-based vs date-free). Ontology amendment not in deliverables list. | R1 (m1), R2 (Minor #6) |
| m-2 | `folio status` per-type summary is new functionality not called out as status implementation change. | R1 (m4), R3 (Blind Spot #8) |
| m-3 | Exit criteria 2, 3, 5 can pass from pre-existing evidence without new closeout-time validation. | R1 (m2), R3 (AA-4) |
| m-4 | Template "Engagement type: TBD" has no guidance on valid values. | R1 (m3) |
| m-5 | Closeout prompt artifact (9.1) has no described content or purpose. | R1 (m5) |
| m-6 | "Implicit linkage" framing — no code path uses implicit linkage in v1; non-decision framed as design decision. | R3 (Minor #8) |
| m-7 | Governance sync has no enforcement mechanism. | R3 (Minor #7) |
| m-8 | `_infer_missing_entry_type()` defaults to `"evidence"` — context entry with missing type would be enrich-eligible. | R3 (FM-6) |
| m-9 | Registry schema version (`_SCHEMA_VERSION = 1`) may need increment. | R3 (Blind Spot #2) |

---

## 5. Agreement Analysis

**Strong agreement (3/3 reviewers):**

- **Registry dataclass is the core risk.** All three independently identified `RegistryEntry` field incompatibility and `rebuild_registry()` context-doc loss as the two blocking issues.
- **The spec describes the target state but not the migration path.** D9 says "source-backed fields become optional" without addressing the Python-level dataclass changes, crash points, or affected code paths.
- **The product design is sound.** All three acknowledged the context doc concept, template, and CLI design are well-specified. Problems are in the engineering substrate, not the product vision.

**Strong agreement (2/3 reviewers):**

- Missing risk assessment section (R1, R3)
- Closeout gate too permissive (R1, R3)
- No unit test plan vs prior specs (R1, R3)
- `folio scan` crash risk (R1, R3)
- Ontology `review_status` deviation (R2, R1 implied)

**Disagreements:**

| Topic | Views | Recommendation |
|-------|-------|----------------|
| Severity of missing risk section | R1: Critical (playbook requires it). R3: Major (important but not blocking). R2: did not flag. | Treat as Should-Fix. A risk subsection addressing registry crash points resolves B-1 and S-5 together. |
| Severity of closeout self-referentiality | R3: Major ("grading its own homework"). R1/R2: not flagged. | Preserve R3's concern. Mitigate by requiring one assertion exercising pre-existing code (S-12). |
| Whether implicit linkage is a real design decision | R3: "marketing language for no linkage." R1/R2: accepted D8 as stated. | Preserve R3's framing. No spec change needed — the spec is honest about v1 scope. |
| Synthetic test coverage sufficiency | R3: weak integration coverage. R1: "well-reasoned" choice. | Both views have merit. Synthetic approach is correct for stability; closeout package with real-library evidence is the intended backstop. Acknowledge tradeoff in risk section. |

---

## 6. Required Actions for CA (B.3 Response)

| Priority | Action | Est. Effort | Resolves |
|----------|--------|-------------|----------|
| **P0** | Add "Required Schema Changes" subsection: list `RegistryEntry` fields needing `Optional` defaults, every crash-point code path, `entry_from_dict`/`to_dict` round-trip, `subtype` addition, `version`/`converted` handling | ~1.5h | B-1, B-2, S-1, S-2, S-3, S-11 |
| **P1** | Resolve ontology `review_status`/`review_flags`/`extraction_confidence` deviation: include with clean defaults OR commit to ontology amendment | ~20m | S-4 |
| **P2** | Add risk assessment subsection (registry generalization crash points primary; synthetic test gap secondary; closeout-as-ceremony tertiary) | ~30m | S-5 |
| **P3** | Add unit test plan: registry round-trip, `check_staleness` bypass, `rebuild_registry` context discovery, `refresh` skip, `validate_frontmatter` context branch, `folio status` type counting, context CLI edge cases | ~45m | S-6 |
| **P4** | Fix scenario/assertion mapping: add `folio refresh` step to 8.2, specify `supersedes` state on seeded notes, add `folio scan` assertion | ~15m | S-7, S-8 |
| **P5** | Strengthen gate semantics: define at least one hard-fail condition; enumerate `validate_frontmatter.py` exemptions | ~20m | S-9, S-10 |
| **P6** | Mitigate self-referential validation: require one assertion exercising pre-existing code not authored by PR E | ~15m | S-12 |

**Total estimated CA revision effort: ~3-4 hours**

---

## 7. Positive Observations

All three reviewers independently noted:

- Non-goals table (Section 4) is exceptionally well-defined with sharp boundaries
- Decision documentation (D1-D12) is thorough with clear rationale
- Template example (7.3) is complete and directly implementable
- Baseline and governance documentation (Section 5) is honest about stale surfaces
- Closeout package includes "what was awkward" section — signals maturity
- Enrich/provenance scope boundaries (D11) verified correct per code analysis (`enrich.py:286` type allowlist, `provenance.py:850` evidence-only filter)
- The product design for context docs is sound — issues are in the engineering specification, not the concept

---

## 8. Decision Summary

**Overall Status: Needs Revision**

The spec's product design is solid and well-motivated. The engineering specification for registry generalization — the single most invasive change in PR E — has a gap between the described target state and the actual code that must change. All three reviewers independently converged on this as the blocking defect.

The P0 action (schema changes subsection) is the critical path. Once the spec explicitly enumerates which `RegistryEntry` fields change, which code paths need guards, and how `rebuild_registry()` discovers source-less docs, the remaining issues are addressable as Should-Fix additions in a single revision pass.
