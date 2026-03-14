---
id: log_20260307_managed-laptop-pdf-fallback
type: log
status: active
event_type: managed-laptop-pdf-fallback
source: cli
branch: codex/pptx-libra-unblocker
created: 2026-03-07
concepts:
  - managed-laptop
  - pdf-fallback
  - libreoffice
  - powerpoint
  - applescript
  - validation
---

# managed laptop PowerPoint renderer fallback

## Summary

Added PowerPoint-via-AppleScript as a fallback PPTX-to-PDF renderer in `normalize.py` for managed laptops where LibreOffice is blocked by MDM. The renderer is auto-detected on macOS and configurable via `pptx_renderer` in `folio.yaml`.

## Goal

Unblock Week 5-6 validation of 50 real PPTX decks on locked-down corporate laptops without manual per-file PDF export.

## Key Decisions

- **Renderer fallback chain:** auto mode tries LibreOffice first (headless, CI-friendly), falls back to PowerPoint on macOS, then raises with manual PDF export instructions as last resort.
- **LO launch-blocked handling:** If LibreOffice is found on disk but fails at runtime (MDM block), auto mode catches the error and falls back to PowerPoint rather than giving up.
- **Named presentation targeting:** AppleScript save/close operations target the presentation by filename, not `active presentation`, to avoid races with other open documents.
- **AppleScript injection mitigation:** All paths are escaped (backslashes, double quotes, control characters, null bytes) before embedding in AppleScript string literals.
- **GUI tradeoff accepted:** PowerPoint cannot run headless on macOS — the GUI briefly appears during each conversion. Acceptable for interactive laptop use.

## Alternatives Considered

- Manual PDF export per file.
  Rejected because it requires 50 manual export steps and silently downgrades text extraction (PPTX-native via MarkItDown → pdfplumber fallback).
- `python-pptx` direct rendering.
  Rejected because it cannot handle SmartArt, charts, gradient fills, or custom fonts.
- Require LibreOffice on the managed laptop.
  Rejected because the target environment blocks it outright via MDM.

## Impacts

- Batch conversion of 50 decks now runs hands-free on managed Macs with PowerPoint.
- Text extraction fidelity is preserved (text comes from original PPTX via MarkItDown, not the PDF).
- Image extraction still uses PDF via Poppler (unchanged).
- No new dependencies — `osascript` is built into macOS.
- Linux/CI environments are unaffected (auto mode prefers LibreOffice there).

## Changes Made

- `folio/pipeline/normalize.py`: Added `_find_powerpoint()`, `_select_renderer()`, `_build_powerpoint_applescript()`, `_escape_applescript_string()`, `_convert_with_powerpoint()`. Extracted `_convert_with_libreoffice()`. Refactored `to_pdf()` as dispatcher with `renderer=` parameter.
- `folio/config.py`: Added `pptx_renderer: str = "auto"` to `ConversionConfig` with validation.
- `folio/converter.py`: Pass `renderer=` kwarg to `normalize.to_pdf()`.
- `tests/test_normalize.py`: 31 new tests across 8 test classes.
- `tests/test_config.py`: 3 new tests for `pptx_renderer` validation.
- `README.md`: Updated prerequisites, managed laptop section, pipeline diagram, config sample.

## Testing

- `.venv/bin/python -m pytest` — 334 passed in isolated virtualenv with `.[dev]`
- All tests fully mocked (no real PowerPoint/LibreOffice needed)
- Manual smoke test on managed Mac pending before 50-deck validation run
