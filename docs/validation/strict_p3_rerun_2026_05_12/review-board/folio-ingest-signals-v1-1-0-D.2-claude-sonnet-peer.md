---
deliverable_id: folio-ingest-signals-v1-1-0
phase: D.2
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Phase D.2 Implementation Review — folio-ingest-signals-v1-1-0 — claude-sonnet peer

## Verdict

approve

## Summary

All six Phase A acceptance criteria are satisfied by the Phase C implementation. The focused test suite (73 tests) passes cleanly under direct execution. No implementation blockers identified.

## Findings

No blocking implementation findings. Detailed criterion-by-criterion assessment follows.

### AC-1 — Action items with `element_type: action`, owner, and due metadata

- `InteractionFinding` carries `owner: Optional[str]` and `due: Optional[str]` fields (`folio/pipeline/interaction_analysis.py:183–184`).
- `_ALLOWED_ELEMENT_TYPES` includes `"action"` (`interaction_analysis.py:34`).
- `_coerce_findings()` extracts `owner` and `due` from the LLM payload for every finding bucket, including `action_items` (`interaction_analysis.py:598–599`).
- The LLM prompt schema explicitly requires `action_items` entries with `owner` and `due` keys (`interaction_analysis.py:111–122`).

### AC-2 — Action items counted in `grounding_summary`

- `InteractionAnalysisResult.all_findings()` concatenates `*self.action_items` with all other finding lists (`interaction_analysis.py:229–236`).
- `_apply_review_state()` iterates `result.all_findings()` to populate `grounding_summary` counters, so action items are counted (`interaction_analysis.py:641–664`).
- `test_action_items_are_coerced_validated_and_counted` directly asserts `grounding_summary["total_claims"] == 1` for a single action item and `review_status == "clean"` when it validates (`tests/test_interaction_actions.py:60–62`).

### AC-3 — Subtype-specific header rendering (Next Steps vs Action Items)

- `_action_header()` returns `"### Next Steps"` for `client_meeting`, `expert_interview`, and `partner_check_in`, and `"### Action Items"` for all other subtypes (`folio/output/interaction_markdown.py:192–195`).
- `assemble_interaction()` omits the header entirely when `action_items` is empty (`interaction_markdown.py:68–70`).
- Tests confirm: `"### Next Steps"` present for `expert_interview`, `"### Action Items"` absent; empty bucket produces neither header (`tests/test_interaction_actions.py:94–115`).

### AC-4 — Deterministic speaker analytics in frontmatter, markdown, and registry

- `generate_interaction()` emits `speakers`, `total_words`, `total_duration_seconds`, `speaker_count`, `balance_score`, `dominant_speaker`, and `speaker_summary` when `analysis_result.speaker_stats is not None` (`folio/output/frontmatter.py:317–325`).
- `assemble_interaction()` calls `_append_speaker_analytics()` to render a markdown table with per-speaker word/turn/time statistics (`folio/output/interaction_markdown.py:56–58`, `145–189`).
- `RegistryEntry` carries a `speaker_summary` field (`folio/tracking/registry.py:62`); `ingest_source()` stores `speaker_summary=analysis_result.speaker_stats.to_summary()` to the registry entry (`folio/ingest.py:333–336`).
- `test_speaker_stats_frontmatter_and_registry_summary` validates frontmatter and registry output end-to-end (`tests/test_speaker_analytics.py:74–118`).

### AC-5 — Speaker analytics independent of LLM; `speaker_analytics_unavailable` flag

- `compute_speaker_stats()` is called at `ingest.py:154–157`, before `analyze_interaction_text()` at `ingest.py:207–216`. The analytics path is therefore entirely LLM-independent.
- `_apply_speaker_analytics_state()` appends `"speaker_analytics_unavailable"` to `review_flags` and sets `review_status = "flagged"` when `speaker_stats is None` (`folio/ingest.py:384–393`).
- `compute_speaker_stats()` returns `None` when no valid timestamped speaker turns are found, covering free-form notes and malformed inputs (`folio/pipeline/speaker_analytics.py:128–131`).
- `test_missing_speaker_stats_sets_review_flag_without_llm_dependency` asserts the flag is set and `speaker_stats` remains `None` without any LLM call (`tests/test_speaker_analytics.py:140–147`).

### AC-6 — Speaker alias merging via confirmed person entity registry

- `_load_speaker_aliases()` builds a lowercased `{alias: canonical}` map from the entity registry, skipping any entity with `needs_confirmation=True` (`folio/ingest.py:359–381`).
- `compute_speaker_stats()` accepts `speaker_aliases` and applies `_canonical_speaker()` (case-insensitive lookup) before aggregating turns (`folio/pipeline/speaker_analytics.py:121–128`, `202–203`).
- `test_speaker_stats_merge_existing_entity_aliases` verifies that `J. Oh` and `Jonathan Oh` collapse to one canonical speaker with `turn_count == 2` and `total_words == 5` (`tests/test_speaker_analytics.py:121–137`).

## Test Assessment

The focused test surface is adequate for this slice:

- **`tests/test_interaction_actions.py`** (3 tests): covers action item coercion/validation/grounding counting, subtype-conditional `Next Steps` header rendering, and empty-bucket header suppression.
- **`tests/test_speaker_analytics.py`** (5 tests): covers bracket-format turn merging, timestamp-header stats computation, frontmatter/registry embedding, alias merging, and unavailable-flag behavior.
- **`tests/test_frontmatter.py`** (65+ tests): broad frontmatter regression coverage; `TestInteractionFrontmatter` confirms `grounding_summary`, `review_status`, `review_flags`, and interaction-specific field layout.

Direct execution result: **73 passed, 0 failed** in 0.15 s.

No coverage gaps identified for the Phase A/B.3 contract.
