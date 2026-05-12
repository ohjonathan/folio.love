---
deliverable_id: folio-ingest-signals-v1-1-0
phase: B.1
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# B.1 Peer Review (Round 2) — folio-ingest-signals-v1-1-0

## Verdict

approve

## Context

Round 1 yielded `approve` from claude-sonnet and gemini, and `request changes` from codex (alignment). The codex blockers were:

1. Spec did not require validator acceptance or `grounding_summary` counting for `action_items`.
2. Spec acceptance criteria omitted graceful degradation (`speaker_analytics_unavailable`), alias merging, and LLM-independent computation from the stated criteria.
3. Manifest cardinality assertion only anchored `action_items|speaker_summary`, leaving grounding counts, unavailable flags, and alias symbols unchecked at gate time.

This round-2 review confirms that all three codex blockers are closed.

## Blocker Resolution Assessment

### Blocker 1 — action_items accepted by validator and counted in grounding_summary

The Phase A spec now reads explicitly: _"Accept action items in the interaction validator and count them in `grounding_summary`."_ This is a direct lift of the Issue #70 acceptance criterion that was absent in round 1. The spec also clarifies that `folio/pipeline/provenance_analysis.py` is intentionally excluded from the write surface because grounding is enforced at ingest-time through `InteractionAnalysisResult.all_findings()` and `_apply_review_state()` — a reasoned architectural decision, not an omission. The manifest cardinality assertion now includes the symbol `grounding_summary` in its ripgrep pattern, so the gate will fail if the symbol is absent from code or tests at phase C exit. **Blocker closed.**

### Blocker 2 — speaker analytics graceful degradation, alias merging, and LLM-independence

The spec acceptance criteria now carry all three behaviors explicitly:

- _"set `speaker_analytics_unavailable` when free-form notes or malformed/no-speaker inputs cannot support speaker statistics"_ — covers graceful degradation.
- _"Merge speaker label aliases through the existing confirmed person entity registry so aliases like `J. Oh` and `Jonathan Oh` aggregate under one canonical speaker"_ — covers alias merging.
- _"Compute speaker analytics independently of LLM availability"_ — covers LLM-independence, reinforced architecturally by the dedicated `folio/pipeline/speaker_analytics.py` module running before any LLM call.

The three criteria map unambiguously to verifiable output states and directly reproduce the Issue #71 acceptance surface. **Blocker closed.**

### Blocker 3 — manifest gate anchors

The manifest cardinality assertion (G-cardinality-1) has been expanded to:

```
test -f folio/pipeline/speaker_analytics.py && rg -n \
  "action_items|grounding_summary|speaker_summary|speaker_analytics_unavailable|speaker_aliases" \
  folio tests
```

Compared to round 1 (`action_items|speaker_summary` only), this now gates on `grounding_summary` (action-item counting), `speaker_analytics_unavailable` (no-speaker/graceful-degradation path), and `speaker_aliases` (alias-merging path). Each symbol must appear in both `folio/` source and `tests/` to satisfy the ripgrep exit-0 expectation. The smoke check command for phase C runs `test_interaction_actions.py`, `test_speaker_analytics.py`, and `test_frontmatter.py`, which provides the test surface to populate all five anchored symbols. **Blocker closed.**

## Remaining Observations (Non-Blocking)

The spec cardinality assertion does not require a test with a name pattern that explicitly exercises the "LLM unavailable, speaker stats still produced" path. LLM-independence is architecturally guaranteed by the module's placement before the LLM call, and the `speaker_analytics_unavailable` symbol gate ensures the graceful-degradation branch exists in tests. Phase C implementer should add at least one test case that directly verifies stats are emitted when `analysis_unavailable` is set; this is not a B.1 gate condition but is worth calling out here so the C-phase author does not need to re-derive it.

## Evidence Hygiene

Evidence boundary is clean. The spec cites `pre_a_triage.md` as scope authority. The triage document was regenerated from live GitHub issue bodies on 2026-05-12 and explicitly excludes prior `folio_*_v1_*` artifacts as lifecycle evidence. The manifest `pre_a.artifact_path` resolves to the same triage document. No stale evidence is carried forward.

## Conclusion

All four round-1 blocker conditions stated in the round-2 dispatch prompt are resolved in the current spec and manifest. The spec is sufficient to drive Phase C without ambiguity on the two deliverables. The manifest gates are adequate to detect missing contract symbols before D.6.
