---
id: log_20260510_folio-love-vtt-srt-transcript-ingest
type: log
status: active
event_type: feature
source: codex
branch: codex/folio-love-vtt-srt-transcript-ingest
created: 2026-05-10
---

# folio-love-vtt-srt-transcript-ingest

## Summary

Implemented issue #69: transcript-native `.vtt` and `.srt` ingest for
`folio ingest`, preserving the existing interaction ingestion architecture and
raw-source provenance.

## Goal

Allow Folio to ingest raw meeting-tool transcript exports directly, without
requiring users to manually convert VTT/SRT files into intermediate Markdown or
plain-text transcript notes.

## Implementation

- Added a pure-stdlib caption normalization layer for `.vtt` and `.srt`.
- Wired `.vtt` and `.srt` into `folio ingest` alongside existing `.txt` and
  `.md` support.
- Kept `source_transcript` and `source_hash` pointed at the original raw
  transcript artifact.
- Updated `folio scan` so source roots discover `.vtt` and `.srt` transcript
  files.
- Added representative fixtures and focused parser, CLI, scan, and ingest
  integration coverage.

## Key Decisions

- Normalize VTT/SRT into deterministic transcript-like text before the existing
  analysis, entity resolution, versioning, frontmatter, and markdown assembly
  path.
- Preserve one line per cue or speaker utterance, with timestamps rendered as
  `[HH:MM:SS.mmm - HH:MM:SS.mmm]`.
- Strip transport markup such as cue numbers, headers, cue settings, VTT
  control blocks, and caption tags while preserving speaker labels where
  present.
- Defer extensionless plaintext sniffing and `--format` overrides; issue #69
  names those as nice-to-have rather than acceptance criteria.

## Alternatives Considered

- Rewriting interaction ingestion around a richer transcript object model was
  rejected as too broad for this slice.
- Feeding raw VTT/SRT text directly into the LLM was rejected because cue
  numbering, timestamps, and transport markup would reduce reviewability.
- Adding a dependency on a subtitle parsing package was rejected because the
  required subset is small and should remain testable without heavy external
  tooling.

## Impacts

- `folio ingest meeting.vtt --type internal_sync --date ...` now succeeds.
- `folio ingest meeting.srt --type internal_sync --date ...` now succeeds.
- Generated notes continue to use the existing interaction frontmatter schema,
  registry shape, versioning behavior, review fields, and raw transcript
  callout.
- README and CLI help now explicitly mention supported transcript formats.

## Testing

- `.venv/bin/python -m pytest tests/test_transcript_formats.py tests/test_interaction_analysis.py tests/test_ingest_integration.py tests/test_cli_ingest.py tests/test_cli_tier2.py -q`
  - Result: 97 passed before the final parser hardening tweak.
- `.venv/bin/python -m pytest tests/test_transcript_formats.py tests/test_ingest_integration.py tests/test_cli_ingest.py tests/test_cli_tier2.py -q`
  - Result: 77 passed after the final parser hardening tweak.
- `.venv/bin/python -m pytest tests -q`
  - Result: 2071 passed, 6 skipped, 5 warnings.

## Documentation

- Updated `README.md` ingest usage examples and architecture notes for
  `.txt`, `.md`, `.vtt`, and `.srt`.
