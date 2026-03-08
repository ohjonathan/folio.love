# Managed macOS Workflow Guide

## Prerequisites

- **Terminal.app** (not iTerm2) — required for AppleScript `System Events` access
- **Microsoft PowerPoint** installed and launchable
- A dedicated PowerPoint session (no other presentations open)

## Automated PPTX Conversion (Tier 1)

```bash
# Convert all PPTX files in a directory
folio batch ./materials --client ClientA

# Monitor: the CLI reports per-file timing, outcome, and restart events
```

### Restart Behavior

Folio automatically restarts PowerPoint every 15 PPTX conversions to prevent
AppleScript fatigue accumulation. This is enabled by default with `--dedicated-session`.

If a conversion fails with error `-9074`, Folio will:
1. Quit and relaunch PowerPoint (5s cooldown)
2. Retry the failed file once
3. If the retry fails, record it as failed and continue

To disable restart automation (e.g., if PowerPoint has other work open):

```bash
folio batch ./materials --no-dedicated-session
```

## PDF Mitigation (NOT Tier 1)

For files that consistently fail automated conversion, manually export to PDF:

1. Open the file in PowerPoint
2. **File → Export → PDF** (select **slides only**, not notes pages)
3. Save into a separate directory (e.g., `./pdfs/`)
4. Run the mitigation batch:

```bash
folio batch ./pdfs --pattern "*.pdf" --client ClientA
```

> **Important**: Operator-exported PDFs do not count toward Tier 1 automated
> conversion gates. They provide usable analysis but lack the full provenance
> chain of automated extraction.

### Portrait PDF Warning

If Folio detects a portrait-oriented PDF (taller than wide), it will warn that
the file may be a notes-page export. Re-export as **slides only** for best results.

### Scanned PDF Warning

If extracted text density is very low (< 50 characters per page on average),
Folio will warn that the file may be a scanned document. Analysis accuracy
may be reduced for scanned content.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `-9074` errors | AppleScript fatigue | Restart PowerPoint, or use `--dedicated-session` (default) |
| Timeout on large files | File > 200 slides | Timeout auto-scales; for very large files, try manual PDF export |
| "Not permitted" from LO | MDM blocks LibreOffice | Folio auto-falls back to PowerPoint in auto mode |
| Portrait PDF warning | Notes-page export | Re-export: File → Export → PDF, slides only |
