---
deliverable_id: folio-ingest-signals-v1-1-0
phase: B.1
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# B.1 Peer Review — folio-ingest-signals-v1-1-0

## Verdict

approve

## Assessment

### Evidence hygiene

The Phase A spec (`docs/validation/strict_p3_rerun_2026_05_12/folio-ingest-signals-v1-1-0_phase_a_spec.md`) explicitly states: _"prior `folio_*_v1_*` artifacts are not lifecycle evidence."_ The manifest (`frameworks/manifests/folio-ingest-signals-v1-1-0.yaml`) anchors its `pre_a.artifact_path` exclusively to `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`, which was regenerated from live GitHub issue bodies on 2026-05-12. No stale evidence is pulled forward. The strict-P3 rerun evidence boundary is clean.

### Spec adequacy

**Scope authority is correctly traced.** The spec cites the triage document as scope authority; the triage document in turn records live issue state for #70 and #71 and explicitly excludes the prior dirty attempt as implementation history only.

**Acceptance criteria are testable.** All three criteria map unambiguously to verifiable output states:
- `action_items` bucket with `element_type: action`, `owner`, `due` fields — verifiable from rendered markdown and registry JSON.
- Subtype-conditional render header (`Next Steps` vs `Action Items`) — verifiable from rendered section name given a known subtype input.
- Deterministic speaker analytics in frontmatter, markdown section, and registry `speaker_summary` — verifiable without LLM involvement.

**Implementation surface is sufficient.** The eight listed files cover the analysis dataclass changes (`interaction_analysis.py`), the new deterministic module (`speaker_analytics.py`), both output renderers (`frontmatter.py`, `interaction_markdown.py`), registry surface (`registry.py`), and the three test files cited in the smoke check command.

**Validation steps are concrete and executable.** The spec names a specific pytest invocation, the `scripts/llm-dev verify` and `verify-lifecycle` commands, and the negative-control requirement that `verify-lifecycle` must fail before receipts exist. These are sufficient to gate phases C and D.

### Manifest consistency

The manifest is consistent with the spec on all load-bearing fields:
- `manifest_version: 1.6.0` and `lifecycle_receipt_inventory_path` present as required.
- `model_assignments` for B.1 are `claude-sonnet: peer`, `codex: alignment`, `gemini: adversarial` — matching the triage document's strict-P3 dispatch requirements.
- Smoke checks and `gate_prerequisites` reference the same pytest command as the spec.
- `allowed_path_patterns` cover the `review-board/folio-ingest-signals-v1-1-0-*.md` glob, so B.1 artifacts land in a permitted path.
- `forbidden_paths` include `.env` and `tests/validation/.env`; `forbidden_symbols` block API key literals.
- `G-cardinality-1` asserts `test -f folio/pipeline/speaker_analytics.py && rg -n "action_items|speaker_summary" folio tests`, which will catch a missing module or missing contract symbols before D.6.

### Minor observation (non-blocking)

Issue #70 calls out a specific provenance/grounding concern: _"Provenance / grounding (`folio/pipeline/provenance_analysis.py`) — extend the validation walk to cover `action_items`."_ This file does not appear in the spec's Implementation Surface list. The omission is not a blocker — the acceptance criteria do not require grounding validation of action items, and the cardinality assertion will catch missing `action_items` references in the test corpus regardless. However, the C-phase implementer should consult the issue body directly to decide whether to extend the provenance walk. The spec author may wish to add a single-line note for clarity in a future revision; it is not required for the slice to proceed.

### Conclusion

The spec and manifest are internally consistent, evidence-clean, and sufficient to drive Phase C implementation without ambiguity on the two primary deliverables (action_items schema and speaker analytics). No blockers identified.
