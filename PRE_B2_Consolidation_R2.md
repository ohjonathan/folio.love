# PR E Spec Review Consolidation (Round 2)

**Spec:** `docs/specs/folio_context_docs_tier3_closeout_spec.md` (Rev 1, revised)
**Review date:** 2026-03-30

---

## 1. Verdict Summary Table

| Reviewer | Role | R1 Verdict | R2 Verdict | Blocking Issues |
|----------|------|------------|------------|-----------------|
| Reviewer 1 | Peer | Request Changes | **Approve** | None |
| Reviewer 2 | Alignment | Request Changes | **Approve** | None |
| Reviewer 3 | Adversarial | Request Changes | **Approve** | None |

**Overall Status: Ready for Implementation**

---

## 2. Round 1 Issue Disposition (All Issues)

### Blocking Issues

| Issue | R1 Status | R2 Status | Resolution |
|-------|-----------|-----------|------------|
| B-1: `RegistryEntry` dataclass incompatibility | Critical (3/3) | **RESOLVED** (3/3) | D9A enumerates every required field change (`source_relative_path`, `source_hash`, `version`, `converted` become `Optional` with defaults), mandates call-site audit, specifies `entry_from_dict()`/`to_dict()` round-trip behavior. |
| B-2: `rebuild_registry()` drops context docs | Critical (3/3) | **RESOLVED** (3/3) | D9A explicitly requires context-note recognition in rebuild and preservation during corruption-recovery. Section 7.4 reiterates. |

### Should-Fix Issues

| Issue | R2 Status | Resolution |
|-------|-----------|------------|
| S-1: `folio scan` crash | **RESOLVED** | D9A call-site guards (lines 401-402); D10 safe-scan behavior; assertion 8.6.5 |
| S-2: `folio refresh` crash | **RESOLVED** | D9A (lines 403-404); D10 skip-before-resolution; assertion 8.6.6 |
| S-3: `RegistryEntry` lacks `subtype` | **RESOLVED** | D9A (line 366) adds `subtype: Optional[str] = None` |
| S-4: Ontology universal fields excluded | **RESOLVED** | D5 now includes `review_status: clean`, `review_flags: []`, `extraction_confidence: null`. Template examples updated. |
| S-5: No risk assessment section | **RESOLVED** | Section 10 covers registry-contract risk, synthetic-test limitation, closeout honesty, compatibility posture. |
| S-6: No unit test plan | **RESOLVED** | Section 8.7 adds 7 minimum unit categories covering registry round-trip, rebuild, refresh, validation, status type counting. |
| S-7: Assertion 5 no scenario step | **RESOLVED** | Scenario 8.2 expanded to 14 steps including refresh (13), scan (12), status --refresh (11). |
| S-8: Assertion 10 underspecified | **RESOLVED** | Now assertion 11: specifies `confirm-doc` yields confirmed `provenance_links` entry. Seeded notes use canonical `supersedes`. |
| S-9: Unfalsifiable gate semantics | **RESOLVED** | Section 9.6 hard-fail conditions. Section 9.7 anti-rubber-stamp rules. Lifecycle test cannot be waived. |
| S-10: `validate_frontmatter.py` rejection | **RESOLVED** | D12 enumerates all field exemptions for context branch. |
| S-11: `version`/`converted` omitted from D9 | **RESOLVED** | D9 line 354 and D5 lines 274-275 explicitly list both. |
| S-12: Self-referential validation | **RESOLVED** | Scenario now exercises `status --refresh`, `scan`, `refresh` (pre-existing code paths). Hard-fail conditions require these complete without crashing. |

### Minor Issues

| Issue | R2 Status |
|-------|-----------|
| m-1: ID convention ontology amendment | **RESOLVED** — Section 12.2 adds ontology as sync target |
| m-2: Status per-type is new functionality | **RESOLVED** — Clearly specified in D10 and assertions |
| m-3: Exit criteria from pre-existing evidence | **RESOLVED** — Section 9.3 requires current corroborating evidence; 9.7 blocks PASS from historical reports alone |
| m-4: Engagement type guidance | **RESOLVED** — Line 610-611 adds taxonomy values |
| m-5: Closeout prompt purpose | **RESOLVED** — Lines 812-814 define content |
| m-6: Implicit linkage framing | Accepted as v1 design — no spec change needed |
| m-7: Governance sync enforcement | **RESOLVED** — Section 12.2 enumerates specific files |
| m-8: `_infer_missing_entry_type` default | **RESOLVED** — D9A line 372 requires explicit `type: context` |
| m-9: Schema version increment | **RESOLVED** — D9A line 365 bumps to v2 |

