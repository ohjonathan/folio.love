---
deliverable_id: folio-document-format-coverage-v1-1-1
phase: D.2
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Phase D.2 Peer Review: folio-document-format-coverage-v1-1-1

## Verdict

approve

## Summary

The Phase C implementation satisfies all Phase A acceptance criteria and the B.3 canonical scope. No blockers found.

## Evidence

Focused test command executed directly:

```
./.venv/bin/python -m pytest tests/test_docx_conversion.py -q
```

Result: **2 passed in 0.07s** (exit 0). Evidence label: `direct-run`.

## Spec Traceability

| Criterion (Phase A) | Implementation | Test Coverage |
|---|---|---|
| Accept `.docx` in `folio convert` | `DOCUMENT_EXTENSIONS = frozenset({".docx"})` at `converter.py:27`; routing guard at `converter.py:160-172` dispatches to `_convert_document` | `test_detect_source_type_docx_is_document`, `test_docx_conversion_uses_document_path_and_skips_slide_images` |
| Document text extraction, not slide image extraction | `_convert_document` calls `text.extract_document_text(source_path)` (`converter.py:794`); never calls `normalize.to_pdf` or `images.extract_with_metadata` | Test patches both image-path functions with `AssertionError` side effects and asserts no `![Slide 1]` image reference in output |
| Single evidence note, `source_type: document`, `slide_count: 1` | `frontmatter.generate(..., source_type="document", ...)` at `converter.py:845`; `slide_count=1` in `ConversionResult` at `converter.py:921`; evidence note in `_assemble_document_markdown` explicitly writes `- source_type: document` and `- slide_count: 1 (compatibility unit)` | `fm["source_type"] == "document"`, `fm["slide_count"] == 1`, registry `source_type == "document"` all asserted |

## B.3 Canonical Scope Alignment

The B.3 verdict required: DOCX conversion routing via a document-oriented MarkItDown path, skipping slide image extraction, emitting a single evidence note with full document text, `source_type: document`, and `slide_count: 1` for compatibility. All five requirements are met:

- **Routing**: `convert()` dispatches on `DOCUMENT_EXTENSIONS` before entering the PPTX/PDF image pipeline (`converter.py:160`).
- **MarkItDown path**: `text.extract_document_text` at `pipeline/text.py:164` uses `MarkItDown` directly and returns a `SlideText(slide_num=1, full_text=raw_text, ...)`.
- **No slide images**: The slide-image pipeline (`normalize`, `images`, `analysis.analyze_slides`) is entirely absent from `_convert_document`. LLM status is recorded as `"skipped"` with reason `"document_text_extraction"` (`converter.py:835`).
- **source_type: document**: Set in both frontmatter (`converter.py:845`) and registry entry (`converter.py:903`). `_detect_source_type` returns `"document"` for `.docx` (`converter.py:1015`).
- **slide_count: 1**: `ConversionResult.slide_count=1` (`converter.py:921`); `compute_version` receives `slide_count=1` (`converter.py:801`); evidence note in output markdown labels it as a compatibility unit.

## Manifest Cardinality Assertion

The manifest gate `G-cardinality-1` requires:

```
rg -n "source_type.*document|docx|slide_count" folio/converter.py tests/test_docx_conversion.py
```

All three patterns resolve: `docx` appears in `DOCUMENT_EXTENSIONS` (`converter.py:27`) and throughout `tests/test_docx_conversion.py`; `source_type.*document` appears at `converter.py:845,903,1015`; `slide_count` appears at `converter.py:801,921`.

## Additional Observations

- `cache_stats=None` is correctly returned for document conversions (no LLM pass, no cache to report). The test asserts this.
- `renderer_used="document-text"` is a clean sentinel distinguishing this path from all PPTX/PDF renderers.
- ID stability logic (`existing_fm.get("id")`) is present in `_convert_document` mirroring the main `convert()` path — no drift risk on reconversion.
- Registry upsert uses `try/except ValueError` to silently skip when the output is outside `library_root`, consistent with the main path pattern.
- No scope violations: only `folio/converter.py` and `tests/test_docx_conversion.py` implement the slice changes. `folio/pipeline/text.py` adds `extract_document_text` within the allowed surface implied by the implementation scope.
