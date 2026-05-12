---
deliverable_id: folio-ingest-signals-v1-1-0
phase: B.1
role: alignment
family: codex
status: completed
evidence_labels_used:
  - direct-run
---
# B.1 Alignment Review: folio-ingest-signals-v1-1-0

## Verdict
request changes

## Evidence Reviewed

This review used only the strict-P3 Phase A inputs for the slice:

- `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`
- `docs/validation/strict_p3_rerun_2026_05_12/folio-ingest-signals-v1-1-0_phase_a_spec.md`
- `frameworks/manifests/folio-ingest-signals-v1-1-0.yaml`

No prior `folio_*_v1_*` lifecycle artifacts were used as evidence. The spec correctly names the pre-A triage as scope authority and states that prior failed-closeout artifacts are not lifecycle evidence. The manifest also routes pre-A authority to the same triage artifact and defines new strict-P3 review-board artifact patterns and receipt inventory, which is directionally adequate for avoiding stale evidence reuse.

## Blockers

1. `docs/validation/strict_p3_rerun_2026_05_12/folio-ingest-signals-v1-1-0_phase_a_spec.md` does not carry forward the full Issue #70 acceptance surface from `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`. The triage acceptance requires `element_type: action` to be accepted by the validator and counted in `grounding_summary`, and its suggested implementation calls out `folio/pipeline/provenance_analysis.py`. The Phase A spec only requires extraction and rendering of `action_items`; it does not require validator or grounding-summary coverage, and its implementation surface omits `folio/pipeline/provenance_analysis.py`. The manifest mirrors that omission in `scope.allowed_paths`, so the slice could pass while leaving action-item provenance/grounding incomplete.

2. `docs/validation/strict_p3_rerun_2026_05_12/folio-ingest-signals-v1-1-0_phase_a_spec.md` compresses Issue #71 too far. The triage requires graceful degradation for free-form notes with `review_flag: speaker_analytics_unavailable`, speaker-name alias merging through existing entity resolution, and speaker stats computed even when LLM analysis is unavailable. The spec's acceptance criterion only says to compute deterministic speaker analytics and expose them in frontmatter, markdown, and registry output. That is not enough to drive the negative and LLM-independent behavior that the issue explicitly treats as acceptance criteria.

3. `frameworks/manifests/folio-ingest-signals-v1-1-0.yaml` does not compensate for those omissions with gate prerequisites. Its cardinality assertion only checks that `folio/pipeline/speaker_analytics.py` exists and that `action_items|speaker_summary` appears somewhere under `folio` and `tests`. The focused pytest command may cover the missing behaviors if the tests are authored well, but the manifest does not require tests for action-item grounding counts, malformed/no-speaker inputs, alias merging, or LLM-unavailable speaker analytics. The manifest should encode these as explicit gate prerequisites or the Phase A spec should make them mandatory validation items.

## Required Changes

Update the Phase A spec and manifest so they preserve the Issue #70 and #71 acceptance criteria rather than only their headline features. At minimum, add validator/grounding-summary coverage for `action_items`, include any required implementation path such as `folio/pipeline/provenance_analysis.py`, and add explicit validation requirements for speaker-analytics graceful degradation, alias merging, and LLM-independent computation. Keep the current strict-P3 stale-evidence language and receipt flow; that part is aligned.
