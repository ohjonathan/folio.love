---
deliverable_id: folio-ingest-signals-v1-1-0
phase: D.2
role: alignment
family: codex
status: completed
evidence_labels_used:
  - direct-run
---

# Codex Alignment Review: folio-ingest-signals-v1-1-0

## Verdict
approve

## Scope Reviewed
Reviewed Phase C implementation against the Phase A acceptance criteria and the B.3 canonical decision for the ingest-signals slice. Files inspected: `folio/ingest.py`, `folio/pipeline/interaction_analysis.py`, `folio/pipeline/speaker_analytics.py`, `folio/output/frontmatter.py`, `folio/output/interaction_markdown.py`, `folio/tracking/registry.py`, and the focused tests named in the assignment.

## Evidence
Direct run completed successfully with the focused test selection:

`PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest -p no:cacheprovider tests/test_interaction_actions.py tests/test_speaker_analytics.py tests/test_frontmatter.py -q`

Result: 73 passed in 0.15s. The `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1` additions were used to honor the D.2 instruction not to edit repository files other than this artifact while running the same focused test set reported by the orchestrator.

## Alignment Findings
The action item path is aligned with Phase A/B.3. The interaction prompt schema includes `action_items` with `element_type: action`, `owner`, and `due`; `InteractionAnalysisResult` stores action items separately; `_coerce_findings()` preserves owner/due metadata; and `InteractionAnalysisResult.all_findings()` includes actions so `_apply_review_state()` counts them in `grounding_summary`. Markdown rendering emits subtype-specific action sections: client meetings, expert interviews, and partner check-ins render `### Next Steps`, while other subtypes render `### Action Items`.

The deterministic speaker analytics path is also aligned. `folio/ingest.py` computes speaker stats from normalized source text before LLM analysis, applies the stats or the `speaker_analytics_unavailable` review flag afterward, and writes a registry `speaker_summary` when stats exist. `folio/pipeline/speaker_analytics.py` provides deterministic parsing, per-speaker totals, talk-time estimates, balance scoring, dominant speaker selection, and alias canonicalization. Alias loading is correctly restricted to confirmed person entities by skipping entries with `needs_confirmation`.

Frontmatter and markdown exposure are present. Interaction frontmatter emits `speakers`, `total_words`, `total_duration_seconds`, `speaker_count`, `balance_score`, `dominant_speaker`, and `speaker_summary` when analytics are available, while unavailable analytics surface through `review_flags`. Markdown renders a speaker analytics table plus balance and longest-monologue summaries.

## Residual Notes
No implementation blockers were identified. One non-blocking edge to consider in a future hardening pass: the `action_items` bucket uses the same generic finding coercion as other buckets, so a malformed LLM payload with an action item carrying a non-action `element_type` would be preserved rather than normalized to `action`. The current prompt, schema, and tests cover the intended contract, and this does not block Phase D.2 approval.
