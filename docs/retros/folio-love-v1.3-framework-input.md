---
id: folio-love-v1.3-framework-input
created: 2026-04-17
source: consolidated extraction from folio.love's v1.1.0 → v1.2.0 lifecycle runs
purpose: final adopter input for johnny-os v1.3 scoping, evidence-weight merge input
slices_covered:
  - proposal-review-hardening-v0-6-0 (slice 1, PR #44)
  - proposal-lifecycle-rename-v0-6-1 (slice 2, PR #45)
  - provenance-lifecycle-rename-v0-6-2 (PROV-1, PR #46)
  - emission-time-rejection-v0-6-3 (slice 3, PR #47)
  - trust-gated-surfacing-v0-6-4 (slice 4)
  - entity-merge-rejection-memory-v0-6-5 (slice 6a, PR #57)
  - folio-digest-v0-7-0 (slice 7, PR #58)
  - folio-graph-generalized-proposals-v0-7-1 (slice 6b.1, PR #60)
  - folio-synthesize-v0-8-0 (slice 6b.2, PR #65)
bundle_versions_used:
  - v1.1.0 (slices 1, 2, PROV-1, 3, 4, 6a, 7)
  - v1.1.1 (patch; five bug-fixes closed)
  - v1.2.0 (slices 6b.1, 6b.2; must-differ-provider + verify-d6-gate.sh + verify-adopter.sh + day-one.sh)
source_docs:
  - docs/retros/llm-dev-v1-adoption.md (958 lines)
  - frameworks/manifests/framework-learnings-v1.1-adoption.md (713 lines)
  - docs/framework-adoption.md (16 lines — adopter-only contract)
  - PR #51 (v1.1.1 ship), #52 (v1.2 build plan; superseded), #53 (resync v1.1.1), #59 (resync v1.2.0)
---

# folio.love v1.3 framework input — consolidated extraction

Last adopter-side input before johnny-os v1.3 scoping starts. Evidence-weight merge target. Nine lifecycle runs on a real Python codebase, spanning v1.1.0 first-adoption through v1.2.0 second-full-adoption.

**Bottom line.** Framework has converged on extension-class slices under v1.1.x (slices 2, PROV-1, 3, 4, 6a all shipped with ≤5 friction entries each). v1.2.0 first-contact surfaced a new friction footprint centered on **dispatch × policy interaction** (F-054/F-055 slice 6b.1) that sustains into slice 6b.2 (F-060/F-061 different classes, same count). Greenfield modules (slice 7, slice 6b.2) stress process boundaries in ways extension slices don't — branch-state hygiene, helper-divergence, spec→impl traceability. Zero preserved blockers at ship across all nine slices; the framework works. v1.3's highest-leverage target is mechanizing the v1.2.0 dispatch-fallback patterns before the next adopter's first-contact.

---

## 1. Run inventory

| Slice | Version | Bundle | Class | Phases | B rounds | D rounds | CB fires | Halts | Friction added | Cumulative friction |
|-------|---------|--------|-------|--------|----------|----------|----------|-------|----------------|---------------------|
| 1 — proposal-review-hardening | v0.6.0 | v1.1.0 | Extension + Pre-A | 0, Pre-A (3r), A (v1.0→v1.3), B (4r + 4×B.3), C, D (D.1 + D.3 + D.4 + D.4b + D.5 + D.6), E | 4 | 1 + D.4 + D.4b (retroactive) | 3 (Pre-A R2, B.3 R3, B.3 R4 soft) | 4 operator-rescinded | F-001..F-028 | 28 |
| 2 — lifecycle rename | v0.6.1 | v1.1.0 | Extension (rename) | A, B (2r), C, D (1r + D.4), E | 2 | 1 + D.4 | 0 | 0 | F-029, F-030 | 30 |
| PROV-1 — provenance rename | v0.6.2 | v1.1.0 | Extension (rename) | A, B (1r), C, D (1r), E | 1 | 1 | 0 | 0 | (none new; clean replay) | 30 |
| 3 — emission-time rejection | v0.6.3 | v1.1.0 | Extension | A, B (1r), C, D (1r + D.4), E | 1 | 1 + D.4 | 0 | 0 | F-042, F-043, F-044 | 44 (incl. re-numbering; see §3 gap note) |
| 4 — trust-gated surfacing | v0.6.4 | v1.1.0 | Extension | A (v1.0→v1.2), B (1r), C, D (1r + D.4 + D.5), E | 1 | 1 + D.4 + D.5 | 0 | 0 | F-045, F-046 (+ F-042 status-updated) | 46 |
| 6a — entity-merge rejection memory | v0.6.5 | v1.1.0 | Extension | A (v1.0→v1.2), B (2r), C, D (1r + D.4), E | 2 | 1 + D.4 | 0 | 0 | F-047, F-048 | 48 |
| 7 — folio digest | v0.7.0 | v1.1.0 | **Greenfield** | A (v1.0→v1.2), B (2r + B.3 R3 orchestrator-direct), C, D (1r + D.4 + D.5 + D.6), E | 2 + R3 ortho | 1 + D.4 + D.5 + D.6 | 0 | 0 | F-049..F-053 | 53 |
| 6b.1 — graph generalized proposals | v0.7.1 | **v1.2.0** | Extension (retrofit) | 0, A (v1.0→v1.2), B (2r + B.3 ortho), C, D (D.1 tweak + D.2 + D.3 ortho + D.4 + D.5×3 + D.6), E | 2 + B.3 ortho | 1 + D.1 tweak + D.3 ortho + D.4 + D.5×3 + D.6 | 0 | 0 | F-054..F-058 | 58 |
| 6b.2 — folio synthesize | v0.8.0 | v1.2.0 | **Greenfield** | 0 (helper promotion), A (v1.0→v1.1), B (1r + B.3 ortho), C, D (1r + D.3 ortho + D.4 + D.5 + D.6 ortho), E | 1 + B.3 ortho | 1 + D.3 ortho + D.4 + D.5 + D.6 ortho | 0 | 0 | F-059..F-062 | 62 |

**Note on friction numbering.** F-031 through F-041 do not appear as individual entries in either source doc — the numbering jumps from F-030 (slice 2) to F-042 (slice 3). The gap is not documented. Treating F-031..F-041 as reserved placeholders rather than missing entries; flagged as a finding in §8.

### Run-inventory aggregate signals

- **9 slices, 0 preserved blockers at ship.** Framework's Phase-A/B/C/D/E sequence caught every load-bearing defect before merge.
- **Halt ledger:** 4 halts in slice 1 (all operator-rescinded); 0 halts in slices 2–6b.2. Circuit breaker fired only during slice 1's Pre-A and B.3 multi-round arcs. No CB fires under v1.2.0.
- **Orchestrator-direct closures:** first appeared as F-029 (slice 2), codified as B-2 policy in v1.2.0, then exercised 7 times across slices 6a (1×), 7 (1×), 6b.1 (2×: B.3 + D.3), 6b.2 (3×: B.3 + D.3 + D.6). All 7 held; none bit back at subsequent phases.
- **Greenfield slices produce more friction classes per slice than extension slices.** Slice 7: 3 new friction classes (branch-state hygiene, helper-divergence, spec→impl traceability). Slice 6b.2: 2 new (author-direct consolidation codification need, test-blessed divergence). Extension slices under v1.2.0 still produce 4-5 friction entries per slice (slice 6b.1: 5) but in rotating classes.

---

## 2. Open recommendations delta — v1.1.0 original 25 vs v1.1.1 + v1.2.0 shipped vs still-open

Starting from the 25 recommendations in `framework-learnings-v1.1-adoption.md` §6 + slice-3/4 addenda.

### Shipped in v1.1.1 (5 items)

| ID | Recommendation | v1.1.1 evidence | New evidence from later slices |
|----|----------------|-----------------|--------------------------------|
| **C-1** | Schema allows dots in `id` | Shipped (semver-in-id now accepted) | No regressions observed |
| **C-2** | `verify-tokens.sh` orchestrator-only annotations | Shipped | No regressions observed |
| **C-4** | `<DOC_INDEX_ARCHIVE>` ordering documented | Shipped | — |
| **C-5** | `check-jsonschema` hard-require | Shipped | — |
| **B-5** | Cardinality re-baseline at B.3 Approve | Shipped | Slices 6a + 7 + 6b.1 all re-baselined cardinality at B.3; pattern works |

### Shipped in v1.2.0 (6 items + 1 class-level addressed)

| ID | Recommendation | v1.2.0 evidence | New evidence from later slices |
|----|----------------|-----------------|--------------------------------|
| **A-1** | Codex adversarial as default (must-differ-provider invariant) | Shipped as `must-differ-provider` P3 invariant | Validated slice 6a (codex caught 2 blockers no other lens did). Slice 7 mixed: codex caught 0 B.1 blockers (peer caught both); caught 1 B.2 + 1 D.2 blocker. Slice 6b.1: codex caught both B.2 blockers; D.2 blocker. Slice 6b.2: codex caught blockers at both B.1 + D.2. **Net: codex adversarial retains highest-yield-per-dispatch on structural defects; not always first-catch on mechanical defects.** |
| **A-2** | `verify-adopter.sh <manifest-path>` | Shipped | Slice 6b.1 passed 4/4 first-try; slice 6b.2 passed 4/4 twice. Validated. |
| **A-3** | Pre-A consolidator (Template 16 P5-style) | Shipped as Template 16 P5-style divergent-reviewer consolidation | Not exercised post-v1.2.0 (slices 6b.1, 6b.2 both inherited Pre-A). |
| **A-4** | Adoption doc v2 + `day-one.sh` | Shipped (`day-one.sh` bootstrap script) | Not re-exercised (no new first-adopter) |
| **B-2** | Orchestrator consolidation on unanimous verdicts | Shipped (manifest_version ≥ 1.2.0 only) | Exercised 7× across slices 6a, 7, 6b.1, 6b.2. All 7 held. Strong validation. |
| **B-3** | D.6 gate as script (`verify-d6-gate.sh`) | Shipped | Exercised 3× (slice 6a, 6b.1: 15/15; 6b.2: 24/24). All first-try PASS. |
| **(class)** C-7 | Severity-aware circuit breaker | Partial: v1.2.0 ships **circuit-breaker preserved-blocker-ID carry-forward** — prevents false halts on improving artifacts | Not specifically exercised (no multi-round CB trips in v1.2.0 slices) |

### Still open after v1.2.0 (14 items from original 25 + Slice-3/4 addenda)

Ranked by evidence weight (recurrence count + severity).

| ID | Recommendation | Original friction | New evidence | Recommendation status |
|----|----------------|-------------------|--------------|-----------------------|
| **B-1** | Scope-audit pre-phase for lean slices | Slice 2 SCOPE-1 | Slice 6a F-047 (manifest scope gap); Slice 7 F-050 (helper-API divergence) — same root cause: orchestrator scope assessment under-samples. 3 slices of evidence. | **Promote to must-ship v1.3** |
| **B-4** | Stdout-worker adapter | F-015 | F-061 (gemini `-p` writes-to-stdout-not-file) is fresh evidence; adopter still using `sed`-extract workaround. 2+ slices stuck on same pattern. | **Promote to should-ship v1.3** |
| **B-6** | `<SCOPE_BASE_COMMIT>` token for G-scope-1 | F-025 | No new occurrences — multi-slice-branch scenario didn't recur. | **Defer or close** — single-occurrence evidence; costly to fix; no recurrence signal. |
| **B-7** | `regression_guards[]` inherits-from pattern | Slice 4 | No new occurrences; slices since have used simple copy-paste. | **Defer** — speculative, no recurrence |
| **C-3** | Rate-limit observability | F-014 | F-043, F-054 (now escalated to HIGH under v1.2.0), F-061 (different gemini failure mode). **4 slices of gemini-related friction.** | **Upgrade to should-ship** as part of dispatch-infrastructure work (T-10/T-11/T-12 cluster) |
| **C-6** | Pre-A `family_verdict` posture suffix | F-012 | No new occurrences — Pre-A ran only once (slice 1). | **Defer** — low recurrence probability |
| **C-8** | Partial-closure as first-class state | F-021 | No new occurrences. | **Defer** |
| **C-9** | Codex adversarial targeted-prompt template | F-042, F-044 | **Mitigated at slice 4** via targeted-prompt pattern. Slice 6b.1 confirmed pattern still works. Never re-broke. | **Close as mitigated** — adopter uses the pattern by convention; codifying as template is polish |
| **C-10** | Template 12 "planner's findings" section | Slice 3 | No new occurrences — no slice has had a pre-implementation-analysis discovery that needed capture since. | **Defer** — single-occurrence, speculative |
| **C-11** | Manifest forbidden-path globs (exclusion syntax) | Slice 3 | Not recurred in exclusion direction. | **Defer** — inversion of T-1 (allowed-path globs) which HAS recurred |
| **C-12** | Contract-enumeration checklist + model-assignments preflight | F-045 | Slice 6b.1 had a related miss (F-056 manifest test-path typo); slice 7 had spec→impl gap (the §10.4 self-heal ordering, covered under T-5). Pattern: "author didn't cross-check enum against implementation surface." 3 slices of evidence in different flavors. | **Promote to should-ship v1.3** |
| **C-13** | B.1 role-overlap reduction (alignment ↔ product) | F-046 | No new occurrences — slices since have had minimal alignment/product overlap. | **Defer** — single-occurrence evidence |
| **C-14** | D.4 fix-summary line-citation regen-after-commit | F-046 area | No new occurrences. | **Defer** — polish, low evidence |

### Summary of v1.1.0 → v1.2.0 open-delta

- **11 items shipped** (C-1, C-2, C-4, C-5, B-5 in v1.1.1; A-1, A-2, A-3, A-4, B-2, B-3 in v1.2.0) — 11/25 = 44% closure rate in two bundle revisions.
- **3 items promote to v1.3** based on recurrence evidence: B-1 (scope-audit), B-4 (stdout-worker), C-12 (contract-enumeration + preflight).
- **1 item close as mitigated**: C-9 (targeted-prompt pattern is the mitigation).
- **1 item upgrade** from polish to should-ship: C-3 (rate-limit observability) — now part of dispatch-infrastructure cluster.
- **8 items defer** due to single-occurrence evidence or low recurrence probability.

---

## 3. New friction not in the original 25

Friction entries from slices that ran AFTER the v1.1 adoption doc was authored (slices 6a, 7, 6b.1, 6b.2). Original friction F-031..F-041 gap is documented as finding in §8.

### Slice 6a (F-047, F-048)

| ID | Category | What happened | Root cause | Severity | Proposed fix |
|----|----------|---------------|------------|----------|--------------|
| F-047 | Manifest/schema | `scope.allowed_paths` requires per-file enumeration; no glob support. Cross-cutting regression test files + Round-N validation artifacts need preemptive inclusion or mid-slice manifest amendment. | Manifest schema designed for tight-surface slices; real adopter slices touch regression guards outside primary scope. | Medium | **T-1 (slice 6a):** manifest `scope.allowed_path_patterns: [glob, ...]` alongside explicit list. |
| F-048 | Verify-script / adopter-tooling | `ontos map` auto-regenerates `AGENTS.md` + `Ontos_Context_Map.md` mid-session despite those files being in `scope.forbidden_paths`. Breaks G-branch-1 clean-working-tree gate. | Ontos tool doesn't consult active deliverable manifest forbidden_paths. | Low | **T-2 (slice 6a):** adoption doc pre-D.6 checklist: "revert any `ontos map`/auto-generated regenerations that land in forbidden_paths." Codified as needed after 3 confirmations (slice 6a + slice 7 + slice 7 within-session). |

### Slice 7 (F-049..F-053)

| ID | Category | What happened | Root cause | Severity | Proposed fix |
|----|----------|---------------|------------|----------|--------------|
| F-049 | Manifest cite-path | `pre_a.justification` cited `§15.7` but §15.7 lives in a different spec than the Pre-A artifact. Spec author hunted across two docs. | Manifest template allows un-qualified section references. | Medium | **T-6:** manifest pre-A justification template requires full `<doc> §<section>` form when citing a contract outside the Pre-A artifact. |
| F-050 | Helper-API divergence | `folio.analysis_docs.create_analysis_document` had 3 shape mismatches with digest's needs (date semantics, path layout, rerun handling). Spec committed to digest-specific helpers. | No spec template prompt for "first consumer of an existing helper family" forcing explicit extend-vs-diverge decision. | Medium | **T-7:** Template 12 "helper-divergence-disclosure" section — author must either extend helper signature OR document divergence explicitly. |
| F-051 | Verify-script (F-048 recurrence) | F-048 pattern recurred during Phase A setup. Third occurrence across sessions. | Adopter-tooling issue, codified | Low | T-2 codification; confirmed at scale. |
| F-052 | **Branch-state hygiene (NEW CLASS)** | Working tree silently switched from feature branch to `main` during codex session-closeout. Codex reviewers read wrong tree state, reported false-positive "manifest absent." | Subprocess inheritance of working-tree state; no branch-pinning check before dispatch. | High | **T-8:** orchestrator runbook section — `git branch --show-current` must equal feature branch before any subprocess invocation. |
| F-053 | Codex prompt template | Codex reported "file missing" without verifying via `git ls-files` / `git rev-parse HEAD`. Defaults to "if I can't ls it, it's missing." | Codex adversarial prompt template has no file-existence verification preamble. | High | **T-4:** reviewer-prompt templates (03 peer, 05 adversarial) add file-existence verification preamble. |

### Slice 6b.1 (F-054..F-058) — FIRST v1.2.0 ADOPTION

| ID | Category | What happened | Root cause | Severity | Proposed fix |
|----|----------|---------------|------------|----------|--------------|
| F-054 | **Dispatch × v1.2 policy (NEW CLASS)** | Gemini 429 rate-limit persisted through B.1/B.2/D.2. Under v1.2.0 must-differ-provider + ≥3-family floor, single-provider outage hard-blocks the round. No in-family substitute. | v1.2.0 policy strictness converts F-014-class friction into hard-blocking. | High | **T-10 (must-ship):** escalation ladder in `framework.md § P3`: 1h retry → ≤24h halt → >24h documented 3-lens fallback + supplementary round. **T-11:** optional manifest `reviewer_family_substitutes[]`. **T-12:** `verify-p3.sh` distinguishes "unavailable" vs "declined." |
| F-055 | Capability-matrix × role-assignment | Gemini CLI in operator env lacks shell + test-runner tools needed for D.5 verifier role. Manifest `cli_capability_matrix.gemini = { shell: false, test_runner: false }` is advisory not enforced. | Capability matrix is informational, not checked against role requirements. | Medium | **T-12 (should-ship):** `verify-p3.sh` cross-checks role assignments against `cli_capability_matrix[<FAMILY>]`; flag incompatible assignments at manifest-validation time. |
| F-056 | Manifest gate-command dry-run gap | 2 of 12 cardinality-gate commands pointed at nonexistent test paths. `verify-adopter.sh` passes schema+P3+gate-categories+artifact-paths but doesn't execute the commands themselves. Caught by 2-lens direct-run at D.2. | `verify-adopter.sh` is structural-only, not executable. | High | **T-13 (should-ship):** `verify-gate-commands.sh` (or extend verify-adopter.sh) actually executes each `cardinality_assertions[].command` + `gate_prerequisites[].verification.command` at Phase-0 validation time. |
| F-057 | Review-lens reachability audit | `supported_relation` gate rule unreachable end-to-end (upstream filter suppresses candidates). Only product-lens direct-run caught it. Peer/adversarial/alignment all missed. | Reviewer prompts don't require reachability audit for new validation-layer rules. | Medium | **T-14 (should-ship):** Template 03 (peer) + Template 05 (adversarial) add "rule-reachability audit" prompt — cite one triggering test case for each new rule. |
| F-058 | Scope-lock line-cap authoring sequence | G-scope-3 authored at 25 lines pre-test-plan; real Phase-C scope (incl. `--include-flagged` test coverage) pushed diff to 33 lines. D.1 surgical tweak to 40. | Scope gates authored before test plan is frozen can mis-calibrate. | Medium | **T-15 (polish):** manifest authoring guidance — author `G-scope-N` gates post-test-plan, or 50-100% headroom pre-test-plan. Each gate carries a rationale string. |

### Slice 6b.2 (F-059..F-062) — SECOND v1.2.0 ADOPTION

| ID | Category | What happened | Root cause | Severity | Proposed fix |
|----|----------|---------------|------------|----------|--------------|
| F-059 | Template gap (consolidation mode) | Author-direct consolidation substituted for codex meta-consolidator at B.3/D.3/D.6 under wall-clock pressure (not family-unavailable, distinct from F-054). Template 06 has no explicit `author-direct` variant. | F-051 surgical-fixes precedent works but is tacit; should be codified as template variant. | Medium | **T-17 (should-ship):** Template 06 accepts optional `author-direct-with-external-lens-citation` mode; requires evidence-row citation of each external verdict. **T-22:** manifest `consolidation_mode: {external, author-direct-with-external-lens}` field; verify-p3.sh validates adversarial LENS is still non-author family. |
| F-060 | Adopter-config (codex × AGENTS.md) | Codex read repo-root `AGENTS.md`, ran `python3 -m ontos map` as activation, command exited 1, codex idled 30 minutes without recovery. | Framework template 01 has no "skip failing activation" boilerplate. | High | **T-19 (should-ship):** Template 01 Phase C clause — if activation fails, skip with logged note; do NOT loop on the failing command. |
| F-061 | Dispatch (distinct from F-055) | Gemini `-p` mode emits verdict to stdout (wrapped in ```markdown fence) instead of writing to requested file path. 3 dispatches needed `sed`-extract recovery. | `cli_capability_matrix` doesn't distinguish `shell: true` from `writes_files_non_interactively: true`. | Medium | **T-18 (should-ship):** `cli_capability_matrix` schema adds `writes_files_non_interactively: bool`. Dispatcher auto-redirects stdout to file when false. |
| F-062 | Phase-C × spec-code drift (NEW CLASS) | Phase-C author wrote tests that blessed spec-vs-code divergence instead of escalating. Caught by 2-lens at D.2 (codex + peer convergent). | No framework mechanism prevents test-blessed divergence during Phase C. | High | **T-16 (must-ship):** Template 01 Phase C clause — if spec-vs-implementation divergence noticed during test authoring, STOP and escalate; do NOT write blessing-test. **T-20/T-21:** adversarial + peer templates add "test-blessed divergence audit" prompt. |

### New friction summary

- **16 new friction entries** since the v1.1 adoption doc (F-047..F-062, modulo F-051 = F-048 recurrence).
- **4 new friction classes:**
  1. Branch-state hygiene (F-052)
  2. Dispatch × v1.2 policy (F-054, F-060, F-061)
  3. Helper-divergence disclosure / Phase-C × spec-code drift (F-050, F-062)
  4. Review-lens design gaps (F-057 reachability; F-056 gate-command dry-run)

- **Severity distribution:** 5 High, 8 Medium, 3 Low. Higher-severity distribution than v1.1 adoption's original 25 (which was dominated by C-tier polish).
- **Dispatch-infrastructure cluster dominates.** F-054/F-055/F-060/F-061 all touch the CLI invocation layer. Cumulative cost: ~12 operator-interventions across slices 6b.1 + 6b.2. Single highest-leverage v1.3 target.

---

## 4. Cross-slice patterns (high-confidence v1.3 signal)

Friction that recurred across 2+ slices. These are the evidence-weight-weighted must-ship signals for v1.3.

### Pattern 1: Dispatch-infrastructure fragility (HIGHEST confidence)

**Recurrence: 4 slices (1, 3, 6b.1, 6b.2) + all v1.2.0 slices.**

| Slice | Entry | Form |
|-------|-------|------|
| 1 | F-014 | Gemini 429 rate-limit, slow-but-completed |
| 3 | F-043 | Gemini 429 recurrence (same as F-014) |
| 3 | F-042 | Codex `exec` output-budget exhaustion |
| 4 | (F-042 mitigated) | Targeted-prompt pattern mitigates codex |
| 6b.1 | F-054 | Gemini 429 **hard-blocks** under v1.2.0 strictness |
| 6b.1 | F-055 | Gemini read-only × D.5 verifier (distinct mode) |
| 6b.2 | F-060 | Codex × AGENTS.md activation loop |
| 6b.2 | F-061 | Gemini `-p` stdout-not-file |

**Interpretation:** Dispatch CLI layer is the single flakiest surface across the entire adoption. Each adopter slice surfaces at least one dispatch friction. The class is NOT converging — new modes appear rather than old modes recurring. v1.2.0's stricter P3 invariant RAISES severity of this class by eliminating graceful degradation paths that existed under v1.1.x.

**v1.3 must-ship cluster:** T-10 (escalation ladder) + T-11 (reviewer_family_substitutes) + T-12 (capability-matrix cross-check) + T-18 (writes_files_non_interactively flag) + T-19 (skip-failing-activation boilerplate). Five inter-related items that collectively mechanize graceful degradation for dispatch fragility.

### Pattern 2: Author-process × spec-implementation traceability (HIGH confidence)

**Recurrence: 3 slices (4, 7, 6b.2).**

| Slice | Entry | Form |
|-------|-------|------|
| 4 | Slice 4 DC-1 | Spec §5.1 listed 6 surfaces, impl wired 5 |
| 4 | F-045 | Author forgot codex adversarial dispatch |
| 7 | B-201 (D.2 blocker) | Spec §10.4 orphan self-heal ordering, impl wrong |
| 7 | F-050 | Helper-API divergence not disclosed in spec |
| 6b.2 | F-062 | Phase-C author wrote tests that blessed divergence |

**Interpretation:** Phase A ↔ Phase C traceability is the second-biggest friction class. Spec enumerates contracts; author implementation partially satisfies; reviewers catch only when code surfaces the gap. When they don't catch it, it ships to D.2 (B-201, F-062). v1.3 should make this harder to introduce AND easier to catch.

**v1.3 must-ship cluster:** C-12 (contract-enumeration checklist + preflight) + T-7 (helper-divergence disclosure in Template 12) + T-16 (Phase-C escalation for spec-code divergence) + T-20/T-21 (adversarial + peer test-blessed divergence audit). Four inter-related items.

### Pattern 3: Manifest scope authoring under-samples (MEDIUM-HIGH confidence)

**Recurrence: 3 slices (2, 6a, 6b.1).**

| Slice | Entry | Form |
|-------|-------|------|
| 2 | SCOPE-1 | Orchestrator scope assessment missed provenance.py |
| 6a | F-047 | Manifest lacked glob support for cross-cutting tests |
| 6b.1 | F-056 | Manifest gate-command paths typoed |

**Interpretation:** Manifest authoring at Phase 0 under-samples the real scope surface. Reviewer catches it at B or D, but the fix is always post-facto amendment. Two sub-patterns: scope-miss (fix via broader audit) and authoring-error (fix via validation).

**v1.3 should-ship cluster:** B-1 (scope-audit pre-phase — promoted from original 25) + T-1 (glob support) + T-13 (gate-command dry-run). Three items.

### Pattern 4: Orchestrator-direct consolidation scaling (VALIDATED)

**Recurrence: 7 successful applications across slices 6a, 7, 6b.1 (2×), 6b.2 (3×).**

| Slice | Phase | Outcome |
|-------|-------|---------|
| 6a | B.3 R2 | Held |
| 7 | B.3 R3 | Held through spec; D.2 found unrelated B-201 |
| 6b.1 | B.3, D.3 | Both held |
| 6b.2 | B.3, D.3, D.6 | All held; no R2 escalation |

**Interpretation:** The pattern works. v1.2.0 codification (B-2 + fast-path policy) is the right direction. v1.3 should codify the TEMPLATE form (T-17 author-direct variant in Template 06) so it's documented rather than tacit precedent. One caveat: slice-7 trace showed R(N+1) orchestrator-direct closure is safe for surgical revisions, risky for structural — T-5 captures this nuance and should ship.

### Pattern 5: Ontos × forbidden_paths (LOW-MEDIUM confidence — adopter-tool-specific)

**Recurrence: 4 occurrences across slices 6a + 7 (3× in single session).**

| Slice | Entry | Form |
|-------|-------|------|
| 6a | F-048 | ontos auto-regen of forbidden files |
| 7 | F-051 | Same, at Phase A setup |
| 7 | (twice more) | Same, during codex invocations |

**Interpretation:** Tool-side issue (Ontos), not framework-core. T-2 adopter-doc guidance is the right answer; mechanization is outside the bundle's scope. Not a v1.3 must-ship but worth documenting.

---

## 5. What the framework got right (with slice evidence)

Prevents v1.3 from breaking working things.

### 5.1 The 4-lens review board catches real defects

**Evidence across all 9 slices.** Every shipped slice had 0 preserved blockers. The board caught:
- 17 blockers in slice 1 (Pre-A + B + D) — all closed
- 6 blockers in slice 2's B.1 (convergent on SCOPE-1)
- 4 blockers in slice 3's B.1 (AL-1 = "planning-phase finding" validated the pre-implementation exploration step)
- 4 blockers in slice 4's B.1 + 2 blockers in slice 4's D.2 (first slice with D-stage blockers — demonstrates code-review layer adds signal)
- 2 codex-only blockers in slice 6a's B.1 (ADV-001, ADV-002 — schema-bump + lost-update race that NO other lens caught)
- 4 blockers across slice 7's B + D
- 9 blockers across slice 6b.1's B + D
- 8 blockers across slice 6b.2's B + D

**Keep:** 4-lens board. Multi-lens convergence criterion. Adversarial lens (codex specifically for v1.2.0+ under must-differ-provider).

### 5.2 Codex adversarial is load-bearing on structural defects

**Evidence: slice 6a B.1 (2 blockers), slice 6b.1 (2 B.2 + 1 D.2 blocker), slice 6b.2 (blockers at B.1 + D.2).** In slices where codex found blockers, no other lens found the same blocker first.

Exception: slice 7 B.1 where **peer** caught both blockers (PR-1 CLI shape + PR-2 pattern citation). Interpretation: when spec is conceptually clean from the start, mechanical defects dominate and peer wins. Codex's edge is structural reasoning.

**Keep:** must-differ-provider invariant in v1.2.0. Codex adversarial on B.1 R1 + D.2 R1 always. De-emphasize subsequent rounds if R1 returned clean (slice 6a observation).

### 5.3 Orchestrator-direct consolidation (v1.2.0 fast-path) is load-bearing efficiency

**Evidence: 7 applications across 4 slices, all held.** Saves ~10-15 min per closure (avoided 4-lens dispatch). Scales reliably when convergence criterion is met (multiple lenses flag same surgical fix).

**Keep:** B-2 v1.2.0 policy (orchestrator consolidation on unanimous or dominant-verdict). v1.3 should ADD template form (T-17) rather than remove the pattern.

### 5.4 `verify-adopter.sh` + `verify-d6-gate.sh` (v1.2.0 tooling) works first-try

**Evidence: slice 6b.1 passed 4/4 + 15/15 first-attempt; slice 6b.2 passed 4/4 twice + 24/24.** Zero false positives. Adopter confidence improved markedly vs v1.1.0 manual `check-jsonschema` dance.

**Keep:** both scripts. v1.3's T-13 extends this tooling rather than replacing.

### 5.5 Adopter-only contract (post-adopter-authority-divergence) holds cleanly

**Evidence: slices 6a, 7, 6b.1, 6b.2 all shipped with zero bundle edits.** All framework gaps flowed upstream as friction entries (F-047..F-062). Bundle resync at v1.1.1 + v1.2.0 worked mechanically.

**Keep:** adopter-only contract as documented in `docs/framework-adoption.md`. Resync script + johnny-os canonical flow.

### 5.6 Pre-A inheritance (§15.7 narrowing contract)

**Evidence: slices 2, PROV-1, 3, 4, 6a, 7, 6b.1, 6b.2 all inherited Pre-A cleanly.** Only slice 1 ran full Pre-A (3 rounds). The lean-slice path is proven.

**Keep:** inherited Pre-A pattern. T-6 (manifest cite-path clarity) makes this more reliable without changing the pattern.

### 5.7 Circuit-breaker + operator-rescind (halt ladder)

**Evidence: slice 1's 4 halts all operator-rescinded → full A→E delivery; zero halts in slices 2 through 6b.2.** The ladder fires at intended boundaries and is a legitimate escape hatch. v1.2.0's preserved-blocker-ID carry-forward is additive, not replacing.

**Keep:** halt ladder. Operator-rescind flow. v1.2.0's carry-forward improvement.

---

## 6. Concrete v1.3 recommendations (ranked, evidence-merged)

Merge of: still-open from original 25, new friction, cross-slice patterns. Ranked by evidence weight (recurrence × severity).

### Must-ship (5 items — all dispatch-infrastructure + author-process)

| # | Recommendation | Friction refs | Evidence count | Effort |
|---|----------------|---------------|----------------|--------|
| **M-1** | **Escalation ladder for unreachable reviewer families.** Document in `framework.md § P3`: 1h retry → ≤24h halt → >24h documented 3-lens fallback + supplementary round. Proven workable on slice 6b.1. | F-054, F-055, F-060 | 3 slices, 3 different modes | 1 hour doc (T-10) |
| **M-2** | **Phase-C spec-vs-implementation escalation clause in Template 01.** "If you notice spec-vs-implementation divergence during test authoring, STOP and escalate — do NOT write a test that blesses the gap." | F-062; slice 7 B-201 D.2 blocker; slice 4 DC-1 | 3 slices of traceability misses | 1 hour doc (T-16) |
| **M-3** | **Scope-audit pre-phase for lean slices (promoted from B-1 v1.1).** Before Phase A, grep entire codebase for the field/symbol being modified; explicitly include or defer every hit. | Slice 2 SCOPE-1, F-047, F-050 | 3 slices, same root cause | 1 hour doc |
| **M-4** | **Contract-enumeration checklist + model-assignments preflight (promoted from C-12 v1.1).** Phase C template extracts §-level enum tables from the spec and verifies each item has a matching implementation anchor. B.1/D.2 launch templates preflight model_assignments. | F-045, slice 4 DC-1, slice 7 B-201, F-062 | 4 slices of related misses | 2 hours (template + doc) |
| **M-5** | **File-existence verification preamble in ALL reviewer prompt templates (03 peer, 05 adversarial, 19 product).** `git ls-files` + `git rev-parse HEAD` + `git branch --show-current` before claiming a file is absent. | F-053, F-052 (root) | 2 slices (slice 7 — 2× within) | 1 hour (template edit) |

### Should-ship (10 items)

| # | Recommendation | Friction refs | Effort |
|---|----------------|---------------|--------|
| **S-1** | Optional manifest `reviewer_family_substitutes[]` field. Pre-declare operator-authorized swaps (`{primary, substitute, lens, condition}`). Mechanizes the ad-hoc codex-as-X pattern. | F-054, F-055 | 3 hours (schema + verify-p3) (T-11) |
| **S-2** | `verify-p3.sh` cross-checks role assignments against `cli_capability_matrix[<FAMILY>]`. `gemini: verifier` should fail P3 if `gemini.test_runner: false`. | F-055 | 1.5 hours (T-12) |
| **S-3** | `verify-gate-commands.sh` (or extend verify-adopter.sh): actually EXECUTE each `cardinality_assertions[].command` + `gate_prerequisites[].verification.command` at manifest-validation time. | F-056 | 2 hours (T-13) |
| **S-4** | Manifest `scope.allowed_path_patterns: [glob, ...]` alongside explicit list. In-scope if matches any path OR any glob. | F-047 | 1 day (T-1, schema + matcher) |
| **S-5** | Reviewer templates (03 peer, 05 adversarial) add "rule-reachability audit" prompt for validation-layer rule additions. Cite one triggering test case for each new rule. | F-057 | 1 hour (T-14) |
| **S-6** | Template 12 "helper-divergence disclosure" section for first-consumer-of-existing-helper-family. | F-050 | 2 hours (T-7) |
| **S-7** | Template 06 accepts optional `author-direct-with-external-lens-citation` variant; manifest `consolidation_mode` field. | F-029, F-030, F-059 | 3-5 hours combined (T-17 + T-22) |
| **S-8** | Adversarial + peer templates: "test-blessed divergence audit" prompt. Grep test suite for comments documenting spec-vs-code mismatches ("does NOT raise", "accept exit despite", etc). | F-062 | 2 hours combined (T-20 + T-21) |
| **S-9** | Template 01 skip-failing-activation boilerplate — if activation fails, skip with logged note; do NOT loop. | F-060 | 30 min (T-19) |
| **S-10** | `cli_capability_matrix` schema adds `writes_files_non_interactively: bool`. Dispatcher auto-redirects stdout to file when false. Addresses B-4 + current gemini gap. | F-015, F-061 | 2.5 hours (T-18) |

### Defer-or-close (9 items)

| # | Item | Decision | Rationale |
|---|------|----------|-----------|
| B-6 | `<SCOPE_BASE_COMMIT>` token | Defer | Single-occurrence (F-025); multi-slice-branch scenario didn't recur |
| B-7 | `regression_guards[]` inherits-from | Defer | Speculative, no recurrence |
| C-3 (partial) | Rate-limit observability doc | Close | Subsumed by M-1 escalation ladder |
| C-6 | Pre-A posture suffix | Defer | Pre-A ran only once (slice 1) |
| C-8 | Partial-closure first-class state | Defer | Single-occurrence (F-021) |
| C-9 | Codex targeted-prompt template | Close | Mitigated by convention; codifying as template is polish |
| C-10 | Template 12 planner's-findings section | Defer | Single-occurrence (slice 3) |
| C-11 | Forbidden-path globs | Defer | Inversion of shipped T-1; low evidence |
| C-13 | B.1 role-overlap reduction | Defer | Single-occurrence (F-046) |
| C-14 | D.4 line-citation regen | Defer | Polish, low evidence |
| T-3 | "codex adversarial marginal value drops after convergence" ROADMAP entry | Close | Captured as orchestrator guidance; no template change needed |
| T-8 | Orchestrator runbook pre-dispatch branch-pinning | Merge into M-5 | Pre-dispatch check is one half of M-5's file-existence preamble cluster |
| T-15 | `G-scope-N` line-cap authoring guidance | Defer-as-doc | Polish, single-occurrence (F-058) |
| T-2 | Pre-D.6 ontos-revert doc | Already codified | Adopter-side; confirmed at scale |

---

## 7. Parallel-execution observations

Folio ran all 9 slices sequentially. Evidence on whether parallel execution would have changed outcomes:

### 7.1 Sequential runs surfaced friction that parallel would have worsened

- **F-052 branch-state confusion (slice 7)** happened during a SINGLE lifecycle. Parallel lifecycles would compound this — multiple in-flight branches + subprocess state + session-closeout hooks = higher probability of wrong-tree-state reviewer runs. **Sequential masked the severity; parallel would surface it much faster and more painfully.**
- **F-054/F-055 dispatch-infrastructure friction (slice 6b.1)** tied up the gemini CLI for ~6 hours. Parallel lifecycles would have BOTH sessions stuck on the same 429 simultaneously. Compounds rather than distributes the outage. (Orchestrator noted this in pre-sub-slice-2 authorization: "two 4-lens boards in flight means 8+ reviewers simultaneously; gemini rate-limits already contended.")
- **Manifest scope hygiene (F-047, F-056)** would have doubled merge-conflict surface in `CHANGELOG.md`, `docs/retros/llm-dev-v1-adoption.md`, and `frameworks/manifests/framework-learnings-v1.1-adoption.md`. Sequential merge-in-series meant mechanical conflicts only; parallel merge-in-parallel would introduce semantic conflicts on the retros.

### 7.2 Sequential runs that parallel would have neither caught nor missed

Most friction classes are orthogonal to concurrency:
- Author-process issues (scope-audit gaps, helper-divergence, contract-enumeration) are per-slice regardless of sequencing.
- Template gaps (reachability audit, file-existence preamble) are reviewer-prompt-level, unaffected by concurrency.
- v1.2.0 policy strictness is a per-slice interaction, unaffected.

### 7.3 What parallel would likely have caught better

None observed. The sequential runs allowed each slice's retro to inform the next slice's manifest + spec. Parallel would have eliminated this inter-slice learning. Specifically:
- Slice 2's SCOPE-1 learning informed slice 6a's broader pre-phase grep.
- Slice 4's F-045 (forgot codex dispatch) informed slice 6a's checklist discipline.
- Slice 6a's F-047 informed slice 7's manifest authoring.
- Slice 7's F-049/F-050/F-051 informed slice 6b.1's helper-divergence + Phase-0 checklist.
- Slice 6b.1's F-054/F-055 informed slice 6b.2's dispatch preparation + helper-promotion phase-0.

**If slice 6a through 6b.2 had run in parallel, the accumulated learnings would have been lost. Sequential was the right call.**

### 7.4 When parallel would make sense

Parallel is feasible ONLY under these conditions:
1. Disjoint code surfaces (no shared module edits).
2. Disjoint review surfaces (no CHANGELOG / retro / framework-learnings conflict — or mechanical-only conflicts).
3. No shared upstream learning expected between slices.
4. Budget headroom on the CLI dispatch surface (gemini in particular).

In practice none of folio's 9 slices met all four conditions simultaneously. For v1.3 framework users: document that parallel execution is an expert mode, not default, and requires explicit disjointness analysis.

---

## 8. Findings flagged for johnny-os v1.3 merge process

### 8.1 Friction numbering gap (F-031..F-041)

Neither source doc explains the numbering jump from F-030 (slice 2) to F-042 (slice 3). Numbering appears to reserve space without entries — OR entries were authored and later removed. johnny-os v1.3 retro-merge should surface this with folio if reconciliation is needed. Impact on this extraction: none — no recommendations reference F-031..F-041. Treating as informational.

### 8.2 Per-slice retro pattern

The user's extraction prompt asked "all per-slice retros in docs/retros/." Folio has ONE retro file (`docs/retros/llm-dev-v1-adoption.md`) with per-slice sections inside, rather than separate files per slice. The 6+1 framework-learnings supplement pattern lives in `frameworks/manifests/framework-learnings-v1.1-adoption.md` — slice 6a, 7, 6b.1, 6b.2 each have full 6-axis supplements there. Slices 1, 2, PROV-1, 3, 4 do NOT have 6-axis supplements — their retro content lives only in the adoption doc's per-slice sections. Flagging so johnny-os merge process knows not to look for 9 separate files.

### 8.3 F-048 tool-side vs framework-side

F-048 (ontos auto-regen of forbidden files) is correctly identified as adopter-tool-side, not framework-core. T-2 codification is adopter-doc guidance, not framework-bundle work. johnny-os v1.3 should acknowledge but not scope this as a framework deliverable.

### 8.4 C-9 close-as-mitigated

C-9 (codex targeted-prompt template) is mitigated by convention but never formally codified. Recommend closing it as "documentation-only polish" in v1.3 rather than carrying it forward. The targeted-prompt pattern works; templatizing it provides marginal value.

### 8.5 Extraction methodology

This doc applies evidence-weight ranking (recurrence count × severity × class-criticality). johnny-os's own v1.2 retro (21 friction entries cited in the user's context) should merge with folio's 62 via the same evidence-weight logic. The **must-ship 5** in §6 are the items where cross-slice evidence is strongest; these should be weighted highest in the merge regardless of what johnny-os surfaces on the maintainer side.

---

## Appendix A: Friction ID → recommendation cross-reference (folio side only)

Full cross-reference lives in `framework-learnings-v1.1-adoption.md` appendix. Additions since v1.1.0:

| Friction | v1.3 recommendation | Status |
|----------|---------------------|--------|
| F-047 | S-4 (T-1) | should-ship |
| F-048 | T-2 | codified adopter-doc |
| F-049 | S-11 candidate (T-6) | should-ship (see §6) |
| F-050 | S-6 (T-7) | should-ship |
| F-051 | T-2 recurrence | codified |
| F-052 | M-5 (T-8 absorbed) | must-ship |
| F-053 | M-5 (T-4 core) | must-ship |
| F-054 | M-1 (T-10) + S-1 (T-11) + S-2 (T-12) | must-ship + should-ship cluster |
| F-055 | S-2 (T-12) | should-ship |
| F-056 | S-3 (T-13) | should-ship |
| F-057 | S-5 (T-14) | should-ship |
| F-058 | T-15 | defer |
| F-059 | S-7 (T-17 + T-22) | should-ship |
| F-060 | S-9 (T-19) | should-ship |
| F-061 | S-10 (T-18) | should-ship |
| F-062 | M-2 (T-16) + S-8 (T-20/T-21) | must-ship + should-ship |

## Appendix B: v1.3 recommendation totals

- **Must-ship:** 5 (M-1 through M-5)
- **Should-ship:** 10 (S-1 through S-10)
- **Defer or close:** 13 (from original 25's still-open + one-offs)
- **Closed-as-mitigated-by-convention:** 1 (C-9)

15 recommendations to weigh in v1.3 scoping (5 must + 10 should). Comparable in magnitude to v1.2.0's shipped surface (6 items in v1.2.0 + 5 items in v1.1.1 = 11). v1.3 is a similarly-sized bundle revision by count, but with a higher dispatch-infrastructure concentration.
