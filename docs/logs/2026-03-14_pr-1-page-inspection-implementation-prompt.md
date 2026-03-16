---
id: log_20260314_pr-1-page-inspection-implementation-prompt
type: log
status: active
event_type: decision
source: codex
branch: codex/grounding-reviewability
created: 2026-03-14
---

# PR 1 page inspection implementation prompt

## Context

PR 1 for the diagram extraction roadmap needs a decision-complete implementation
prompt for a developer agent. The current converter pipeline derives blank pages
from `ImageResult.is_blank`, which comes from a pixel-histogram heuristic in
`folio/pipeline/images.py`. That heuristic is currently authoritative for the
post-pass-1 `pending()` override, Pass 2 skip gating, and reviewability
`known_blank_slides`, which can destroy valid sparse-diagram analyses.

## Decision

Created the canonical implementation prompt at
`docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr1_page_inspection.md`.

The prompt instructs the developer to:

- add a new deterministic inspection stage over normalized PDFs
- introduce `PageProfile`, `BoundedText`, coordinate transforms, and Set-of-Mark
  viability measurement
- wrap all `pypdfium2` usage behind a thin adapter
- make inspection-derived blank classification authoritative in the converter
- preserve current LLM behavior and keep per-page DPI changes out of PR 1
- add generated PDF fixture tests for geometry, classification, adapter output,
  SoM viability, and the sparse-diagram regression

Created a local branch reference `codex/diagram-pr1-page-inspection` from the
current `codex/grounding-reviewability` tip without switching the dirty
workspace.

## Rationale

- The implementation prompt must reflect the current repo, not older planning
  text. The live test baseline is 556 tests, and the active destructive bug
  lives in `folio/converter.py`, not in the LLM analysis layer.
- PR 1 is a foundation PR, not a diagram-pipeline PR. The prompt therefore
  narrows scope to deterministic inspection, geometry correctness, and blank
  gating only.
- `pypdfium2` must be pinned and adapter-wrapped because the API surface is
  still beta and the rest of the pipeline should not depend on its internals.
- Programmatic PDF fixtures via `reportlab` and `pypdf` make rotation/CropBox
  geometry tests deterministic and reviewable in git.
- The original `<5 vector lines => blank` heuristic contradicts the sparse-
  diagram success criterion, so the prompt resolves that explicitly: any vector
  primitive or bounded text makes a page nonblank.

## Consequences

- The repo now contains a durable, executable PR 1 implementation prompt under
  `docs/prompts/`.
- Future developer-agent work on PR 1 can start without re-deriving the current
  converter bug path or the geometry/adapter design decisions.
- Ontos indexing now includes the new prompt document and this log entry.
