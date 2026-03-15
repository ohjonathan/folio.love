---
id: log_20260314_fr700-reviewability-integration
type: log
status: active
event_type: fr700-reviewability-integration
source: cli
branch: codex/grounding-reviewability
created: 2026-03-14
---

# FR-700: Reviewability Integration

## Goal

Integrate reviewability features into the Folio pipeline so documents carry
`review_status`, `review_flags`, and `extraction_confidence` through
config → analysis → frontmatter → converter → registry → CLI.

## Summary

Implemented a complete reviewability system that auto-flags documents based on
evidence quality. Documents with low-confidence evidence, unvalidated claims,
partial analysis failures, or high-density unanalyzed slides are flagged for
human review. The CLI blocks promotion of flagged documents and displays flag
counts in `folio status`.

## Changes Made

- `folio/config.py`: `review_confidence_threshold` (default 0.6)
- `folio/pipeline/analysis.py`: `_compute_extraction_confidence()`,
  `ReviewAssessment`, `assess_review_state()` with `known_blank_slides` param
- `folio/output/frontmatter.py`: review fields + always-emit grounding_summary
- `folio/converter.py`: passes blank_slides and review data through pipeline
- `folio/tracking/registry.py`: 4 new RegistryEntry fields, converter-authoritative docs
- `folio/cli.py`: flagged counts in status, promote blocking
- `docs/prompts/CLAUDE_CODE_PROMPT_grounding_multipass.md`: canonical spec

## Key Decisions

- **6 flag types**: `analysis_unavailable`, `partial_analysis_slide_<N>`,
  `low_confidence_slide_<N>`, `unvalidated_claim_slide_<N>`,
  `high_density_unanalyzed`, `confidence_below_threshold`
- **Known blank slides**: Converter passes blank-slide set explicitly rather than
  inferring blankness from text content (avoids visual-only false negatives)
- **Authoritative fields**: `review_status`/`review_flags` are frontmatter-authoritative;
  `extraction_confidence`/`grounding_summary` are converter-authoritative
- **grounding_summary always emitted**: Even with zero claims, to prevent registry drift

## Alternatives Considered

- Text-based blank detection (rejected — misflags visual-only slides)
- Reconciling grounding_summary from frontmatter (rejected — it's computed)
- Suppressing grounding_summary when zero claims (rejected — causes rebuild drift)

## Impacts

- 22 files changed, +1,989 / -52 lines
- 551 tests pass (including ~50 new reviewability tests)
- PR #18 with 4 review rounds (11 initial + 3 audit + 4 architect R1 + 3 architect R2)

## Testing

```
python3 -m pytest tests/ -v
551 passed, 3 skipped, 2 errors (pre-existing pptx module)
```