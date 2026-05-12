---
deliverable_id: folio-document-format-coverage-v1-1-1
phase: D.2
role: alignment
family: codex
status: completed
evidence_labels_used:
  - direct-run
---
# Codex Alignment Review: folio-document-format-coverage-v1-1-1

## Verdict
approve

## Review Scope

I reviewed the Phase C implementation against the Phase A acceptance criteria and the B.3 canonical verdict for the strict-P3 document-format slice. The controlling acceptance criteria require `.docx` conversion support, document text extraction instead of slide image extraction, and a single evidence note with full document text plus `source_type: document` and compatibility `slide_count: 1`.

## Alignment Evidence

- Phase A defines the required behavior in `docs/validation/strict_p3_rerun_2026_05_12/folio-document-format-coverage-v1-1-1_phase_a_spec.md:13`, including `.docx` acceptance, document text extraction, and compatibility `slide_count: 1`.
- B.3 authorizes Phase C with the same shape in `docs/validation/strict_p3_rerun_2026_05_12/folio-document-format-coverage-v1-1-1_B.3_canonical_verdict.md:20`, specifically requiring a document-oriented MarkItDown path and no old slide-image extraction path.
- `folio/converter.py:26` defines `.docx` as a document extension, and `folio/converter.py:160` routes document sources to `_convert_document` before the normalize/image extraction pipeline begins.
- `folio/converter.py:794` calls `text.extract_document_text(source_path)`, stores it as unit 1, computes version metadata with `slide_count=1`, and returns `ConversionResult(slide_count=1, renderer_used="document-text")` at `folio/converter.py:919`.
- `folio/converter.py:840` generates frontmatter with `source_type="document"`, while `folio/converter.py:893` upserts the registry row with `source_type="document"`.
- `folio/converter.py:1022` assembles the document output as one evidence note and writes the full extracted document text under `## Document Text`, while documenting `slide_count: 1 (compatibility unit)`.
- `folio/pipeline/text.py:164` implements the MarkItDown document extraction helper and returns one `SlideText` with `slide_num=1` and full extracted text.
- `tests/test_docx_conversion.py:31` patches `normalize.to_pdf` and `images.extract_with_metadata` to raise if the slide/image path runs; the conversion test passes only if the new document path is used.
- `tests/test_docx_conversion.py:50` asserts result compatibility metadata, full document text in output, absence of slide image markdown, frontmatter `source_type: document`, frontmatter `slide_count: 1`, skipped LLM metadata, and registry `source_type: document`.

## Direct-Run Evidence

Focused validation command run locally:

```text
./.venv/bin/python -m pytest tests/test_docx_conversion.py -q
```

Result:

```text
..                                                                       [100%]
2 passed in 0.07s
```

## Blockers

No implementation blockers found. The Phase C changes align with Phase A and B.3 for the reviewed slice: DOCX inputs are handled by a document-oriented MarkItDown path, the slide-image extraction path is skipped, output metadata uses `source_type: document`, and `slide_count: 1` is preserved as compatibility metadata.
