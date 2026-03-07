---
id: log_20260307_managed-laptop-pdf-fallback
type: log
status: active
event_type: managed-laptop-pdf-fallback
source: cli
branch: main
created: 2026-03-07
concepts:
  - managed-laptop
  - pdf-fallback
  - libreoffice
  - validation
---

# managed laptop PDF fallback

## Summary

Added an explicit managed-laptop fallback for environments where LibreOffice is blocked. Folio now tells users to export decks to PDF from PowerPoint and run `folio convert <deck>.pdf`, and the README documents PDF-first validation as an accepted path for most Tier 1 hardening work.

## Goal

Unblock Week 5-6 validation and hardening on locked-down corporate laptops without treating local LibreOffice installation as a prerequisite for all testing.

## Key Decisions

- Treat PDF input as a first-class validation path because the product already supports `.pdf` directly.
- Add the fallback at the point of failure in `normalize.py` so users get an actionable next step instead of a dead-end dependency error.
- Document the tradeoff explicitly: PDF-first validation bypasses only PPTX/PPT normalization, not the rest of the pipeline.

## Alternatives Considered

- Add a PowerPoint-native export fallback in code.
  Rejected for now because it adds platform-specific automation complexity and was unnecessary to unblock validation immediately.
- Require LibreOffice on the managed laptop.
  Rejected because the target environment blocks it outright.

## Impacts

- Users can validate image extraction, PDF text extraction, analysis, version tracking, and source tracking on managed laptops.
- Direct PPTX/PPT normalization still needs to be validated on an unrestricted machine or a dedicated test environment.
- Supportability improves because the missing-LibreOffice path now tells the user what to do next.

## Changes Made

- Updated `folio/pipeline/normalize.py` to mention the PowerPoint-to-PDF fallback when LibreOffice is unavailable.
- Added a regression test covering the fallback message in `tests/test_normalize.py`.
- Updated `README.md` to clarify that LibreOffice is only required for PPTX/PPT inputs and that PDF-first validation is supported.

## Testing

- `python3 -m pytest tests/test_normalize.py` in an isolated temporary virtualenv with `.[dev]` installed
