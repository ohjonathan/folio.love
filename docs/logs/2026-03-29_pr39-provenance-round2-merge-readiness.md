---
id: log_20260329_pr39-provenance-round2-merge-readiness
type: log
status: active
event_type: fix
source: codex
branch: codex/provenance-pr-d
created: 2026-03-29
---

# PR39 provenance round2 merge readiness

## Context

Goal: Close the remaining provenance PR review items on PR #39, publish the
implementation branch, and leave the change set in merge-ready shape.

Reviewed inputs:
- `docs/specs/folio_provenance_spec.md`
- `folio/provenance.py`
- `folio/enrich.py`
- `folio/cli.py`
- `folio/pipeline/provenance_analysis.py`
- PR #39 review consolidations, including the Round 2 approval comment

## Decision

Key decisions:
- Implement the remaining review findings directly in the existing PR instead
  of deferring correctness and CLI-alignment gaps to a follow-up branch.
- Keep `enrich_batch()` responsible for its own mutation lock so the library
  API is safe even when called outside the CLI wrapper.
- Remove the dead provenance-analysis helper path instead of leaving a
  second, divergent matching/budget contract in-tree.
- Preserve the already-approved public CLI surface while tightening the
  outputs to match the provenance spec more closely.
- Treat the final interactive-command lock inconsistency as future hardening,
  not a merge blocker, because the reviewed branch now has unanimous approval.

## Rationale

Alternatives considered:
- Leave the Round 2 items uncommitted locally and merge the earlier pushed
  branch head.
- Fix only the blocking correctness issues and leave output/spec alignment
  and self-heal coverage for later.
- Keep the stale provenance analysis helpers in place as “deprecated”
  compatibility code.
- Expand this pass to also refactor the interactive mutation helpers onto the
  same locked-write pattern as batch mode.

Why rejected:
- The local work addressed real review feedback and should be published before
  merge so the branch matches the reviewed implementation.
- Splitting the remaining spec-alignment and coverage items again would leave
  the PR half-finished despite the work already being straightforward and
  verified.
- Dead parallel code paths were the maintenance trap called out by all three
  reviewers.
- The interactive mutation lock refactor would widen scope after approval and
  was not necessary for merge readiness.

## Consequences

Impacts:
- PR #39 now includes the production evidence parser, enrich-side library
  locking, protection-default correction, acknowledgement cleanup, repair
  self-heal hardening, and CLI output alignment that the review asked for.
- The branch is pushed, the PR has an explicit update comment, and the draft
  PR has been marked ready for review.
- Validation now covers the production markdown evidence format, lock
  behavior, self-heal invariants, dry-run limit semantics, and refresh-hash
  snapshot output.
- The only remaining note on the PR is a minor future-hardening suggestion
  around interactive mutation helpers, not a merge blocker.

## Testing

- `./.venv/bin/python -m py_compile folio/provenance.py folio/cli.py folio/enrich.py folio/pipeline/provenance_analysis.py tests/test_provenance.py tests/test_provenance_cli.py tests/test_enrich.py`
- `./.venv/bin/pytest tests/test_provenance.py tests/test_provenance_cli.py tests/test_enrich.py -q`
- `./.venv/bin/pytest tests/test_frontmatter.py -q`
- `./.venv/bin/pytest tests/test_enrich_integration.py -q`
- `./.venv/bin/pytest tests/test_cli_tier2.py -q`
