---
id: log_20260315_pr-20-reviewer-3-adversarial-review
type: log
status: active
event_type: decision
source: codex
branch: codex/diagram-pr2-provider-dpi-tiles
created: 2026-03-15
---

# PR #20 Reviewer 3 adversarial review

## Context

Adversarial review of PR #20 scoped to the delta from `6a44b2d` to `HEAD`
(`2162ff8`) on branch `codex/diagram-pr2-provider-dpi-tiles`.

## Goal

Identify failure modes, regressions, and hidden assumptions in the cache-hit
provenance follow-up, with emphasis on:

- pass-1 cache hits
- pass-2 deep cache hits
- fallback summary flags on cached fallback provenance
- mixed-provider reporting when cache hits and misses are mixed

## Decision

Recommend blocking merge until the remaining pass-2 mixed hit/miss provenance
inconsistency is fixed.

## Key Decisions

- Reviewed only the delta in `folio/pipeline/analysis.py` and
  `tests/test_analysis_cache.py`, plus directly relevant reporting code in
  `folio/converter.py` and `folio/llm/types.py`.
- Verified the new targeted tests pass, then used custom local repros to probe
  mixed cache-hit/cache-miss and malformed-cache edge cases.

## Rationale

The new pass-1 and deep-cache hit bookkeeping populates
`StageLLMMetadata.per_slide_providers`, but the branch still leaves a reachable
pass-2 reporting mismatch when cached primary hits are mixed with fallback
misses. In that shape, `per_slide_providers` shows multiple providers while
`fallback_activated` remains false, so converter-level `_llm_metadata`
under-reports fallback usage.

The new helper also trusts cached `_provider` / `_model` values without
type-checking. Malformed cache provenance that previously had no effect can now
propagate into converter reporting and raise when provider tuples are hashed.

## Alternatives Considered

- Approve based on the targeted tests alone. Rejected because the added
  “frontmatter” test does not invoke `FolioConverter.convert()` or assert
  `_llm_metadata`.
- Treat malformed cached provenance as out of scope. Rejected because the cache
  path already contains other defensive validation and this change introduces a
  new crash surface by trusting on-disk metadata.

## Consequences

## Impacts

- Merge remains blocked pending a follow-up that makes pass-2 fallback summary
  flags consistent with `per_slide_providers` in mixed hit/miss runs.
- Additional regression coverage should target real converter/frontmatter output
  and malformed cached provenance handling.
