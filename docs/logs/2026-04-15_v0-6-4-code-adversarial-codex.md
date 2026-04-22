---
id: log_20260415_v0-6-4-code-adversarial-codex
type: log
status: active
event_type: exploration
source: codex
branch: feat/trust-gated-surfacing-v0-6-4
created: 2026-04-15
---

# v0-6-4-code-adversarial-codex

## Objective

Perform D.2 adversarial code review for llm-dev-v1.1 Phase D.2 on the
v0.6.4 trust-gated surfacing implementation. Target breakage, bypass paths,
and latent bugs in `folio/links.py`, `folio/cli.py`, S4-* tests, and the v1.1
spec contract.

## Findings

- Wrote the review artifact to
  `docs/validation/v0.6.4_code_adversarial_codex.md`.
- Verdict: Needs Fixes.
- Blocker D-ADV-001: `links confirm-doc` and `links reject-doc` disclose
  flagged exclusions only when `acted == 0`. In mixed clean+flagged documents,
  they report a partial success and silently omit the flagged-excluded count.
- Should-fix D-ADV-SF-001: `links status --include-flagged` and
  `relationship_status_summary(..., include_flagged=...)` are missing despite
  the v1.1 committed-surface contract.
- Should-fix coverage gaps: S4-11 tests only one stale-registry direction;
  S4-17 does not exercise the full review-output-to-confirm refusal path;
  reject and bulk include-flagged paths need explicit tests.
- No target-frontmatter authorization bypass was found in the shared
  collect/find/confirm/reject paths. `_resolve_target_flagged` uses a per-call
  cache, not global state.

## Conclusions

The implementation handles the core target-frontmatter authority path correctly
and avoids the original single-proposal consent bypass by defaulting
confirm/reject lookups through the filtered collection. Approval should wait on
the mixed bulk-command disclosure fix because it violates the v1.1 rule that
flagged exclusions are disclosed on committed surfaces.

## Key Decisions

- Classified the mixed bulk-command disclosure hole as a blocker because it is
  observable operator-facing behavior, not just incomplete tests.
- Classified the missing `status --include-flagged` path as should-fix because
  it is a spec contract miss, but status remains read-only and does not expose
  proposal IDs.
- Treated `SuppressionCounts.total()` as informational future-proofing, not
  dead code requiring removal, because renderers correctly keep rejection-memory
  and flagged-input counts separate.

## Alternatives Considered

- Considered approving with only test-coverage findings because the main
  confirm/reject consent path is safe. Rejected due to the mixed
  `confirm-doc` / `reject-doc` silent omission.
- Considered making missing `status --include-flagged` a blocker. Kept it
  should-fix because the current status output discloses aggregate
  flagged-excluded counts and does not leak actionable proposal IDs.

## Impacts

- The author should update CLI rendering for `confirm-doc` and `reject-doc` to
  print flagged-excluded diagnostics whenever `flagged_excluded > 0` in default
  mode.
- Add regression coverage for mixed clean+flagged bulk operations, both stale
  target-frontmatter directions, single-proposal reject with/without
  `--include-flagged`, and bulk include-flagged actions.
- Decide whether to implement `links status --include-flagged` or revise the
  spec so status is explicitly disclosure-only.

## Next Steps

- Author fixes D-ADV-001 and adds the missing S4 coverage.
- Re-run D.5 verification after fixes.
