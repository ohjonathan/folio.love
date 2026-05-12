---
id: folio-ingest-signals-v1-1-0-D.5-claude-sonnet-verifier-r2
deliverable_id: folio-ingest-signals-v1-1-0
phase: D.5
role: verifier
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Phase D.5 Verifier Review (claude-sonnet, r2): folio-ingest-signals-v1-1-0

## Verdict

approve

## Summary

The post-D.5 compatibility fix is correctly implemented. `speaker_analytics_unavailable` is gated by a `mark_unavailable` boolean computed from input type, so ordinary clean/free-form notes are never flagged solely because they lack speaker timing data. Transcript-like inputs (`.vtt`, `.srt`, or text with embedded timestamp/speaker patterns) retain the flag when analytics are unavailable. All 2100 tests pass.

## Evidence

### Direct code inspection

**`_should_flag_speaker_analytics_unavailable`** (`folio/ingest.py:405-417`):

```python
def _should_flag_speaker_analytics_unavailable(
    normalized_source_body: str,
    *,
    source_extension: str,
) -> bool:
    if source_extension in TRANSCRIPT_FORMAT_EXTENSIONS:
        return True
    return bool(
        re.search(
            r"(?m)^(?:\[?\d{1,2}:\d{2}(?::\d{2})?|Speaker\s+\d+\s*:)",
            normalized_source_body,
        )
    )
```

- `.vtt` and `.srt` inputs → `True` unconditionally.
- `.txt`/`.md` inputs with embedded timestamp lines or `Speaker N:` headers → `True`.
- Ordinary prose notes (`.txt`/`.md` without timestamp patterns) → `False`.

**`_apply_speaker_analytics_state`** (`folio/ingest.py:391-402`):

```python
def _apply_speaker_analytics_state(
    analysis_result: InteractionAnalysisResult,
    speaker_stats: SpeakerStats | None,
    *,
    mark_unavailable: bool = True,
) -> None:
    analysis_result.speaker_stats = speaker_stats
    if speaker_stats is not None or not mark_unavailable:
        return
    if "speaker_analytics_unavailable" not in analysis_result.review_flags:
        analysis_result.review_flags.append("speaker_analytics_unavailable")
    analysis_result.review_status = "flagged"
```

The early return on `not mark_unavailable` is the critical guard: when `mark_unavailable=False`, the function sets `speaker_stats` and exits, preserving whatever `review_status` and `review_flags` the LLM analysis produced.

**Call site** (`folio/ingest.py:221-228`):

```python
_apply_speaker_analytics_state(
    analysis_result,
    speaker_stats,
    mark_unavailable=_should_flag_speaker_analytics_unavailable(
        normalized_source_body,
        source_extension=source_extension,
    ),
)
```

The two functions are correctly wired: `mark_unavailable` is derived from the input's extension and content, not hardcoded.

### Test coverage

**`tests/test_speaker_analytics.py:140-147`** — `test_missing_speaker_stats_sets_review_flag_without_llm_dependency`:
Exercises `_apply_speaker_analytics_state(result, None)` with the default `mark_unavailable=True`, confirming the flag path works without LLM involvement. Asserts `review_status == "flagged"` and `review_flags == ["speaker_analytics_unavailable"]`.

**`tests/test_ingest_integration.py` — `test_ingest_provider_failure_writes_degraded_note`** (line 1041):
Uses `client_meeting.txt`, a free-form notes fixture. LLM raises `EndpointNotAllowedError`. The test asserts `review_flags == ["analysis_unavailable"]`, confirming that ordinary notes do **not** accumulate `speaker_analytics_unavailable` on top of the degraded LLM status. This is the compatibility invariant the fix preserves.

**`tests/test_ingest_integration.py` — `test_ingest_writes_interaction_note_and_registry`** (line 149):
End-to-end clean ingest of `expert_interview.md`. Asserts `review_status == "clean"` and `review_flags == []`, confirming neither path adds spurious flags when analytics succeed or the input type does not require them.

### Test suite

Orchestrator-reported result: **2100 passed, 6 skipped**. No regressions introduced by the compatibility fix.

## Observations

- There is no dedicated unit test for `_should_flag_speaker_analytics_unavailable` covering each branch independently, and no unit test for the `mark_unavailable=False` fast-exit path of `_apply_speaker_analytics_state`. Coverage of these paths is currently indirect, via integration tests. This is a minor hardening gap and is not a release stopper; the integration tests provide sufficient confidence.
- The D.3 canonical verdict already approved this design. The D.4 fix summary explicitly states the intent to preserve clean/free-form note behavior. The implementation matches that stated intent precisely.
- The regex `r"(?m)^(?:\[?\d{1,2}:\d{2}(?::\d{2})?|Speaker\s+\d+\s*:)"` correctly identifies transcript-like patterns in `.txt`/`.md` inputs, including normalized VTT/SRT cue lines and `HH:MM:SS Speaker` header lines. No false-positive risk for ordinary prose notes was identified.

## Conclusion

The compatibility fix is sound. `speaker_analytics_unavailable` is applied only when the input is either a structured transcript format (`.vtt`, `.srt`) or contains embedded timing/speaker cues in freetext, and when speaker analytics cannot be computed from that expected-transcript input. Ordinary clean or degraded notes are unaffected. The fix satisfies the D.4 intent and all tests pass.
