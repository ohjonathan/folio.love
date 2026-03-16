# Diagram Extraction Implementation Checklist

**Started:** 2026-03-14
**Proposal:** Final — approved for implementation
**Playbook:** LLM Development Playbook v3.3.1, Tier 1 Agent Team Review
**Test suite:** 506 (baseline) → 621 (PR 1) → 693 (PR 2) → 777 (PR 3) → 897 (PR 4) → 1010 (PR 5)

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
  - [x] Merged — main at `97f03b9`
  - **Outcome:** Diagram extraction runtime, separate diagram caches, Pass A/B/C plus dense sweep, confidence scoring, and dev iteration harness merged on main
  - **Delivery shape:** Shipped as one PR; approved 4a/4b split boundary was not needed

- [x] **PR 5:** Deterministic Rendering + Mermaid + Entity Resolution (2-2.5 days) — **PR #23 MERGED**
  - [x] CA prompt generated
  - [x] CA implementation prompt generated
  - [x] Developer implements — PR #23 created
  - [x] Review Team prompt generated
  - [x] Review Team executes
  - [x] CA cross-check + fixes
  - [x] Tests pass (1007 passed, 3 skipped; 1010 collected)
  - [x] Merged — main at `bced524`
  - **Outcome:** Deterministic Mermaid rendering, graph-bound prose, component/connection tables, entity resolution, and Mermaid parser validation merged on main

- [ ] **PR 6:** Output Assembly + Standalone Notes + Freeze + Review History (3-3.5 days)
  - [ ] CA prompt generated
  - [ ] CA implementation prompt generated
  - [ ] Developer implements
  - [ ] Review Team prompt generated
  - [ ] Review Team executes
  - [ ] CA cross-check + fixes
  - [ ] Tests pass, no regressions
  - [ ] Merged

- [ ] **Model Comparison Testing** (7-9 days, after PR 5)

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
  - Minimum needed: 5-10 diagram pages covering simple, medium, and dense; at least 2 system architecture and 2 data flow
- [ ] **Model Comparison:** 20-30 diagram pages from engagement materials
- [ ] **Model Comparison:** Two annotators for 5-page inter-annotator agreement

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
| PR 4 | Pre-implementation readiness check | **Completed.** Six questions answered by Codex CA. Key findings shaped PR 4 prompt. | 2026-03-15 |
| PR 4 | Diagram extraction runtime | **Merged** — separate diagram caches, Pass A/B/C, dense-only completeness sweep, confidence scoring, and `tools/diagram_iterate.py` shipped on main | 2026-03-15 |
| PR 4 | Split PR 4 by day 3? | **No split needed** — shipped as a single PR (`#22`) | 2026-03-15 |
| PR 4 | Supported diagram types for v1 extraction | **Strict allowlist** — `architecture` and `data-flow` only; all other types abstain | 2026-03-15 |
| PR 5 | Deterministic rendering layer | **Merged** — Mermaid, prose, tables, and technology entity resolution generated from graph data only | 2026-03-15 |
| PR 5 | Obsidian Mermaid transclusion gate for PR 6 | **Pass** — synthetic plus real PR 5 renderer output transcluded correctly in Obsidian `1.12.4` | 2026-03-16 |

---

## Carried-Forward Findings (Cumulative)

All findings from PR 1-3 reviews and the PR 4 readiness check that constrain downstream PRs. CA must read before writing any implementation prompt.

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
1. **Separate diagram cache required.** `.analysis_cache.json` / `.analysis_cache_deep.json` have file-global `_prompt_version` tied to consulting-slide prompts. PR 4 must build `.analysis_cache_diagram.json` (or equivalent) with its own version markers.
2. **`ProviderInput` has no `system_prompt` field.** Single `prompt` string + images tuple only. All prompt content goes in one string.
3. **`ImagePart.role` is free-form string.** Not an enum.
4. **No runtime callers for `prepare_images()` or `highlight_regions()` outside tests.** PR 4 builds the first real diagram LLM path.
5. **`assess_review_state()` keys off `abstained`, not `review_required`.** All abstention paths must set `abstained=True`.
6. **`unsupported_diagram` never emitted by inspection.** PR 4 must implement this classification in the extraction flow (after Pass A identifies diagram type).
7. **`_stable_signature()` is dead code.** Do not assume it exists.
8. **CLI `--passes` only accepts `1` or `2`.** PR 4's internal A/B/C/sweep stages should not assume new CLI pass numbers.
9. **Riskiest integration: coordinate-space join.** No code yet does `PDF bbox → pixel highlight overlay → multi-image LLM call → verified graph update` end-to-end. Transform helpers note rendered-overlay validation was deferred.
10. **No eval harness exists.** Only `folio convert --no-cache` / `folio batch --no-cache`. PR 4 includes a lightweight iteration harness.
11. **PR 4 split boundary validated.** 4a (A+B) / 4b (C+sweep+confidence) is the right cut. Intermediate object: DiagramAnalysis with graph populated, no verification data.

