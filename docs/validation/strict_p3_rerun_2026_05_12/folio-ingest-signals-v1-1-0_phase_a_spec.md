---
id: folio-ingest-signals-v1-1-0-phase-a-spec
deliverable_id: folio-ingest-signals-v1-1-0
phase: A
role: spec-author
family: claude-opus
status: completed
---

# Phase A Spec: folio-ingest-signals-v1-1-0
## Scope
This strict-P3 rerun slice addresses issues #70 and #71. The scope authority is `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`; prior `folio_*_v1_*` artifacts are not lifecycle evidence.
## Acceptance Criteria
- Extract `action_items` with `element_type: action`, owner, and due metadata.
- Accept action items in the interaction validator and count them in `grounding_summary`.
- Render `Next Steps` or `Action Items` sections by interaction subtype.
- Compute deterministic speaker analytics and expose them in frontmatter, markdown, and registry summary output.
- Compute speaker analytics independently of LLM availability and set `speaker_analytics_unavailable` when free-form notes or malformed/no-speaker inputs cannot support speaker statistics.
- Merge speaker label aliases through the existing confirmed person entity registry so aliases like `J. Oh` and `Jonathan Oh` aggregate under one canonical speaker.
## Implementation Surface
- `folio/pipeline/interaction_analysis.py`
- `folio/ingest.py`
- `folio/pipeline/speaker_analytics.py`
- `folio/output/frontmatter.py`
- `folio/output/interaction_markdown.py`
- `folio/tracking/registry.py`
- `tests/test_interaction_actions.py`
- `tests/test_speaker_analytics.py`
- `tests/test_frontmatter.py`
`folio/pipeline/provenance_analysis.py` remains out of the write surface for this slice because issue #70's grounding requirement is enforced at ingest-time by `InteractionAnalysisResult.all_findings()` and `_apply_review_state()`, not by retroactive cross-note provenance.
## Required Validation
- `./.venv/bin/python -m pytest tests/test_interaction_actions.py tests/test_speaker_analytics.py tests/test_frontmatter.py -q`
- `scripts/llm-dev verify <manifest>`
- Negative control: `scripts/llm-dev verify-lifecycle <manifest>` must fail with `review_pending` before receipts exist.
- Dispatch B.1, D.2, and D.5 through `dispatch-family-review.sh --append-receipt` for `claude-sonnet`, `codex`, and `gemini`.
- D.6 final approval must include the exact strict-P3 receipt row and pass `verify-d6-gate.sh --strict-p3 --manifest <manifest> <final_approval>`.
## Non-Goals
- Do not count any old artifacts from the prior failed closeout as evidence.
- Do not commit API keys or local `.env` files.
