---
id: framework-learnings-v1.1-adoption
created: 2026-04-15
source: folio.love first production adoption (3 slices)
purpose: Feed frameworks/llm-dev-v1/ROADMAP.md v1.2 scope
slices_covered:
  - proposal-review-hardening-v0-6-0 (slice 1, PR #44)
  - proposal-lifecycle-rename-v0-6-1 (slice 2, PR #45)
  - provenance-lifecycle-rename-v0-6-2 (PROV-1, PR #46)
---

# Framework Learnings — llm-dev-v1.1 Production Adoption (folio.love)

Three full lifecycle runs on a real Python codebase. Friction entries F-001 through F-030 are the raw data; this document extracts the six structural lessons that feed v1.2 scope.

---

## 1. Token-fill friction

### Hard to fill

| Token | Difficulty | Why | Friction ref |
|-------|-----------|-----|--------------|
| `<DOC_INDEX_TOOL?>` / `<DOC_INDEX_ACTIVATION?>` / `<DOC_INDEX_ARCHIVE?>` | Medium | Optional in `tokens.md` but mandatory in folio's `AGENTS.md`. Framework doesn't explain how `<DOC_INDEX_ARCHIVE>` interacts with Phase E — the archive command should run AFTER the retro, but nothing says that. Adopter has to infer the ordering. | F-004 |
| `<SCOPE_LOCK_PATHS[]>` / `<NO_TOUCH_PATHS[]>` | Medium | No language-specific guidance. Python's `folio/pipeline/**` vs `folio/pipeline/enrich_data.py` (one file in-scope, dir forbidden) required manual glob reasoning. TS adopters have `src/` conventions; Python adopters have package-dir conventions. Neither is documented. | F-002 |
| `<CARDINALITY_ASSERTIONS[]?>` | Medium | Drafted at manifest time (before Phase A) but Phase A often narrows scope, making assertions stale. Slice 1's `PROPOSAL_LIFECYCLE_STATES` assertion failed at D.6 because the spec deferred it. Rework needed at B.3 Approve time. | F-026 |

### Ambiguous

| Token | Issue | Friction ref |
|-------|-------|--------------|
| `<BRANCH_CONVENTION>` | `tokens.md` shows `feat/<DELIVERABLE_ID>-<PHASE_ID>-<ROLE>-<FAMILY>` but doesn't say whether branch creation is per-phase or single-branch-for-lifecycle. Folio used single branch (simpler); framework implies per-phase. | — |
| `<COMMIT_PREFIX>` | Used `[llm-dev-v1]` as specified, but unclear whether this prefix is for ALL commits or only lifecycle-managed commits. Pre-existing commits on the branch don't use it. | — |

### Unused

| Token | Notes |
|-------|-------|
| `<DELIVERABLE_SLUG>` | Defined but never referenced in any template body. `verify-tokens.sh` warns about it. |
| `<META_CONSOLIDATOR_FAMILY>` | Same — defined, warned, never template-referenced. |
| `<MODEL_ASSIGNMENTS>` | Same. These are manifest-level tokens consumed by the orchestrator, not by worker templates. |
| `<PR_TITLE_PATTERN>` | Same. |
| `<REPO_URL>` | Same. |
| `<STATIC_CHECKS>` | Same. |

**v1.2 action:** Add `orchestrator-only: true` annotation to `tokens.md` for tokens intentionally consumed outside template bodies. Suppresses the `verify-tokens.sh` warning (F-009) and clarifies the token's consumer.

### Missing tokens

| Proposed token | Why needed |
|----------------|-----------|
| `<MANIFEST_DIR>` | Adopter manifests have no blessed home. Folio invented `frameworks/manifests/`. Every first-run adopter reinvents this (F-003, F-008). |
| `<SCOPE_BASE_COMMIT>` | `G-scope-1` gate uses `main..HEAD` which is too broad on multi-slice branches (F-025). A manifest-level base-commit token would scope the diff correctly. |
| `<PRE_A_ROUND_POLICY>` | Pre-A halt behavior (`strict-first-round` vs `default-one-revision-cap`) is buried in operator prose, not machine-checkable (F-016). |

---

## 2. Template gaps

### Where I improvised

| Gap | What I did | Friction ref |
|-----|-----------|--------------|
| **No Pre-A meta-consolidator.** Template 16 has no consolidation step. When 2 reviewers disagreed (gemini Proceed, claude-sub Revise), I wrote an ad-hoc consolidation applying P5 rules borrowed from Template 06. | Wrote `v0.6.0_pre_a_proposal_canonical_verdict.md` as an orchestrator consolidation | F-013 |
| **No B.3/D.3 role available with 3 CLI families.** Template 06 meta-consolidator must be non-author + non-reviewer. With all families already used on B.1, no family was free for B.3. | Orchestrator wrote consolidation directly (F-029 pattern; repeated for slices 2 and PROV-1) | F-023, F-029 |
| **Template 16 artifact naming.** 2-lens postures (Adversarial+Product, Alignment+Technical) don't map to `<phase>_<role>_<family>.md` pattern since both reviewers have role `proposal-reviewer`. | Invented posture-suffix naming: `_claude-sub_adversarial_product.md` | F-012 |
| **Stdout-only CLI output.** Gemini `-p` emits to stdout, can't write files. Worker-session-contract assumes workers write their own artifacts. | Orchestrator captured stdout and wrote files for gemini and codex dispatches | F-015 |

### Halt conditions

| Condition | Fired? | Assessment |
|-----------|--------|------------|
| Pre-A verdict != Proceed | **Fired 2x** (R1, R2) — both operator-rescinded for another round | Correctly calibrated. Operator-rescind is the intended escape hatch. |
| B.3 Round 2 != Approve | **Fired 1x** (R3 halt, operator-rescinded for R4) | Correct but blunt: R3's single remaining blocker was a wording-precision issue (§4.4 "additive" vs §7 "breaking"), not a structural defect. Circuit breaker doesn't distinguish wording from structural (F-022). |
| Template 14 spec-deviation | **Never fired.** All D.4 fixes stayed within spec scope. | Working as designed. |
| Smoke-check failure x3 | **Never fired.** Smoke checks passed on first attempt for all 3 slices. | Working as designed. |

### Halt conditions that SHOULD have fired but didn't

None observed. The circuit breaker and halt conditions all fired at appropriate boundaries.

### Halt condition that fired unnecessarily

The B.3 R3 halt on a 5-minute wording fix (F-022/F-024) is debatable. The circuit breaker treats all "Needs Fixes" equally — a blocker about §4.4 phrasing is treated identically to a blocker about wrong API shape. A severity-aware circuit breaker could distinguish "cosmetic blocker → Approve-with-notes" from "structural blocker → halt." Not necessarily wrong as-is, but the framework should document why it chooses the blunt approach.

---

## 3. Multi-family dispatch friction

### CLI reliability

| Family | CLI | Reliability | Notes | Friction refs |
|--------|-----|-------------|-------|---------------|
| **claude** (author) | `claude` v2.1.110 | High | Agent tool for sub-agents is reliable; background agents complete without issues. File writes work natively. | — |
| **claude-sub** | Agent tool | High | Separate-session isolation works. ~60-120s per review dispatch. File writes work. | — |
| **codex** | `codex exec` v0.116.0 | High | Non-interactive mode via `codex exec "prompt"` works well. Writes files directly. ~60-120s per dispatch. Ontos integration attempted but failed (F-017 area). | — |
| **gemini** | `gemini -p` v0.38.0 | Medium | Rate-limit 429 errors on stderr (F-014) — output still valid after retries. Requires `-y --sandbox false` flags. ~90-180s including retry backoff. Can't write files in headless plan mode — stdout capture required. | F-014, F-015 |

### Context-window pressure

No context-window issues observed. Each review dispatch is self-contained (spec or diff + source files). The largest dispatch was slice 1's Phase B full-spec review — the spec was ~700 lines and all reviewers handled it without truncation. The orchestrator's conversation context is the bottleneck — the original slice 1 session ran to compaction at ~6.5 hours. Slice 2 and PROV-1 were faster (smaller scope).

### Verdict quality differences

| Lens | Family | Quality assessment | Evidence |
|------|--------|--------------------|----------|
| **Adversarial** (claude-sub) | claude-sub | **Adequate for spec review; insufficient for code review.** Caught 9 spec findings in slice 2 (A-1 through A-9) including the provenance.py blocker. But missed B-001 (malformed target_id surfacing) in slice 1 D.1 code review — codex retro caught it. | F-006-confirmed |
| **Adversarial** (codex) | codex | **Strong.** Found B-001 in retro pass (slice 1). Found stale test assertion D2-COD-1 in slice 2. Found raw-dict dual-check gap in PROV-1 spec. Three-for-three on catching things other lenses missed. | F-006-confirmed, D2-COD-1, PROV-1 B-1 |
| **Peer** (codex) | codex | **Strong.** Thorough line-number verification in both slices. Source-audit evidence labels. | — |
| **Alignment** (gemini) | gemini | **Reliable for scope compliance.** All 3 alignment reviews (slice 1, 2, PROV-1) correctly assessed scope narrowing vs parent spec. Zero false positives. | — |
| **Product** (claude-sub) | claude-sub | **Good.** Found the cli.py provenance misidentification (P-1) independently from adversarial. CHANGELOG clarity feedback was actionable. | — |

**Key learning: codex adversarial > claude-sub adversarial for code review.** The training-data diversity between OpenAI's model and Anthropic's model is a real differentiator for adversarial findings. Same-provider adversarial has a blind spot for defects in patterns the provider's model learned to write. This is the single strongest empirical finding from the adoption.

---

## 4. Verify-script accuracy

### Did verify-all.sh catch real issues?

**Yes — indirectly.** `verify-schema.sh` caught the dots-in-id problem (F-011) when I ran ad-hoc schema validation against the adopter manifest. The bundle's own 8/8 pass confirmed internal consistency. `verify-p3.sh` validated the example manifests' family diversity. `verify-tokens.sh` caught the unreferenced-token pattern (F-009).

### What did it miss?

| Gap | Impact | Friction ref |
|-----|--------|--------------|
| **Adopter manifest not validated.** All `verify-*.sh` hard-code example manifest paths. The adopter's `frameworks/manifests/proposal-review-hardening-v0-6-0.yaml` was never auto-validated — I ran `check-jsonschema` by hand. | Medium — adopter flies blind on their own manifest | F-007, F-010 |
| **Cardinality assertions not re-baselined.** Manifest cardinality assertions drafted at scope time went stale after Phase A narrowed scope. `verify-all.sh` doesn't check these against the spec. | Low — caught at D.6 manually | F-026 |
| **`check-jsonschema` not preinstalled.** `verify-schema.sh` silently skipped when the tool was missing. Exit code 2 = skip, not fail. | Medium — adopter may not notice the skip | F-005 |

### False positives

| Script | False positive | Impact |
|--------|---------------|--------|
| `verify-tokens.sh` | 7 "defined but not referenced" warnings for orchestrator-only tokens | Low — noise, not blockers | F-009 |

**v1.2 action:** Ship `verify-adopter.sh <manifest-path>` that runs schema + P3 + gate-categories + artifact-paths against the adopter's manifest. This is the single highest-leverage tooling improvement.

---

## 5. Manifest/schema ergonomics

### Was the manifest easy to draft?

**Mostly yes, with two sharp edges.**

The slice 1 manifest took ~15 minutes to draft by copying the example and substituting folio values. The structure is intuitive: scope paths, model assignments, smoke checks, gate prerequisites. The YAML schema is well-documented in the example comments.

**Sharp edge 1: `id` pattern forbids dots.** `proposal-review-hardening-v0.6.0` failed schema validation; had to rewrite as `v0-6-0`. This is a paper-cut that costs 2 minutes and every adopter using semver in IDs will hit (F-011).

**Sharp edge 2: `scope.forbidden_paths` requires enumeration.** For slice 2, `folio/pipeline/**` was forbidden EXCEPT `folio/pipeline/enrich_data.py`. The glob-level exclusion with file-level inclusion isn't expressible — had to list the exception in `allowed_paths` and the dir in `forbidden_paths`, hoping the evaluation logic treats allowed > forbidden. Schema doesn't clarify precedence.

### Schema validation helpful or noisy?

**Helpful.** `check-jsonschema` caught the id-pattern violation immediately. The schema's `required` fields caught one missing `summary` field in an early draft. Zero false rejections on valid manifests.

**Noisy in one way:** the schema doesn't validate `model_assignments` entries against P3 rules (that's `verify-p3.sh`'s job). So a manifest can pass schema validation but fail P3. Two-step validation (schema then P3) is correct architecturally but confusing for first-run adopters who expect one pass.

### Slice 2 manifest inheritance

Slice 2's manifest was drafted from slice 1 in ~5 minutes. Key changes: different `id`/`slug`, narrower `allowed_paths`, removed Pre-A phases from `model_assignments`, updated `cardinality_assertions`. The inheritance pattern works well when you have a prior manifest to copy. **First-time adopters without a prior manifest have a harder time** — the example manifests are toy-sized and don't demonstrate real-world scope-lock complexity.

---

## 6. Concrete v1.2 recommendations (ranked, friction-linked)

### Tier A — first-time adopter blockers

| # | Recommendation | Friction refs | Effort |
|---|---------------|---------------|--------|
| A-1 | **Codex adversarial as default.** Framework must NOT treat same-provider sub-agent adversarial as equivalent to cross-family. Require a different-provider family for the adversarial role, or document same-provider adversarial as "advisory only" with mandatory cross-provider second-pass before D.6. This is the single strongest empirical finding from the adoption. | F-006, F-006-confirmed | Policy change |
| A-2 | **`verify-adopter.sh <manifest-path>`.** Unified entry point running schema + P3 + gate-categories + artifact-paths against an adopter manifest. Every `verify-*.sh` should also accept `--manifest <path>`. | F-007, F-010 | 1 day |
| A-3 | **Pre-A consolidator.** Ship Template 16b or prescribe orchestrator consolidation rules in Template 16. Current Pre-A has no adjudication protocol when reviewers disagree. | F-013 | 2 hours |
| A-4 | **Adoption doc v2.** Single `<ADOPTER_REPO_ROOT>` variable; per-language appendix (Python/TS/Go); concrete `day-one.sh` script; explicit `<MANIFEST_DIR>` convention. | F-001, F-002, F-003, F-008 | 1 day |

### Tier B — significant cost workarounds

| # | Recommendation | Friction refs | Effort |
|---|---------------|---------------|--------|
| B-1 | **Scope-audit pre-phase for lean slices.** Before Phase A, grep the entire codebase for the field/symbol being modified. Explicitly include or defer every hit. The orchestrator's targeted search missed provenance.py in slice 2 — the adversarial reviewer's broad grep caught it. | Slice 2 SCOPE-1 | 1 hour (doc) |
| B-2 | **Orchestrator consolidation for unanimous verdicts.** Allow orchestrator-authored B.3/D.3 when all lenses agree (all-Approve or all-Needs-Fixes). Reserve cross-family consolidation for split verdicts where P5 evidence-weighting matters. | F-023, F-029 | Policy change |
| B-3 | **D.6 gate as script.** Gate prerequisites are machine-verifiable (file exists, test passes, grep returns empty). Ship `gate-check.sh <manifest-path>` rather than requiring a reviewer dispatch. | F-030 | 4 hours |
| B-4 | **Stdout-worker adapter.** Bundle script that normalizes dispatch across file-writing (codex, claude-sub) and stdout-only (gemini -p) CLIs. | F-015 | 4 hours |
| B-5 | **Cardinality re-baseline at B.3.** Prescribe that manifest `cardinality_assertions` be re-evaluated against the final Phase A spec at B.3 Approve time. Stale assertions cause false D.6 failures. | F-026 | 1 hour (doc) |
| B-6 | **`<SCOPE_BASE_COMMIT>` token.** `G-scope-1` should diff against Phase C branch-point, not `main..HEAD`. Manifest-level token auto-resolving to the pre-Phase-C commit. | F-025 | 2 hours |

### Tier C — polish

| # | Recommendation | Friction refs | Effort |
|---|---------------|---------------|--------|
| C-1 | **Schema: allow dots in `id`.** Pattern `^[a-z][a-z0-9.-]*$` to accept semver-in-id. | F-011 | 5 min |
| C-2 | **`verify-tokens.sh` orchestrator-only annotations.** Suppress defined-but-unused warnings for tokens tagged `orchestrator-only: true`. | F-009 | 1 hour |
| C-3 | **Rate-limit observability guide.** Adoption doc section on "how to tell a rate-limited-but-completed dispatch from a failed one." | F-014 | 30 min (doc) |
| C-4 | **`<DOC_INDEX_ARCHIVE>` ordering.** Document that archive runs AFTER Phase E retro. | F-004 | 10 min (doc) |
| C-5 | **`check-jsonschema` hard-require.** README "Prerequisites" section should list it as non-negotiable, or vendor a minimal alternative. | F-005 | 30 min |
| C-6 | **Pre-A `family_verdict` posture suffix.** Add `<posture>` placeholder to path-pattern for 2-lens reviews. | F-012 | 1 hour |
| C-7 | **Severity-aware circuit breaker.** Playbook §B.3 should document why the halt gate doesn't distinguish wording-precision blockers from structural blockers — and whether v1.2 should add the distinction. | F-022, F-024 | 2 hours (design) |
| C-8 | **Partial-closure as first-class state.** Template 16 and Template 06 should bless "partial closure" for multi-part blockers with sub-part disposition. | F-021 | 1 hour |

---

## Appendix: friction-to-recommendation cross-reference

| Friction | Recommendation | Status |
|----------|---------------|--------|
| F-001 | A-4 (adoption doc v2) | open |
| F-002 | A-4 | open |
| F-003 | A-4 | open |
| F-004 | C-4 | open |
| F-005 | C-5 | open |
| F-006 | A-1 (codex adversarial) | open |
| F-006-confirmed | A-1 | open |
| F-007 | A-2 (verify-adopter.sh) | open |
| F-008 | A-4 | open |
| F-009 | C-2 | open |
| F-010 | A-2 | open |
| F-011 | C-1 | open |
| F-012 | C-6 | open |
| F-013 | A-3 (Pre-A consolidator) | open |
| F-014 | C-3 | open |
| F-015 | B-4 (stdout adapter) | open |
| F-016 | Missing-token `<PRE_A_ROUND_POLICY>` | open |
| F-017 | External (ontos CLI) | open |
| F-018 | A-4 (tokens.local.md commit guidance) | open |
| F-019 | A-4 (pre-A revision paths) | open |
| F-020 | C-8 (cross-round dynamics doc) | open |
| F-021 | C-8 (partial-closure) | open |
| F-022 | C-7 (severity-aware circuit breaker) | open |
| F-023 | B-2 (orchestrator consolidation) | open |
| F-024 | C-7 | open |
| F-025 | B-6 (scope base commit) | open |
| F-026 | B-5 (cardinality re-baseline) | open |
| F-027 | B-5 (declared-baseline-failure ignore) | open |
| F-028 | B-2 (D.5 single-verifier) | open |
| F-029 | B-2 | open |
| F-030 | B-3 (D.6 as script) | open |