### PR 4 Review Findings
1. **V1 type gate is strict.** Only `architecture` and `data-flow` continue through extraction. All other detected types abstain.
2. **Sanity short-circuit is mutation-accounting based.** Thresholds are no longer graph-size delta based; later PRs should preserve the accounting-driven thresholds and reasons.
3. **Pass C highlights are claim-relevant and per-batch.** Dense-diagram verification should not revert to all-node overlays.
4. **IoU inheritance depends on stale-cache lookup.** `diagram_cache.load_stale_entry()` intentionally bypasses marker validation so ID inheritance survives prompt/model drift.
5. **Verification attempt and verification success are distinct.** `pass_c_attempted` and `pass_c_verdicts_parsed` are both needed; later PRs must not collapse them.
6. **Abstention coverage expanded.** Unsupported types, empty graphs, and low-confidence outputs all abstain; supported diagrams may still carry `review_required` and `review_questions` without abstaining.
7. **Sweep discoveries are weak signals.** Sweep-added edges are capped low-confidence (`<= 0.5`) and should stay review-flagged downstream.
8. **Mixed-page behavior is now explicit.** Consulting-slide inherited fields remain for mixed pages and diagram evidence is appended rather than replacing them.

### PR 5 Review Findings
1. **Mermaid parser validation is a real test-time dependency.** Preserve the Node-based Mermaid validation harness instead of bypassing it.
2. **Group membership must reconcile `group.contains` and `node.group_id`.** Later output logic must not trust `group.contains` alone or regrouped nodes may disappear.
3. **Render-time omit-and-flag is an invariant.** Unsafe labels or omitted Mermaid elements must surface through `uncertainties` and `review_required`, not fail silently.
4. **Unknown or malformed edge directions render conservatively.** Later PRs must not re-infer direction semantics from rendered Mermaid text.
5. **Converter ordering matters.** Deterministic rendering runs before `assess_review_state()` so render-time flags are visible to review/frontmatter logic.
6. **Supported diagrams can still be review-heavy.** Abstained-with-graph, low-confidence, and sweep-discovered elements are expected runtime states and must be surfaced downstream.

---

## Risks Realized

| Risk | PR | What Happened | Resolution |
|------|----|---------------|------------|
| pypdfium2 bounding boxes unreliable on dense pages | PR 1 | Real-corpus SoM validation failed acceptance bar on dense material, driven by systematic failure cluster in `dense_06_target_state_arch.pdf` | Locked PR 2 to tiles instead of SoM |
| Raster-only blank detection needed separate handling | PR 1 | Structural blank detection alone missed raster-only blank pages | Added `image_blank` + histogram confirmation path |
| Soft pdfium text failure could misclassify pages | PR 1 | pdfium word extraction returned empty while pdfplumber still found text | Added pdfium → pdfplumber fallback |
| Rate-limit/runtime edge cases | PR 2 | Shared fallback throttling bugs, TPM limiter loop, partial-progress/cache-flush gaps | Fixed before merge in PR #20 follow-up commits |
| Mixed-provider cache provenance under-reported | PR 2 | Warm-cache and mixed hit/miss runs drifted from actual per-slide provider usage | Fixed with narrow cache-hit provenance follow-up |
| Stable edge identity and partial warm-cache payloads | PR 3 | Order-sensitive same-pair edge IDs and partial diagram payloads surfacing too cleanly | Fixed with deterministic parallel-edge disambiguation and pending/review-required coercion |
| PR 4 first-integration runtime surfaced extraction-specific correctness gaps | PR 4 | Broad type gate, all-node highlight overlays, stale-cache ID inheritance loss, and weak abstention coverage produced inaccurate or overly clean outputs | Fixed before merge via strict type allowlist, per-batch claim-relevant highlights, `load_stale_entry()` for IoU inheritance, and broader abstention/review handling |
| Deterministic rendering surfaced graph-shape/runtime mismatches | PR 5 | Regrouped nodes could be omitted if rendering trusted `group.contains` alone; malformed edge directions and unsafe Mermaid labels needed conservative handling | Fixed before merge with group-membership reconciliation, conservative direction normalization, omit-and-flag behavior, and Mermaid parser-backed validation |

---

## Regressions / Known Limitations

| Issue | PR | Status |
|-------|----|--------|
| `som_viable` is lexical-only, not spatial overlay validated | PR 1 | Known limitation; documented for any future SoM revisit |
| `text_light` / `image_blank` classifications added during review; downstream must use merged runtime enums | PR 1 | Resolved; merged code is source of truth |
| Real-corpus diagram PDFs are still not repo assets | PR 4 | Known execution constraint; prompt tuning depends on externally supplied corpus |
| Diagram extraction v1 only supports `architecture` and `data-flow` | PR 4 | Intentional scope boundary; other diagram types abstain |
| Supported diagrams can still be review-heavy | PR 4 | Expected runtime state; low-confidence nodes, sweep discoveries, and open questions must be handled by PR 5/PR 6 |
| Mermaid transclusion validation is environment-specific | PR 5 | Validated on macOS + Obsidian `1.12.4`; sufficient for current scope but not a cross-platform guarantee |
| Standalone diagram notes and deck-level output assembly are still not implemented | PR 5 | PR 6 owns transclusion-based output assembly, review sections, and freeze/history behavior |
