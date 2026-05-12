---
deliverable_id: folio-document-format-coverage-v1-1-1
phase: B.1
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Peer Review — folio-document-format-coverage-v1-1-1 Phase B.1

## Verdict

approve

## Basis for Review

Source files inspected directly in this session:

- `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`
- `docs/validation/strict_p3_rerun_2026_05_12/folio-document-format-coverage-v1-1-1_phase_a_spec.md`
- `frameworks/manifests/folio-document-format-coverage-v1-1-1.yaml`

No prior `folio_*_v1_*` artifacts were consulted; the pre-A triage (`pre_a_triage.md`, line 9) explicitly excludes them as lifecycle evidence, and this review honours that rule.

## Findings

### Stale Evidence Posture — Clean

`pre_a_triage.md` line 9 states: "prior `folio_*_v1_*` artifacts and the preserved dirty attempt are implementation history only; they are not lifecycle evidence for this rerun." The phase A spec echoes this directly in its opening scope sentence and in the Non-Goals block ("Do not count any old artifacts from the prior failed closeout as evidence"). The manifest carries no `review_rounds` or `self_review_caveats` entries that reference prior evidence. Stale reuse risk is nil.

### Acceptance Criteria — Adequately Specified

Three acceptance criteria appear in the phase A spec:

1. Accept `.docx` at the `folio convert` normalization gate.
2. Use document-oriented text extraction (MarkItDown path) rather than slide image extraction.
3. Emit a single evidence note with `source_type: document` and compatibility field `slide_count: 1`.

All three are concrete, binary-testable, and map unambiguously to work in `folio/converter.py`. The cardinality assertion in the manifest (`rg -n "source_type.*document|docx|slide_count" folio/converter.py tests/test_docx_conversion.py`) anchors them to the implementation files, and the phase C smoke check (`./.venv/bin/python -m pytest tests/test_docx_conversion.py -q`) closes the loop.

### Implementation Surface — Correct and Minimal

`folio/converter.py` and `tests/test_docx_conversion.py` are both present in `scope.allowed_paths`. The scope is narrower than the issue body's broader discussion (issue #56 also touches rendering), but the spec deliberately limits phase C to the conversion gate; downstream rendering changes are not needed for the stated acceptance criteria.

### Manifest Structural Compliance — Full

- `manifest_version: 1.6.0` ✓ (required by pre_a_triage.md)
- `lifecycle_receipt_inventory_path` present ✓
- Phase A `claude-opus: spec-author` ✓
- Phase B.1 `claude-sonnet: peer`, `codex: alignment`, `gemini: adversarial` ✓
- Phase D.5 all three families as `verifier` ✓
- Phase D.6 `claude-opus: final-approval` ✓
- `consolidation_mode: external` ✓
- `forbidden_paths` includes `.env` and variants ✓
- `forbidden_symbols` blocks credential leakage ✓
- Negative lifecycle control mandated in spec ("must fail with `review_pending` before receipts exist") ✓

### Minor Observation (Non-Blocking)

The cardinality assertion regex `source_type.*document|docx|slide_count` uses implicit OR precedence, so the middle branch `docx` will match any line containing that substring — including import comments, test function names, or docstrings. This means the assertion is a coarse existence check rather than a precise anchor. The implementation author should ensure the three acceptance-criteria strings (`source_type: document`, `slide_count`, `.docx` handling logic) appear as functional code, not only as string literals in comments or test names. This is not a blocker because the smoke-check test suite provides the authoritative correctness gate; the cardinality assertion is supplementary.

The spec does not document the rationale for choosing `slide_count: 1` as a fixed compatibility shim rather than omitting the field entirely for document-type sources. This could puzzle the implementation author. However, the AC is unambiguous — the value is specified — so no clarification is required before implementation proceeds.

## Summary

The spec and manifest together are adequate to drive phase C implementation of the `.docx` conversion slice without any risk of stale evidence reuse. The acceptance criteria are testable, the implementation surface is correctly bounded, and all strict-P3 structural requirements are present in the manifest.
