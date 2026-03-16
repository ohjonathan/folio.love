---
id: log_20260302_source-grounding-multi-pass-extraction-pipeline
type: log
status: active
event_type: grounding-multipass-genesis
source: cli
branch: folio.love_genesis
created: 2026-03-02
---

# source grounding & multi-pass extraction pipeline

## Summary

Implemented source grounding and multi-pass extraction for Folio's LLM analysis pipeline. Restructured flat root-level Python files into proper `folio/` package hierarchy. Every LLM claim now cites exact slide text with confidence levels and validation. Optional selective second pass on high-density slides.

## Goal

Add evidence-backed analysis to Folio conversions so every claim is traceable to source slide text.

## Key Decisions

- Package restructure as prerequisite (imports already assumed nested structure)
- Evidence validation uses substring match + 80% word overlap fallback (no embedding-based matching)
- Density scoring formula: evidence count * 0.3 + word count threshold + framework bonus + slide type bonus + comma count
- Default density threshold 2.0 (configurable via folio.yaml)
- Pass 2 evidence merges into Pass 1 results with deduplication at 85% word overlap

## Changes Made

- Moved 13 root files → `folio/{pipeline,tracking,output}/` subpackages
- `SlideText` dataclass with element detection (title/body/note)
- Grounded `ANALYSIS_PROMPT` requesting cited evidence per claim
- Evidence parsing state machine + validation against extracted text
- Density scoring + `analyze_slides_deep()` for selective second pass
- `--passes` CLI option, `default_passes`/`density_threshold` config fields
- Evidence rendering in markdown + `grounding_summary` in frontmatter
- 49 tests (unit + mocked integration)

## Alternatives Considered

- Character-level offset indexing (rejected: slide-level + quotes sufficient)
- Embedding-based dedup (rejected: word overlap matching fine for scope)
- Async/parallel API calls (rejected: keep simple for v1)

## Testing

49 tests passing: `.venv/bin/python -m pytest tests/ -v`