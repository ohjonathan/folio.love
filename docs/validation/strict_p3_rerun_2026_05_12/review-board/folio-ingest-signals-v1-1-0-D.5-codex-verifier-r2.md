---
deliverable_id: folio-ingest-signals-v1-1-0
phase: D.5
role: verifier
family: codex
status: completed
evidence_labels_used:
  - direct-run
---

# D.5 Codex Verifier R2: folio-ingest-signals-v1-1-0

## Verdict
approve

## Scope
This verifier pass reviewed the post-D.5 compatibility fix for `speaker_analytics_unavailable`. The intended behavior is that transcript-like sources still receive the unavailable-speaker-analytics flag when deterministic speaker analytics cannot be computed, while ordinary clean/free-form notes preserve their preexisting clean or degraded review state.

Reviewed files:
- `folio/ingest.py`
- `tests/test_speaker_analytics.py`
- `tests/test_ingest_integration.py`
- `docs/validation/strict_p3_rerun_2026_05_12/folio-ingest-signals-v1-1-0_D.3_canonical_verdict.md`
- `docs/validation/strict_p3_rerun_2026_05_12/folio-ingest-signals-v1-1-0_d4_fix_summary.md`

## Evidence
Ontos activation was attempted first. `ontos map` exited nonzero on preexisting duplicate validation document IDs and metadata warnings, and `python3 -m ontos map` was unavailable. I then loaded the existing `Ontos_Context_Map.md` Tier 1 and the two requested D.3/D.4 documents. `scripts/llm-dev doctor` passed.

Focused direct run:

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/test_speaker_analytics.py tests/test_ingest_integration.py -q -p no:cacheprovider
31 passed in 0.19s
```

Additional direct behavior probe:

```text
clean_freeform_md: should=False status=clean flags=[]
degraded_freeform_txt: should=False status=flagged flags=['analysis_unavailable']
timestamp_txt: should=True status=flagged flags=['speaker_analytics_unavailable']
transcript_vtt: should=True status=flagged flags=['speaker_analytics_unavailable']
```

The orchestrator also reported the full validation command `./.venv/bin/python -m pytest tests -q` as `2100 passed, 6 skipped`; I did not rerun the full suite in this verifier pass.

## Findings
`folio/ingest.py` now computes `mark_unavailable` through `_should_flag_speaker_analytics_unavailable(...)` before applying speaker analytics state. Transcript format extensions remain strict, so missing analytics on VTT/SRT-like inputs are flagged. For other supported source text, the guard only returns true when the normalized body looks transcript-like, using timestamp or `Speaker N:` line detection.

`_apply_speaker_analytics_state(...)` preserves existing status and flags whenever `speaker_stats` exists or `mark_unavailable` is false. This is the critical compatibility behavior: a normal free-form clean note remains clean, and a separately degraded free-form note keeps its existing degradation reason without accumulating `speaker_analytics_unavailable`.

The D.3 canonical verdict and D.4 fix summary match the implemented behavior, and the focused tests continue to pass. No request-changes items were found for the compatibility fix under review.
