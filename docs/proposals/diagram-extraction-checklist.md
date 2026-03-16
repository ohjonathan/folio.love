# Diagram Extraction Implementation Checklist

**Started:** 2026-03-14
**Proposal:** Final — approved for implementation
**Playbook:** LLM Development Playbook v3.3.1, Tier 1 Agent Team Review
**Test suite:** 506 (baseline) → 621 (PR 1) → 693 (PR 2) → 777 (PR 3) → 897 (PR 4) → 1010 (PR 5) → 1054 (PR 6)
**Status:** All 6 production PRs merged. Model comparison testing next.

---

## PR Sequence

- [x] **PR 1:** Page Inspection + Blank Fix + Coordinates + Set-of-Mark Validation (2-2.5 days) — **PR #19 MERGED**
  - [x] CA prompt generated (orchestrator)
  - [x] CA implementation prompt generated (Claude Code)
  - [x] Developer implements — PR #19 created
  - [x] Review Team prompt generated (orchestrator)
  - [x] Review Team executes (Claude Code agent team)
  - [x] CA cross-check (Codex)
  - [x] Fixes applied
  - [x] Decision output: Set-of-Mark viability verdict
  - [x] Tests pass (615 passed, 3 skipped; 621 collected)
  - [x] Merged
  - **Outcome:** SoM NOT VIABLE → PR 2 uses tiles (global + quadrant crops)

- [x] **PR 2:** Provider Abstraction + DPI + Rate Limiting + Tiles Image Strategy (2.5-3 days) — **PR #20 MERGED**
  - [x] CA prompt generated (orchestrator)
  - [x] CA implementation prompt generated (Claude Code)
  - [x] Developer implements — PR #20 created
  - [x] Review Team prompt generated (orchestrator)
  - [x] Review Team executes (Claude Code agent team)
  - [x] CA cross-check + fixes
  - [x] Tests pass (690 passed, 3 skipped; 693 collected)
  - [x] Merged
  - **Outcome:** Provider runtime, per-page DPI, tiles/highlights infrastructure, rate limiting/retry, cache-hit provenance fixes merged on main

- [x] **PR 3:** Schema + Routing + Cache + Deserialization Factory (2-2.5 days) — **PR #21 MERGED**
  - [x] CA prompt generated (orchestrator)
  - [x] CA implementation prompt generated (Claude Code)
  - [x] Developer implements — PR #21 created
  - [x] Review Team prompt generated (orchestrator)
  - [x] Review Team executes (Claude Code agent team)
  - [x] CA cross-check + fixes
  - [x] Tests pass (774 passed, 3 skipped; 777 collected)
  - [x] Merged — main at f9ac21f
  - **Outcome:** DiagramAnalysis schema, polymorphic deserialization, diagram/mixed Pass 2 exclusion, abstention handling, IoU-based node ID inheritance, stable edge-ID rewriting, cache version/invalidation markers merged on main

- [x] **PR 4:** Extraction Prompts + Pass A/B/C + Completeness Sweep + Confidence (5-7 days) — **PR #22 MERGED**
  - [x] Pre-PR 4 readiness check completed (orchestrator → Codex CA)
  - [x] CA prompt generated (orchestrator)
  - [x] CA implementation prompt generated (Claude Code)
  - [x] Developer implements — PR #22 created
  - [x] Review Team prompt generated (orchestrator)
  - [x] Review Team executes
  - [x] CA cross-check + fixes
  - [x] Tests pass (894 passed, 3 skipped; 897 collected)
  - [x] Merged — main at 97f03b9
  - **Outcome:** Diagram extraction runtime, separate diagram caches, Pass A/B/C plus dense sweep, confidence scoring, and dev iteration harness merged on main
  - **Delivery shape:** Shipped as one PR; approved 4a/4b split boundary was not needed

- [x] **PR 5:** Deterministic Rendering + Mermaid + Entity Resolution (2-2.5 days) — **PR #23 MERGED**
  - [x] CA prompt generated (orchestrator)
  - [x] CA implementation prompt generated (Claude Code)
  - [x] Developer implements — PR #23 created
  - [x] Review Team prompt generated (orchestrator)
  - [x] Review Team executes
  - [x] CA cross-check + fixes
  - [x] Tests pass (1007 passed, 3 skipped; 1010 collected)
  - [x] Merged — main at bced524
  - **Outcome:** Deterministic Mermaid rendering, graph-bound prose, component/connection tables, entity resolution, and Mermaid parser validation merged on main

