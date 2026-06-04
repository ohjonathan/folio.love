# Issue #76 Validation Report — Slide-Scoped Diagram Retries & Stronger Extraction

**Date:** 2026-06-04
**Validator:** Automated implementation + regression run (Claude Code)
**Scope:** GitHub issue #76 — public diagram retry ergonomics + broadened extraction
**Pipeline version:** folio 1.4.0 (Unreleased; branch `feat/issue-76-diagram-retry-extraction`)
**LLM calls:** None (all tests use mocked providers / pure unit paths)

---

## Summary

A real PPTX conversion hit transient provider failures on diagram slides 35/36/39,
which the public CLI could not retry surgically, and the extractor still abstained
on `concept-map`/`process`. This change adds public slide-scoped retry flags, a
surgical retry path that reuses cache and refreshes only affected artifacts,
first-class `concept-map`/`process` support with a structured inventory, a
payload-reduction fallback, and an end-of-run retry-candidate summary.

| Metric | Value |
|--------|-------|
| New CLI flags | `--slides`, `--diagrams-only`, `--retry-failed-diagrams`, `--retry-review-required-diagrams` |
| New surgical path | `FolioConverter.convert_diagrams()` |
| New diagram-notes helpers | `discover_retry_candidates`, `collect_diagram_retry_candidates`, `format_retry_candidate_summary`, `_build_structured_inventory` |
| New tests (`test_diagram_retry.py`) | 23 passed |
| Full suite | 2125 passed, 6 skipped |
| Live provider calls | 0 |

---

## Requested capabilities → evidence

### 1. Public slide-scoped / rerun options
| Item | Status | Evidence |
|------|--------|----------|
| `--slides`, `--diagrams-only`, `--retry-failed-diagrams`, `--retry-review-required-diagrams` | ✅ | `folio/cli.py` `convert`; `TestConvertCliDiagramFlags::*` (dispatch, `--slides` guard, invalid-value guard). |
| Surgical retry without full reconversion | ✅ | `FolioConverter.convert_diagrams()`; `TestConvertDiagramsOrchestration::test_retry_failed_targets_provider_failure_slide`. |

### 2. Better diagram cache / retry behavior
| Item | Status | Evidence |
|------|--------|----------|
| Reuse / persist successful diagram work | ✅ | `analyze_diagram_pages` persists `.analysis_cache_diagram_final.json` even on `force_miss`; non-targets untouched in the retry path. `TestCachePersistence`. |
| Detect `provider_failure` from sidecar metadata | ✅ | `discover_retry_candidates(mode="failed")`; `TestDiscoverRetryCandidates`. |
| Retry only failed / review-required notes | ✅ | `convert_diagrams` target resolution; `TestConvertDiagramsOrchestration`, `TestDiscoverRetryCandidates::test_review_required_mode`. |
| Refresh deck frontmatter review flags + registry | ✅ | `_refresh_deck_diagram_flags` (body-preserving); `TestRefreshDeckDiagramFlags`, `TestRecomputeDiagramReviewFlags`. |

### 3. Broader diagram support
| Item | Status | Evidence |
|------|--------|----------|
| `concept-map` + `process` first-class | ✅ | `_SUPPORTED_DIAGRAM_TYPES`; `TestSupportedDiagramTypes::{test_concept_map_supported,test_process_supported,test_first_class_type_set}`. |
| Separate "cannot render Mermaid" from "cannot extract structure" | ✅ | Rendering emits tables/inventory for any graph; only an empty graph abstains (`render_diagram_analyses`, `_build_note_body`). |
| Structured inventories (zones, lanes, stages, callouts, decisions, relationships, components) | ✅ (generic) | `_build_structured_inventory` + existing component/connection tables; `TestStructuredInventory`. |
| Bespoke schemas (process flow, stage-gate, timeline/gantt, operating-model/swimlane, nested capability map, matrix-with-callouts) | ⏸ Deferred | See **Deferred** — minimum-robust generic inventory implemented per the issue's own guidance. |

### 4. Provider-failure resilience
| Item | Status | Evidence |
|------|--------|----------|
| Robust retry/backoff for Pass A | ✅ (pre-existing) | `llm/runtime.py execute_with_retry` (exponential backoff + jitter + `Retry-After`). |
| Reduced image-payload / lower-detail fallback | ✅ | `_reduced_pass_a_images` + payload-reduction retry; `TestPayloadReductionFallback`. |
| Smaller semantic-inventory-only extraction | ⏸ Deferred | See **Deferred**. |
| End-of-run retry-candidate summary | ✅ | `format_retry_candidate_summary` + CLI echo; `TestCollectAndFormatCandidates`, `TestConvertCliDiagramFlags::test_normal_convert_prints_retry_candidate_summary`. |

---

## Behavior preservation

Full-conversion behavior is unchanged unless a new flag is used: `convert()` only
gains an additive end-of-run summary (output-only). The 2125-test suite passes,
including all pre-existing diagram/converter integration tests.

---

## Deferred (documented split, per completion requirements)

- **Bespoke consulting-visual schema library** (six dedicated schemas + per-type
  prompts/renderers). The issue's implementation guidance explicitly scopes this
  pass to "the minimum robust schema and rendering behavior needed to stop
  treating `concept-map` and `process` as unsupported." The generic
  `DiagramGraph`-derived structured inventory satisfies "emit structured
  inventories … even when Mermaid is unavailable." The bespoke library is a
  large multi-PR effort tracked as a follow-up.
- **Semantic-inventory-only LLM fallback** (text-inventory-driven extraction when
  image requests repeatedly fail). The payload-reduction retry, first-class type
  broadening, and surgical retry already restore recoverability; a text-only
  extraction mode is a further enhancement, deferred to a follow-up.

## Residual risk

- The deck-level frontmatter refresh recomputes only the `diagram_*_slide_{n}`
  flags (which depend solely on diagram analyses); other review flags and
  `review_status` are recomputed conservatively (`flagged` whenever any flag
  remains). A full `folio convert` (now cache-fast) recomputes the complete
  review state if desired.
