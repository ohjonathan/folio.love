# Issue #76 — Session Log

**Session date:** 2026-06-04
**Branch:** `feat/issue-76-diagram-retry-extraction`
**Companion docs:** [Validation Report](issue_76_validation_report.md) ·
[Chat Log / Exception Summary](issue_76_chat_log.md) · [Prompt](issue_76_prompt.md)

---

## Phase 1 — Understand

1. Traced the diagram pipeline: `converter.convert()` →
   `diagram_extraction.analyze_diagram_pages()` (Pass A/B/C) →
   `diagram_rendering.render_diagram_analyses()` → `diagram_notes.emit_diagram_notes()`.
2. Found the root causes:
   - Only `{architecture, data-flow}` were allowlisted (`_SUPPORTED_DIAGRAM_TYPES`);
     all other types (`concept-map`, `process`, swimlane, …) abstain at the
     allowlist gate *before* a graph is attached — and abstained slides never
     reach the cache store, so consulting decks cached almost nothing.
   - Provider failure (`pass_a_parse_outcome: provider_failure`) gives up
     immediately; the public CLI had no surgical retry.
3. Confirmed reusable machinery: `discover_frozen_notes` (sidecar read +
   `_hydrate_graph_from_tables`), `assess_review_state` diagram-flag naming
   (`diagram_abstained_slide_{n}`, `diagram_review_required_slide_{n}`,
   `diagram_open_questions_slide_{n}` — depend only on diagram analyses), and the
   `review_status = flagged if flags else clean` rule.

## Phase 2 — Implement

1. **Diagram-type breadth:** added `concept-map`/`process` to
   `_SUPPORTED_DIAGRAM_TYPES`; added `_build_structured_inventory` to the note body.
2. **Candidate discovery + summary:** `discover_retry_candidates` (sidecar),
   `collect_diagram_retry_candidates` (in-memory), `format_retry_candidate_summary`.
3. **Surgical path:** `FolioConverter.convert_diagrams()` (deterministic prep →
   target resolution → `analyze_diagram_pages(force_miss=True)` → render → emit
   target sidecars → `_refresh_deck_diagram_flags` body-preserving frontmatter +
   registry update).
4. **CLI:** `--slides`, `--diagrams-only`, `--retry-failed-diagrams`,
   `--retry-review-required-diagrams` + dispatch + `_echo_retry_candidates`.
5. **Resilience:** `_reduced_pass_a_images` + a bounded payload-reduction retry on
   provider failure; end-of-run summary wired into `convert()` and the retry path.

## Phase 3 — Validate

1. New `tests/test_diagram_retry.py` — 23 tests (discovery, summary, flag
   recompute, inventory, payload reduction, cache persistence, `convert_diagrams`
   orchestration, CLI dispatch).
2. Updated `tests/test_diagram_extraction.py::TestSupportedDiagramTypes` to assert
   the first-class set.
3. Full suite: **2125 passed, 6 skipped**.

## Commands

```bash
.venv/bin/python -m pytest tests/test_diagram_retry.py -q                  # 23 passed
.venv/bin/python -m pytest tests/test_diagram_extraction.py tests/test_diagram_notes.py \
    tests/test_diagram_rendering.py tests/test_converter_integration.py -q  # green
.venv/bin/python -m pytest tests/ -q                                       # 2125 passed, 6 skipped
```