- [x] **PR 6:** Output Assembly + Standalone Notes + Freeze + Review History (3-3.5 days) — **PR #24 MERGED**
  - [x] CA prompt generated (orchestrator)
  - [x] CA implementation prompt generated (Claude Code)
  - [x] Developer implements — PR #24 created
  - [x] Review Team prompt generated (orchestrator)
  - [x] Review Team executes
  - [x] CA cross-check + fixes
  - [x] Tests pass (1051 passed, 3 skipped; 1054 collected)
  - [x] Merged — main at 5afdfac
  - **Outcome:** Standalone diagram notes, deck-note transclusion, freeze bypass with frozen-note hydration, diagram-aware deck frontmatter/tags, and initialized review-history fields merged on main

- [ ] **Model Comparison Testing** (7-9 days, after PR 6)

---

## Manual Action Items

- [x] **Week 1:** Test Obsidian transclusion with Mermaid blocks (15 min manual test)
  - Result: works — PR 6 uses section transclusion (`![[note#section]]`)
  - Validation artifact: `docs/validation/obsidian_transclusion_test_result.md`
- [x] **PR 1:** Provide 5-10 real corpus PDFs for Set-of-Mark validation
  - Location: `/Users/Jonathan_Oh/tmp/diagram_som_corpus`
  - Validation set: 8 PDFs, 25 diagram/mixed pages
- [x] **PR 4:** Real corpus diagrams available for prompt iteration
  - Status: used during PR 4 prompt tuning, but still an external prerequisite rather than a checked-in repo asset
  - Note: prior validation corpus path from PR 1 is recorded, but the PDFs are not assumed to be present on every machine
- [ ] **Model Comparison:** 20-30 diagram pages from engagement materials
- [ ] **Model Comparison:** Two annotators for 5-page inter-annotator agreement
- [ ] **Model Comparison:** Define annotation rules before starting

---

## Decision Log

