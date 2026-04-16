---
id: framework-learnings-v1.1-adoption
created: 2026-04-15
updated: 2026-04-16
source: folio.love first production adoption (6 slices)
purpose: Feed frameworks/llm-dev-v1/ROADMAP.md v1.2+ scope
slices_covered:
  - proposal-review-hardening-v0-6-0 (slice 1, PR #44)
  - proposal-lifecycle-rename-v0-6-1 (slice 2, PR #45)
  - provenance-lifecycle-rename-v0-6-2 (PROV-1, PR #46)
  - emission-time-rejection-v0-6-3 (slice 3, PR #47)
  - trust-gated-surfacing-v0-6-4 (slice 4)
  - entity-merge-rejection-memory-v0-6-5 (slice 6a)
---

# Framework Learnings — llm-dev-v1.1 Production Adoption (folio.love)

Six full lifecycle runs on a real Python codebase. Friction entries F-001 through F-048 are the raw data; this document extracts the six structural lessons that feed v1.2+ scope. Slice 6a supplement at the bottom applies the same six-point template to the latest run.

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

## Slice 3 addendum (emission-time-rejection-v0-6-3)

### 1. Token-fill friction (slice 3)

No new token-fill issues. The manifest was templated from slice 2 and all tokens filled without ambiguity. The lean-slice path (inherited Pre-A, narrow scope-lock) makes token-fill straightforward for mechanical slices.

### 2. Template gaps (slice 3)

**Missing:** A "planner's findings" section in Template 12 (spec author). Slice 3's critical bug (rejected-proposal preservation) was discovered during pre-implementation planning exploration, not during spec authoring or code review. The spec template has no designated section for documenting risks found during the planning phase. Without this, the finding only appears in the plan file, which is session-local and not preserved.

**Halt conditions:** No false fires. The codex adversarial failure (F-042) would have triggered a "reviewer non-delivery" halt if strictly enforced, but the framework has no such halt condition. Three of four reviewers delivered.

### 3. Multi-family dispatch friction (slice 3)

| Family | Reliability | Context pressure | Verdict quality |
|--------|-------------|-----------------|-----------------|
| Claude (orchestrator) | Stable | Moderate (1M context comfortably held spec + code + plan) | N/A (author, not reviewer) |
| Claude-sub (peer, product) | Stable | Low (Agent tool isolates) | Good — caught P-1, P-2 (blockers), PR-1 (blocker) |
| Gemini (alignment) | 429 on first attempt; recovered | Low | Good — caught AL-1 (the most significant blocker: unauthorized scope expansion) |
| Codex (adversarial) | **Failed** — output budget consumed by file reads | N/A | **Zero findings** — codex exec with full-auto ran shell commands reading files until output truncated. No structured review produced. |

**Codex adversarial remains the friction hotspot.** F-042 is the third distinct codex invocation issue across 4 slices (F-006: claude-sub weakness in slice 1; user directive to switch to codex; F-042: codex exec output truncation in slice 3). The `codex exec` subcommand prioritizes autonomy over structured output, which conflicts with the review board's need for a formatted verdict document.

### 4. Verify-script accuracy (slice 3)

`verify-all.sh`: **8/8 green** with the new manifest. No false positives. The `verify-p3.sh` correctly identified the new manifest as `user_facing: false` and skipped the product-lens requirement check. `verify-gate-categories.sh` correctly validated all six gate categories present.

No real issues missed by the verify script either — the script validates structural correctness, not semantic correctness, which is appropriate.

### 5. Manifest/schema ergonomics (slice 3)

The manifest was easy to draft — copied from slice 2, changed IDs, narrowed scope, swapped codex/claude-sub roles. Time: ~5 minutes.

One friction: the `scope.forbidden_paths` list grew from 8 to 13 entries because slice 3's narrower scope means more paths to explicitly forbid. This is the opposite of the "narrow scope, less ceremony" promise. **Recommendation:** Support glob negation (`!folio/enrich.py` means "everything in folio/ except enrich.py") to avoid long exclusion lists.

### 6. Concrete v1.2 recommendations (slice 3 addendum)

| Priority | Recommendation | Friction ref | Effort |
|----------|---------------|--------------|--------|
| C-9 | **Codex exec review mode.** Document or implement a `codex exec --review` flag that produces structured markdown output instead of autonomous tool-use exploration. Alternatively, document the exact invocation pattern that produces a review verdict. | F-042, F-044 | 2 hours (doc or 1 day feature) |
| C-10 | **Template 12 "planner's findings" section.** Add an optional section to the spec-author template where the author documents risks/bugs found during pre-implementation analysis. | Slice 3 retro | 30 min |
| C-11 | **Manifest forbidden-path globs.** Support `folio/**` minus `folio/enrich.py` syntax to reduce exclusion list verbosity. | Slice 3 manifest | 2 hours |

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
| F-042 | C-9 (codex exec review mode) | **mitigated** (Slice 4: targeted-prompt pattern resolves without framework change) |
| F-043 | C-3 (rate-limit observability) | open |
| F-044 | C-9 (codex exec invocation docs) | open |
| F-045 | C-12 (model-assignment checklist) | open |
| F-046 | C-13 (B.1 role-overlap reduction) | open |

---

## Slice 4 addendum (2026-04-16)

### Axis 1 — Token-fill friction (no change)

No new token gaps. `<SCOPE_LOCK_PATHS[]>` / `<NO_TOUCH_PATHS[]>` handling already accommodates Python file+dir patterns; Slice 4 forbidden-path list matches Slice 3 shape. `<CARDINALITY_ASSERTIONS[]?>` was intentionally omitted for Slice 4 (no new enum cardinality to guard) — confirms that this token is discretionary, not required, which should be documented in `tokens.md`.

### Axis 2 — Template gaps

**New gap:** spec templates do not prompt the author to cross-reference a "surface enumeration checklist." Slice 4 §5.1 listed six surfaces needing `--include-flagged`; v1.0 implementation wired five. All four D.2 reviewers flagged it (DC-1). This is a recurring class of bug — the spec enumerates a contract, the author forgets one item, reviewers see the gap only when code is present.

**v1.2 recommendation (C-12):** Phase C template should include a "contract enumeration checklist" that extracts §-level enum tables from the spec and verifies each item has a matching implementation anchor (function, CLI flag, class field, test). This runs before D.1 and is cheap.

### Axis 3 — Multi-family dispatch friction

**F-042 status update:** Mitigated without framework change. Slice 4 used a targeted-prompt pattern for codex adversarial:

1. Explicit numbered failure-mode targets (1-6) in the prompt body.
2. "Use shell commands sparingly" instruction up front.
3. Pre-listed file paths to read.
4. Strict output format (frontmatter + classification).

Result: codex produced a 273-line review with 1 blocker + 3 should-fix, including a finding (ADV-001 in B.1, D-ADV-001 in D.2) that no other reviewer caught. This is the first clear adversarial-lens win on codex.

**v1.2 recommendation (C-9):** Update adversarial-prompt template to encode the targeted-prompt pattern. Suggested template:

```
You are the adversarial reviewer for <DELIVERABLE_ID>. Find what breaks.
Read (sparingly): <FILE_LIST>.
Target failure modes:
1. <MODE_1>
2. <MODE_2>
...
Classify: Blockers, Should-fix, Informational.
```

**New friction F-045:** Author initially dispatched 3/4 B.1 reviewers in parallel but omitted codex. Caught mid-run by user. Manifest `model_assignments` section was not cross-checked before the parallel dispatch.

**v1.2 recommendation (C-12 extended):** Phase B.1 and Phase D.2 launch templates should list the manifest's model_assignments for the phase as a pre-flight checklist. A one-line command (e.g., `yq '.model_assignments[] | select(.phase == "B.1")' manifest.yaml`) would print the assignments. Then: "Confirm all assignments dispatched. Proceed?"

### Axis 4 — Verify-script accuracy

D.5 verifier (gemini) caught a real hygiene issue in Slice 4's D.4 fix summary: line numbers in citations drifted ~18 lines from the actual code location because fix authoring ran multiple edits without refreshing references. Logic was correct; hygiene was off.

**v1.2 recommendation (C-14):** D.4 fix-summary template should instruct the fix author to generate line citations by running `git grep -n <anchor>` AFTER the final commit, not during edit sessions. Cheap, mechanical fix.

### Axis 5 — Manifest/schema ergonomics

Slice 4's manifest reused Slice 3's structure with minimal change (scope-lock swap, regression_guards inheritance). Copy-paste between slice manifests is now frictionless but creates a drift risk: if the parent spec adds a new regression_guard (e.g., a new tier requires a new test file), manifest inheritance won't catch it.

**v1.2 recommendation (B-7):** `regression_guards[]` should support an inherits-from pattern (list of prior deliverable_ids), with a lint check that warns when a listed deliverable has active regression_guards not carried forward.

### Axis 6 — Concrete v1.2 recommendations (additions)

Existing recommendations (C-1..C-8, B-2..B-6 from prior slices) stand. Slice 4 adds:

- **C-9 update:** Codify the targeted-prompt pattern for codex adversarial (see Axis 3). Mark F-042 mitigated.
- **C-12 (new):** Contract-enumeration checklist in Phase C + model-assignments dispatch preflight.
- **C-13 (new):** B.1 role-overlap reduction — alignment + product repeatedly produce overlapping findings when the spec under-scopes "surface." Consider a combined "operator-contract" role or explicit division in role templates (alignment = parent-spec fidelity; product = operator experience; no overlap on surface enumeration).
- **C-14 (new):** D.4 fix-summary line-citation regen-after-commit guidance.

### Delta signal table (updated)

| Axis | Slice 1 | Slice 2 | Slice 3 | Slice 4 | Trend |
|------|---------|---------|---------|---------|-------|
| Token-fill friction | 4 entries | 1 | 0 | 0 | Converging — templates stabilized |
| Template gaps | 3 (Pre-A) | 1 | 2 | 1 (contract enum) | New class surfaced |
| Multi-family | 2 (F-014, gemini 429) | 1 | 3 (F-042/43/44) | 1 (F-045 dispatch hygiene) | F-042 mitigated |
| Verify-script | 1 | 0 | 0 | 1 (line citation drift) | New |
| Manifest/schema | 0 | 1 | 0 | 0 | Stable |
| v1.2 recs | — | C-1..C-4 | C-5..C-8 | C-9..C-14 | Accumulating cleanly |

**Net effect:** Slice 4 produced fewer friction entries than any prior slice (2 vs. 3-8). Framework is converging. The remaining signal is not about framework defects but about author hygiene (checklist-able) and reviewer role-overlap (template-fixable). Next slice will likely stabilize further.

---

# Slice 6a supplement — entity-merge-rejection-memory-v0-6-5

Reviewed against the six-point framework per the earlier session directive (frameworks/manifests README).

### 1. Token-fill friction

**No new findings.** Slice 6a was a clean manifest drop from the slice-1 / slice-2 template. All tokens auto-resolved.

However, a token-adjacent gap emerged: `scope.allowed_paths` in the manifest schema doesn't support glob patterns. Every adopter slice that touches cross-cutting regression tests or produces Round-N artifacts needs per-file enumeration. Surfaced as friction F-047.

**v1.3 recommendation (promoted from polish to should-ship):** `scope.allowed_path_patterns: [glob...]` schema field. See §6 recommendation T-1 below.

### 2. Template gaps

**No new template gaps.** v1.1.1 closed the B-3 (D.6 as script) target; slice 6a ran D.6 via orchestrator-authored machine-verified prerequisites with no reviewer dispatch. Clean end-to-end.

Template 16 Pre-A tightening (v1.2 A-3) wasn't exercised this slice (Pre-A inherited from parent proposal §15.6). Unchanged signal.

### 3. Multi-family dispatch friction

**No new CLI reliability issues.** Four dispatches per round, all completed within their timeout budgets:
- codex exec (adversarial): ~3-4 min per round, clean output
- gemini -p (alignment): ~1-2 min, correct scope verification
- Claude agent (peer + product): ~2-3 min each, deep line-by-line coverage

**Adversarial recall pattern reconfirmed.** Slice 6a:
- B.1 R1: codex adversarial found 2 blockers (ADV-001 schema-bump, ADV-002 lost-update). Peer, alignment, product found zero blockers.
- D.2: codex adversarial Approve with zero findings after v1.2 spec and clean Phase C. Peer / product / gemini found only minor or scope-hygiene items.
- **Conclusion:** codex adversarial is still the single highest-yield lens for design-defect detection when the spec is fresh. When the spec has already converged (v1.2), codex's marginal value is near-zero. Recommend keeping codex adversarial on B.1 R1 + D.2 R1 as policy; subsequent rounds can de-emphasize if codex R1 returned clean.

### 4. Verify-script accuracy

**No verify-script regressions.** Post-v1.1.1 cardinality-assertion format (Python-native imports instead of CLI-help grep) worked cleanly — both cardinality assertions passed first try.

**One new finding:** D.6 gate's G-branch-1 ("working tree clean") is sensitive to `ontos map` auto-regeneration of `AGENTS.md` and `Ontos_Context_Map.md` (both in scope.forbidden_paths). Had to `git checkout` them before the gate would pass. Surfaced as friction F-048.

**v1.3 recommendation (polish):** adoption doc should document the "revert ontos auto-regeneration before D.6" step for adopters using ontos-adjacent tooling.

### 5. Manifest/schema ergonomics

**No schema errors.** Manifest passed `verify-all.sh` on first draft.

**One real ergonomic friction:** §15.6 says scope is "folio/tracking/entities.py" but the slice's label-rename side-effect ("Duplicate person candidates" → "Reviewable…") forced test updates in `tests/test_graph_cli.py` — a file that wasn't in the primary scope. Manifest drafting underestimated the cross-cutting blast radius. The fix is F-047's glob support.

### 6. Concrete v1.3 recommendations (ranked, friction-linked)

| Tier | ID | Recommendation | Friction ref | Effort estimate |
|------|----|----------------|--------------|----|
| **Should-ship** | T-1 | Manifest `scope.allowed_path_patterns: [glob, ...]` schema field. Match semantics: in-scope if file matches any exact path OR any glob. Documented exclude list for safety. | F-047 | Schema + matcher: ~1 day |
| Polish | T-2 | Adoption doc entry: "before D.6 gate, revert any `ontos map` / auto-generated regenerations that land in scope.forbidden_paths." One-paragraph insert. | F-048 | ~30 min |
| Polish | T-3 | ROADMAP entry: "codex adversarial marginal value drops after spec convergence (v1.2+)." Useful orchestrator guidance for when to save a dispatch. | Slice 6a D.2 observation | ~15 min |

All three are adopter-experience hygiene; none are design-critical. Slice 6a confirms the framework has stabilized into "patch-class friction" territory (small ergonomic fixes) rather than "structural-class friction" (template gaps, halt-condition miscalibrations, family-diversity breakdowns).

### Cross-slice friction trend (updated through slice 6a)

| Class | Slice 1 | Slice 2 | PROV-1 | Slice 3 | Slice 4 | Slice 6a | Trend |
|-------|---------|---------|--------|---------|---------|----------|-------|
| Token-fill | 6 | 0 | 0 | 0 | 0 | 0 (1 adjacent → F-047) | Stable-clean |
| Template gap | 3 | 1 | 0 | 1 | 0 | 0 | Stable-clean |
| Multi-family | 2 | 0 | 0 | 0 | 1 (F-042, mitigated in slice 4) | 0 (adversarial-value note) | Stable |
| Verify-script | 1 | 0 | 0 | 0 | 1 (line citation drift) | 1 (F-048 ontos regen) | Stable |
| Manifest/schema | 0 | 1 | 0 | 0 | 0 | 1 (F-047 glob) | Stable |
| v1.2+ recs | — | C-1..C-4 | C-5..C-8 | C-9..C-14 | — | T-1..T-3 | Accumulating cleanly |

**Net effect:** Slice 6a matches slice 4's low-friction baseline (2 entries). Both new entries (F-047, F-048) are ergonomic, not structural. The framework has converged for the adopter's code-surface category; remaining friction is in adopter tooling (ontos, glob support) and orchestrator heuristics (when to dispatch codex vs. orchestrator-consolidate).
