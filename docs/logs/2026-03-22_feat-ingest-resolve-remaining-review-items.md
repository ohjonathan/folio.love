---
id: log_20260322_feat-ingest-resolve-remaining-review-items
type: log
status: active
event_type: v0-5-0-ingest-review-fixes-and-merge-ready
source: cli
branch: feature/v0.5.0-ingest
created: 2026-03-22
---

# feat(ingest): resolve remaining review items

## Goal

Close the remaining PR #32 review items so the `folio ingest` branch is merge-ready,
clean the repo of unrelated generated files, and archive the session in Ontos.

## Summary

Finished the last deferred ingest review work after the main PR feedback was
already addressed. This pass resolved the remaining minor issues around
interaction confidence, prompt separation, and context-window heuristics, then
verified the full test suite and cleaned the branch for merge.

## Changes Made

- Added `system_prompt` to the shared `ProviderInput` contract and threaded it
  through Anthropic, OpenAI, and Google provider adapters so ingest can send
  instructions separately from untrusted transcript content.
- Split interaction-analysis prompts into system and user parts for both the
  single-pass and chunk-reduce paths.
- Changed interaction extraction confidence to `null` when an executed ingest
  yields zero findings, aligning with the approved spec's "no analysis => null"
  direction instead of emitting an arbitrary midpoint.
- Expanded `_context_window_for_model()` to recognize additional model families
  explicitly, including `gpt-4o`, `gpt-4.1`, and `o1`/`o3`.
- Added regression tests for system-prompt threading, zero-findings confidence,
  and explicit model-family context-window handling.
- Removed unrelated generated files from the working tree and restored the
  generated context map so the branch is clean apart from the intended feature
  work and this archive log.

## Key Decisions

- Kept the fix narrow and targeted to the last unresolved review items rather
  than reopening broader ingest design questions that had already been accepted
  on the PR.
- Implemented message-level prompt separation through the shared provider
  contract instead of an ingest-only workaround, so the abstraction now
  directly represents the distinction between instructions and untrusted user
  content.
- Treated zero-findings interaction output as lacking confidence-bearing
  evidence for a score, so `extraction_confidence` now becomes `null`.

## Alternatives Considered

- Leaving the single-string prompt intact and relying only on transcript
  delimiters for isolation. Rejected because the remaining review feedback
  explicitly called out message-level separation, and the shared provider layer
  could support it without destabilizing the existing pipelines.
- Keeping `0.5` as the confidence for zero findings. Rejected because it was an
  arbitrary midpoint not justified by the spec or downstream review semantics.
- Deferring explicit model-family heuristics entirely. Rejected because the
  change was low-risk and removed a documented gap before merge.

## Impacts

- `folio ingest` now records cleaner execution semantics and produces a more
  defensible confidence contract in sparse-result cases.
- The shared LLM provider abstraction is slightly more expressive and now
  supports instruction/data separation for future pipelines.
- The branch is in a clean, merge-ready state with no unrelated generated files
  left in the worktree.

## Testing

- `.venv/bin/python -m pytest tests/test_interaction_analysis.py tests/test_llm_providers.py tests/test_ingest_integration.py tests/test_cli_ingest.py tests/test_cli_tier2.py -v`
- `.venv/bin/python -m pytest tests/ -v`