| PR | Decision | Verdict | Date |
|----|----------|---------|------|
| PR 1 | Set-of-Mark viability (pypdfium2 bounding boxes) | **Not viable** — overall `0.76`, medium/dense `0.722`, systematic dense-page failures | 2026-03-14 |
| PR 1 | Obsidian transclusion with Mermaid | **Pass** — use section transclusion (`![[note#section]]`) in PR 6 | 2026-03-16 |
| PR 2 | Image strategy (SoM primary vs tiles fallback) | **Tiles** (global + quadrant crops) | 2026-03-14 |
| PR 2 | Provider/runtime implementation | **Merged** — consulting-slide path uses multi-image provider contract with one `global` image; tiles/highlights remain PR 4 infrastructure | 2026-03-15 |
| PR 3 | Data model / routing / cache foundation | **Merged** — DiagramAnalysis, factory deserialization, image-hash cache markers, abstention flow, Pass 2 exclusion | 2026-03-15 |
| PR 3 | Cache contract for diagram work | **Image-hash keyed + invalidation markers** (`_schema_version`, `_pipeline_version`, `_image_strategy_version`); composite cache-key deferred | 2026-03-15 |
| PR 4 | Pre-implementation readiness check | **Completed.** Six questions answered by Codex CA. Key findings shaped PR 4 prompt (five codebase-vs-proposal mismatches caught). | 2026-03-15 |
| PR 4 | Diagram extraction runtime | **Merged** — separate diagram caches, Pass A/B/C, dense-only completeness sweep, confidence scoring, and `tools/diagram_iterate.py` shipped on main | 2026-03-15 |
| PR 4 | Split PR 4 by day 3? | **No split needed** — shipped as a single PR (#22) | 2026-03-15 |
| PR 4 | Supported diagram types for v1 extraction | **Strict allowlist** — `architecture` and `data-flow` only; all other types abstain | 2026-03-15 |
| PR 5 | Deterministic rendering layer | **Merged** — Mermaid, prose, tables, and technology entity resolution generated from graph data only | 2026-03-15 |
| PR 5 | Obsidian Mermaid transclusion gate for PR 6 | **Pass** — synthetic plus real PR 5 renderer output transcluded correctly in Obsidian 1.12.4 | 2026-03-16 |
| PR 6 | Output assembly + freeze support | **Merged** — standalone diagram notes, deck transclusion, freeze bypass, and diagram-aware deck metadata shipped on main | 2026-03-16 |
| PR 6 | Graphless abstentions in deck metadata | **Excluded** — abstained pages with `graph=None` do not contribute to deck-level `diagram_types` | 2026-03-16 |
| PR 6 | Frozen mixed slide cost model | **Keep consulting Pass 1** — only the diagram path bypasses for frozen mixed slides | 2026-03-16 |

---

## Success Criteria Status

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Zero diagram pages destroyed (no `pending()` override) | **MET** | PR 1 blank override fix; PageProfile gates post-LLM override |
| 2 | Node label recall > 95% on test corpus | **Pending** | Requires model comparison testing |
| 3 | Edge recall > 85% simple/medium, > 70% dense | **Pending** | Requires model comparison testing |
| 4 | Edge direction accuracy > 90% | **Pending** | Requires model comparison testing |
| 5 | Mermaid syntactically valid > 99% | **MET** | Deterministic generation + sanitization + omit-and-flag + CI parser validation (`tests/mermaid`) |
| 6 | Every diagram page produces standalone note or explicit abstention | **MET** | PR 6 standalone emitter; abstained pages produce notes with explanation + source image |
| 7 | Every extraction includes confidence_reasoning and review_questions | **MET** | PR 4 confidence scoring; dual-path (text-rich / text-poor) |
| 8 | Claim-level verification on every node and edge | **MET** | PR 4 Pass C batched verification with claim-relevant highlights |
| 9 | Human overrides preserved across re-processing | **MET** | folio_freeze bypass + IoU-based ID inheritance + frontmatter `human_overrides` merge |
| 10 | No regressions on existing test suite | **MET** | 506 → 1054, all green, no regressions across 6 PRs |
| 11 | Model comparison completed with weighted rubric | **Pending** | Requires model comparison testing |
| 12 | Confidence calibration measured | **Pending** | Requires model comparison testing |
| 13 | Privacy/compliance confirmed with endpoint-level controls | **MET** | PR 2 provider config with per-provider endpoint restrictions |
| 14 | Review history captured for continuous learning | **MET** | `_review_history` initialized as append-only list; structure defined for reviewer edits |
| 15 | System honestly framed | **MET** | "Extracts at high quality and flags what needs checking" — abstention, review_required, confidence_reasoning, review_questions all implemented |

**9/15 criteria met. 6 pending model comparison testing.**

---

## Carried-Forward Findings (Complete)

All findings from PR 1-6 reviews and the PR 4 readiness check. Reference for model comparison testing, future maintenance, and subsequent feature work.

### PR 1 Review Findings
1. **`som_viable` is lexical-only, not spatial-overlay validated.** If SoM is revisited, spatial validation required.
2. **`image_blank` requires hybrid blank gating** (histogram confirmation). Must not be bypassed by later PRs.
3. **`pdfium → pdfplumber` fallback added.** Downstream code should not assume pypdfium2 always succeeds.
4. **`inspect_pages()` degrades per-page.** Handle pages with partial/degraded PageProfiles.
5. **Classification enums expanded.** `text_light` and `image_blank` exist in merged code. Use codebase values, not proposal's original list.

### PR 2 Review Findings
1. **Tiles/highlights are infrastructure only.** Consulting-slide runtime uses single `global` image. PR 4 is the first PR to wire tiles/highlights into diagram prompts.
2. **`per_slide_providers` is provenance source of truth.** Don't rely on summary booleans.
3. **Partial-progress preservation is an invariant.** Per-miss cache flushes; later failures don't discard earlier pages.
4. **TPM limiter is best-effort and usage-driven.** Don't assume pre-reservation.
5. **Shared runtime layer for retry/throttle.** Reuse, don't reimplement.
6. **`image_blank` blank gating remains in force.**

### PR 3 Review Findings
1. **`SlideAnalysis.from_dict()` is the required polymorphic entry point.** Do not manually reconstruct analyses. Marker-only payloads route to DiagramAnalysis and surface as pending/review-required.
2. **Routing contract is live.** `diagram`, `mixed`, `unsupported_diagram` skip consulting-slide Pass 2. `unsupported_diagram` bypasses both passes → abstained DiagramAnalysis.
3. **Abstention pattern established.** `DiagramAnalysis(abstained=True)` excluded from provider-failure buckets, emits `diagram_abstained_slide_N`. Reuse `abstained + review_required` — do NOT invent a second review-state path.
4. **Stable ID contract fixed.** Arbitrary node IDs, IoU inheritance, edge IDs derived from final source_id + target_id with deterministic disambiguation for parallel edges. Do NOT hash labels into IDs.
5. **Cache is image-hash keyed with invalidation markers.** Extend this contract; per-miss flushes remain mandatory.
6. **Output is polymorphism-safe but rendering not implemented.** DiagramAnalysis accepted by markdown/frontmatter. Diagram-specific rendering is PR 5/PR 6.

### PR 4 Readiness Check Findings (Codex CA, verified on f9ac21f)
1. **Separate diagram cache required.** `.analysis_cache.json` / `.analysis_cache_deep.json` have file-global `_prompt_version` tied to consulting-slide prompts. PR 4 built `.analysis_cache_diagram.json` with its own version markers.
2. **`ProviderInput` has no `system_prompt` field.** Single `prompt` string + images tuple only.
3. **`ImagePart.role` is free-form string.** Not an enum.
4. **No runtime callers for `prepare_images()` or `highlight_regions()` outside tests.** PR 4 built the first real diagram LLM path.
5. **`assess_review_state()` keys off `abstained`, not `review_required`.** All abstention paths set `abstained=True`.
6. **`unsupported_diagram` never emitted by inspection.** PR 4 implemented this classification in the extraction flow.
7. **`_stable_signature()` is dead code.** Not used.
8. **CLI `--passes` only accepts `1` or `2`.** Internal A/B/C stages don't assume new CLI pass numbers.
9. **Riskiest integration: coordinate-space join.** First end-to-end `PDF bbox → pixel highlight → multi-image LLM → graph update` built in PR 4.
10. **No eval harness existed.** PR 4 added `tools/diagram_iterate.py`.
11. **PR 4 split boundary validated.** 4a (A+B) / 4b (C+sweep+confidence). Not needed; shipped as one PR.

### PR 4 Review Findings
1. **V1 type gate is strict.** Only `architecture` and `data-flow` continue through extraction. All other detected types abstain.
2. **Sanity short-circuit is mutation-accounting based.** >40% overall mutation ratio OR >50% action dominance. Not the proposal's original >30% nodes / >40% edges.
3. **Pass C highlights are claim-relevant and per-batch.** Broad all-node overlays were too noisy on dense diagrams; reverted to targeted highlights.
4. **IoU inheritance depends on stale-cache lookup.** `diagram_cache.load_stale_entry()` intentionally bypasses marker validation so ID inheritance survives prompt/model drift.
5. **Verification attempt and verification success are distinct.** `pass_c_attempted` and `pass_c_verdicts_parsed` are both needed; do not collapse them.
6. **Abstention coverage expanded.** Unsupported types, empty graphs, and low-confidence outputs all abstain. Supported diagrams may still carry `review_required` and `review_questions` without abstaining.
7. **Sweep discoveries are weak signals.** Capped at ≤ 0.5 confidence, stay review-flagged downstream.
8. **Mixed-page behavior is explicit.** Consulting-slide inherited fields remain; diagram evidence is appended, not replacing.

### PR 5 Review Findings
1. **Mermaid parser validation is a real test-time dependency.** Preserve the Node-based Mermaid validation harness (`tests/mermaid`).
2. **Group membership must reconcile `group.contains` and `node.group_id`.** PR 4's `regroup` updates only `node.group_id`; output logic that trusts `group.contains` alone silently loses regrouped nodes.
3. **Render-time omit-and-flag is an invariant.** Unsafe labels or omitted Mermaid elements surface through `uncertainties` and `review_required`, not silent degradation.
4. **Unknown or malformed edge directions render conservatively.** Do not re-infer direction semantics from rendered Mermaid text.
5. **Converter ordering matters.** Deterministic rendering runs before `assess_review_state()` so render-time flags are visible to review/frontmatter logic.
6. **Supported diagrams can still be review-heavy.** Abstained-with-graph, low-confidence, and sweep-discovered elements are expected runtime states and must be surfaced downstream.

### PR 6 Review Findings
1. **Graphless abstentions are excluded from deck-level `diagram_types`.** Output surfaces the note and source image, but deck aggregation does not advertise a diagram type when no graph was extracted.
2. **Freeze protection fails closed.** If an existing standalone note cannot be parsed safely, preserve it and do not overwrite during reprocessing.
3. **Frontmatter fence parsing is stricter and shared.** Closing `---` must be column-0-only (rstrip, not strip); converter and diagram-note parsing share one helper. Reuse that path.
4. **Frozen mixed slides still incur consulting Pass 1 cost.** Merged behavior bypasses only the diagram path; mixed-page slide analysis remains intact.
5. **`unsupported_diagram` routing and freeze parsing robustness hardened during review.** Fail-safe branches must be preserved.
6. **Standalone diagram notes remain deck-local vault notes, not registry entries.** Registry logic stays deck-only unless explicitly redesigned.

---

## Risks Realized (Complete)

| Risk | PR | What Happened | Resolution |
|------|----|---------------|------------|
| pypdfium2 bounding boxes unreliable on dense pages | PR 1 | Real-corpus SoM validation failed acceptance bar on dense material, driven by systematic failure cluster in `dense_06_target_state_arch.pdf` | Locked PR 2 to tiles instead of SoM |
| Raster-only blank detection needed separate handling | PR 1 | Structural blank detection alone missed raster-only blank pages | Added `image_blank` + histogram confirmation path |
| Soft pdfium text failure could misclassify pages | PR 1 | pdfium word extraction returned empty while pdfplumber still found text | Added pdfium → pdfplumber fallback |
| Rate-limit/runtime edge cases | PR 2 | Shared fallback throttling bugs, TPM limiter loop, partial-progress/cache-flush gaps | Fixed before merge in PR #20 follow-up commits |
| Mixed-provider cache provenance under-reported | PR 2 | Warm-cache and mixed hit/miss runs drifted from actual per-slide provider usage | Fixed with narrow cache-hit provenance follow-up |
| Stable edge identity and partial warm-cache payloads | PR 3 | Order-sensitive same-pair edge IDs and partial diagram payloads surfacing too cleanly | Fixed with deterministic parallel-edge disambiguation and pending/review-required coercion |
| PR 4 first-integration surfaced extraction correctness gaps | PR 4 | Broad type gate, all-node highlight overlays, stale-cache ID inheritance loss, and weak abstention coverage produced inaccurate or overly clean outputs | Fixed via strict type allowlist, per-batch claim-relevant highlights, `load_stale_entry()` for IoU inheritance, and broader abstention/review handling |
| Deterministic rendering surfaced graph-shape mismatches | PR 5 | Regrouped nodes omitted when rendering trusted `group.contains` alone; malformed edge directions and unsafe Mermaid labels needed conservative handling | Fixed with group-membership reconciliation, conservative direction normalization, omit-and-flag behavior, and Mermaid parser-backed validation |
| Output assembly exposed note-integrity edge cases | PR 6 | Graphless abstentions polluted deck metadata, frozen-note parsing could overwrite human work, and loose frontmatter fence parsing broke round-trip safety | Fixed via graphless-abstention exclusion, fail-closed freeze handling, shared strict frontmatter parsing, and unsupported/frozen-path hardening |

---

## Regressions / Known Limitations

| Issue | PR | Status |
|-------|----|--------|
| `som_viable` is lexical-only, not spatial overlay validated | PR 1 | Known limitation; documented for any future SoM revisit |
| `text_light` / `image_blank` classifications added during review; downstream must use merged runtime enums | PR 1 | Resolved; merged code is source of truth |
| Real-corpus diagram PDFs are still not repo assets | PR 4 | Known execution constraint; prompt tuning depends on externally supplied corpus |
| Diagram extraction v1 only supports `architecture` and `data-flow` | PR 4 | Intentional scope boundary; other diagram types abstain |
| Supported diagrams can still be review-heavy | PR 4 | Expected runtime state; low-confidence nodes, sweep discoveries, and open questions are normal |
| Mermaid transclusion validation is environment-specific | PR 5 | Validated on macOS + Obsidian 1.12.4; sufficient but not a cross-platform guarantee |
| Frozen mixed slides still incur consulting Pass 1 cost | PR 6 | Intentional merged behavior; only the diagram path bypasses on frozen mixed pages |
| Standalone diagram notes are deck-local vault notes, not registry entries | PR 6 | Intentional scope boundary; registry remains deck-only unless redesigned later |

---

## Process Learnings

### What worked
1. **Pre-PR readiness checks for integration PRs.** The PR 4 readiness check was the highest-value intervention in the sequence. It caught five codebase-vs-proposal mismatches (no `system_prompt` on ProviderInput, image-hash cache not composite, `assess_review_state` keying off `abstained` not `review_required`, dead `_stable_signature`, no runtime callers for tiles/highlights). Without it, the PR 4 prompt would have been wrong in five places. Worth doing before any PR that's the first real integration of prior infrastructure.

2. **Carried-forward findings prevented drift.** Every review surfaced things the proposal didn't anticipate (mutation-accounting sanity check, group membership reconciliation, frontmatter fence parsing, frozen mixed-page cost model). Logging these and front-loading them in the next PR's prompt kept the codebase coherent across six PRs written by different agent sessions with no shared memory.

3. **Tier 1 agent team review caught real bugs.** PR 6 alone: 5 blocking, 6 should-fix, 19 minor issues resolved before merge. Not ceremony — real defect prevention. The review prompts with role-specific mandates (peer/alignment/adversarial) consistently surfaced different categories of issues.

4. **Decision gates prevented wasted work.** SoM viability verdict (PR 1 → PR 2), transclusion test (PR 5 → PR 6), and the PR 4 split boundary were all resolved before the dependent PR started. No conditional forks in implementation prompts.

5. **Playbook discipline on prompt freshness.** Every prompt generated fresh with current context. No "same as last time but change the PR number." Each review prompt included the accumulated carry-forward findings and codebase-specific constraints from prior PRs.

### What to improve
1. **Obsidian transclusion test should have been done in week 1, not after PR 5.** It was on the manual action items from day one but slipped. The test took 15 minutes and the result was needed for PR 6. Starting it earlier would have removed uncertainty sooner.

2. **The proposal's thresholds and data models drifted during implementation.** Sanity check thresholds, cache key scheme, classification enums, and ProviderInput contract all changed from the proposal. The readiness check and carry-forward findings caught these, but a more systematic "proposal drift register" would have made this explicit earlier.

3. **Real corpus availability should be a day-1 prerequisite, not a PR 4 concern.** The corpus was needed for prompt iteration but wasn't guaranteed to be available. Making it a hard prerequisite before starting PR 1 would have been cleaner.

---

## Next Phase: Model Comparison Testing

**Effort:** 7-9 days
**Status:** Pending
**Prerequisites:** 20-30 diagram pages from engagement materials, two annotators, annotation rules defined before starting

**From proposal:**
- Corpus: 20-30 diagram pages, system architecture and data flow only
- Ground-truth annotation (4-5 days): annotation rules first, inter-annotator agreement on 5-page subset
- Pipeline runs (3-4 days): 75+ runs (25 diagrams × 3 models)
- Models: Claude Sonnet 4.6, GPT-4o/5.4, Gemini 2.5/3.1 Pro
- Dev harness: `tools/diagram_iterate.py` (built in PR 4)
- Evaluation: weighted operational rubric (13 metrics)
- Selection: quality primary; cost, latency, stability, compliance as secondary

**Pending success criteria (6 of 15):**

| # | Criterion | What Testing Must Prove |
|---|-----------|------------------------|
| 2 | Node label recall > 95% | Measured on annotated corpus across all three models |
| 3 | Edge recall > 85% simple/medium, > 70% dense | Measured by complexity tier |
| 4 | Edge direction accuracy > 90% | On detected edges |
| 11 | Model comparison completed with weighted rubric | Full rubric applied to 75+ runs |
| 12 | Confidence calibration measured | Predicted confidence vs actual accuracy on corpus |
| 6* | Stability across retries | Same diagram, multiple runs, output consistency |

*Criterion 6 is already met structurally (every page produces a note or abstention) but stability across retries is a model comparison metric from the proposal's evaluation rubric.
