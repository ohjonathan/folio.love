---
deliverable_id: folio-ingest-signals-v1-1-0
phase: D.5
role: verifier
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Phase D.5 Verification — folio-ingest-signals-v1-1-0

## Verdict

approve

## Test Execution

Focused test command `./.venv/bin/python -m pytest tests/test_interaction_actions.py tests/test_speaker_analytics.py tests/test_frontmatter.py -q` completed with **73 passed in 0.14s** — zero failures, zero errors.

## D.3 Canonical Verdict Review

The D.3 verdict (`folio-ingest-signals-v1-1-0_D.3_canonical_verdict.md`) carries a clean `approve`. No UNRESOLVED, BLOCKER, or REQUEST CHANGES markers are present. The only noted item was a future hardening edge for malformed action item element types, explicitly not treated as a release stop. The D.4 fix summary confirms all B.1/D.2 scope refinements were implemented: action items in validation summaries, alias-merged speaker analytics, and `speaker_analytics_unavailable` for unsupported inputs.

## Implementation Verification

**Action item extraction and rendering (`folio/pipeline/interaction_analysis.py`, `folio/output/interaction_markdown.py`):**

- `InteractionAnalysisResult.all_findings()` at line 229 includes `*self.action_items`, so action items count toward `grounding_summary.total_claims`. This directly satisfies the D.3 evidence item for ingest grounding coverage.
- `_coerce_findings()` at line 571 normalizes `element_type` from the LLM payload (including `"action"`) and coerces unknown types to `"statement"` — the malformed-type edge Codex noted is handled defensively.
- `_action_header()` at line 194 of `interaction_markdown.py` returns `"### Next Steps"` (not `"### Action Items"`), and the header is conditionally emitted at line 68–70 only when `analysis_result.action_items` is non-empty. The tests `test_action_items_render_as_next_steps_with_owner_and_due` and `test_empty_action_bucket_omits_action_header` confirm both branches.

**Deterministic speaker analytics (`folio/pipeline/speaker_analytics.py`, `folio/ingest.py`):**

- `compute_speaker_stats()` at line 108 accepts a `speaker_aliases` dict and applies alias canonicalization before aggregating turn stats (lines 121–128). The alias map keys are lowercased; the test `test_speaker_stats_merge_existing_entity_aliases` confirms two-turn alias merge into one `Jonathan Oh` speaker with the correct aggregate word count.
- `_apply_speaker_analytics_state()` at `folio/ingest.py:384` assigns `speaker_stats` to the result and, when `None`, appends `"speaker_analytics_unavailable"` to `review_flags` and sets `review_status = "flagged"`. This is called unconditionally after LLM analysis at line 221, including the `EndpointNotAllowedError` degraded path. The test `test_missing_speaker_stats_sets_review_flag_without_llm_dependency` exercises this path.
- `_load_speaker_aliases()` at line 359 reads confirmed person entities from the entity registry, skipping entries with `needs_confirmation=True`.

**Registry integration (`folio/tracking/registry.py`):**

- `RegistryEntry` carries a `speaker_summary` field. The test `test_speaker_stats_frontmatter_and_registry_summary` confirms that `stats.to_summary()` serializes `speaker_count`, `dominant_speaker`, and `shares` keys correctly.

**Frontmatter coverage (`folio/output/frontmatter.py`):**

- Speaker stats are emitted under `speakers` (per-speaker keyed dict) and `speaker_summary` (aggregate) in the interaction frontmatter. The test `test_speaker_stats_frontmatter_and_registry_summary` asserts `fm["speakers"]["alice_lee"]["word_count"] == 3`, `fm["total_words"] == 8`, and `fm["speaker_summary"]["dominant_speaker"] == "Bob Chen"`.

## Gate Prerequisite Assessment

| Gate ID | Status |
|---------|--------|
| G-test-1 | PASS — 73 tests passed |
| G-scope-1 | PASS — `docs/validation/strict_p3_rerun_2026_05_12/review-board` exists |
| G-cardinality-1 | PASS — `folio/pipeline/speaker_analytics.py` present; all contract anchors (`action_items`, `grounding_summary`, `speaker_summary`, `speaker_analytics_unavailable`, `speaker_aliases`) found in code and tests |
| G-blocker-1 | PASS — D.3 canonical verdict contains no unresolved blocker markers |
| G-branch-1 | PASS — active branch is `codex/github-issues-closeout-strict-p3-rerun` |

## Summary

D.3/D.4 are coherent: the D.3 verdict documents approval with a non-blocking future hardening note, and D.4 confirms implementation of all scoped items. Direct test execution (73/73 pass) and static code review confirm that action item extraction/rendering and deterministic speaker analytics are correctly implemented. No release issues found.