---

## 3. Adversarial Assumption Attack Disposition

| # | Attack | R1 | R2 | Notes |
|---|--------|----|----|-------|
| AA-1 | Registry generalization is safe | LIVE | **NEUTRALIZED** | D9A is comprehensive |
| AA-2 | Implicit linkage is sufficient | LIVE | **ACKNOWLEDGED** | Accepted v1 limitation, not a gap |
| AA-3 | Lifecycle test proves Tier 3 works | LIVE | **SUBSTANTIALLY MITIGATED** | Unit test plan + expanded scenario + production closeout evidence requirement |
| AA-4 | Closeout will be honest | LIVE | **NEUTRALIZED** | Hard-fail conditions + anti-rubber-stamp rules |
| AA-5 | PR #39 is merged baseline | LIVE | **NEUTRALIZED** | Section 12.2 sync targets specified |
| AA-6 | No blocking open questions | LIVE | **NEUTRALIZED** | Section 13 explicitly gates on schema/validator/testing acceptance |
| AA-7 | Three clean parts | LIVE | **SUBSTANTIALLY MITIGATED** | External-observable command anchors in steps 11-13 |

---

## 4. Failure Mode Disposition

All 6 failure modes from Round 1 are now **specified with pending implementation**:

| FM | Round 2 Status | Spec Coverage |
|----|---------------|---------------|
| FM-1: `status --refresh` crash | D9A lines 394-396; assertion 8.6.4 |
| FM-2: `scan` crash / `source: None` print | D9A lines 401-407; assertion 8.6.5 |
| FM-3: `refresh` crash before type check | D9A lines 403-404; D10 lines 433-437; assertion 8.6.6 |
| FM-4: `rebuild_registry()` drops context docs | D9A lines 385-391; unit test category in 8.7 |
| FM-5: `validate_frontmatter.py` rejects context docs | D12 lines 456-471; unit test category in 8.7 |
| FM-6: `entry_from_dict()` crash on source-less row | D9A lines 367-376; unit test in 8.7 |

---

## 5. New Issues from Round 2

No critical or major new issues. Minor/informational items only:

| # | Issue | Flagged By | Severity | Action |
|---|-------|------------|----------|--------|
| N-1 | `reconcile_from_frontmatter()` needs `subtype` added to authoritative list — D9A specifies it but could be more explicit | R1, R2 | Minor | Implementation detail; D9A mandate covers it |
| N-2 | Ontology Section 4.1 context example is internally stale (missing v2.1 universal review fields) — pre-existing, not caused by PR E | R2 | Informational | Section 12.2 sync scope should broaden to include this example |
| N-3 | `to_dict()` strips `None` values including `extraction_confidence: null` from registry JSON — round-trip is safe but semantic distinction between absent and explicit-null is lost | R3 | Negligible | Frontmatter retains the value; registry storage loss is cosmetic |
| N-4 | Hard-fail conditions lack machine-enforced gate (only CI lifecycle test is mechanically enforced) — consistent with Tier 1/2 pattern | R3 | Accepted | Matches established closeout model |
| N-5 | Section 8.7 unit test categories lack minimum counts per category | R3 | Low | Categories are specific enough for good-faith implementation |

---

## 6. Agreement Analysis

**Unanimous (3/3):**
- All Round 1 blocking issues are resolved
- D9A is the keystone addition that makes the spec implementable
- The spec's product design was already sound; the revision fixed the engineering specification
- The spec is now ready for implementation

**Risk assessment:**
- Round 1: **HIGH** (unspecified crash paths, missing contracts)
- Round 2: **LOW-MEDIUM** (residual implementation-execution risk only)

---

## 7. Decision Summary

**Overall Status: Ready for Implementation**

The CA addressed every blocking, should-fix, and most minor issues from Round 1 in a single comprehensive revision. The keystone addition is D9A (Required Registry Schema and Compatibility Changes), which converts the registry generalization from an implicit assumption into an explicit implementation contract. All seven adversarial assumption attacks are either neutralized or acknowledged. All six failure modes are specified with corresponding test coverage.

The remaining risk is implementation-execution quality, which is the correct residual risk for a spec reviewed to this depth.
