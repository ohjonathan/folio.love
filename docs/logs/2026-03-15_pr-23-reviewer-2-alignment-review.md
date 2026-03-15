---
id: log_20260315_pr-23-reviewer-2-alignment-review
type: log
status: active
event_type: decision
source: codex
branch: codex/diagram-pr5-rendering
created: 2026-03-15
---

# pr-23-reviewer-2-alignment-review

## Context

Alignment review for PR #23 on branch `codex/diagram-pr5-rendering` at
`3c6c52d`, compared against base `97f03b9`, with focus on proposal
compliance, PR 4 runtime alignment, backward compatibility, and scope
containment.

## Goal

Verify that deterministic diagram rendering is derived only from the live
`DiagramGraph` contract, stays out of frontmatter/standalone-note scope,
preserves consulting-slide behavior, and keeps the existing suite green.

## Decision

Request changes.

## Rationale

- Ran Ontos activation and reviewed:
  - `docs/proposals/diagram-extraction-proposal.md`
  - `docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr4_extraction.md`
  - `docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr5_rendering.md`
  - `docs/logs/2026-03-15_pr-21-reviewer-2-alignment-review-rerun.md`
- Inspected the base-to-HEAD diff and confirmed scope is limited to:
  - `folio/converter.py`
  - `folio/output/diagram_rendering.py`
  - `folio/pipeline/analysis.py`
  - `tests/mermaid/package.json`
  - `tests/mermaid/validate.mjs`
  - `tests/test_diagram_rendering.py`
- Ran validation:
  - `.venv/bin/python -m pytest tests/test_diagram_rendering.py -q`
    -> `3 failed, 90 passed`
  - `.venv/bin/python -m pytest tests/test_diagram_analysis.py tests/test_converter_integration.py tests/test_frontmatter.py tests/test_pipeline_integration.py -q`
    -> `187 passed`
  - `.venv/bin/python -m pytest tests -q`
    -> `3 failed, 984 passed, 3 skipped`
- Reproduced that the new Mermaid validator fails before syntax validation
  with `DOMPurify.addHook is not a function`, so the parser-backed validation
  requirement is not currently satisfied.
- Reproduced that an unrecognized edge direction such as `"mystery"` renders
  as forward (`-->`, `→`) instead of conservative unknown/none handling.
- Reproduced that a node label that sanitizes to empty, e.g. `"()"`, falls
  back to the node ID in Mermaid with no uncertainty and no `review_required`
  flag, which diverges from the omit-and-flag contract.

## Key Decisions

- Treated proposal/runtime alignment as the primary merge gate, not unit-test
  volume alone.
- Counted the broken parser-backed Mermaid validation as a blocking issue
  because full-suite green and real-parser validation are explicit PR 5
  requirements.
- Counted the sanitization and unknown-direction behaviors as material
  proposal drift because they can misrepresent graph data without review
  signaling.

## Alternatives Considered

- Approve because the consulting-slide and integration slices remain green.
  Rejected because the full suite is red and two renderer behaviors diverge
  from the approved contract.
- Downgrade the sanitization drift to test-only disagreement. Rejected because
  the runtime behavior itself suppresses omit-and-flag review signaling.
- Treat the Mermaid failures as generated-syntax failures. Rejected after
  direct validator repro showed the helper crashes before parsing input.

## Consequences

- Merge should stay blocked until the parser-backed validation path is made
  functional and the renderer is brought back into alignment on
  sanitization/unknown-direction handling.
- The rest of the scope is contained correctly: no new LLM calls, no
  frontmatter or standalone-note changes, and consulting-slide coverage
  remains green in the targeted compatibility slices.

## Impacts

- Prevents PR 5 from landing with a red suite in environments that install the
  test-only Mermaid dependency.
- Prevents silently unsafe labels from rendering as internal node IDs without
  review flags.
- Prevents unexpected direction values from being presented as forward flow,
  which would overstate certainty relative to the extracted graph.
