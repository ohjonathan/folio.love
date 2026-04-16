---
id: log_20260415_v0-6-1-code-adversarial-review
type: log
status: active
event_type: exploration
source: codex
branch: feat/proposal-lifecycle-rename-v0-6-1-C-author-claude
created: 2026-04-15
---

# v0.6.1 code adversarial review

## Objective
Goal: perform D.2 adversarial code review for the v0.6.1 relationship proposal `status` -> `lifecycle_state` rename on branch `feat/proposal-lifecycle-rename-v0-6-1-C-author-claude`, using `git diff main..HEAD`, static inspection, and the requested targeted pytest run.

## Findings
- `ontos map` activation failed on existing metadata warnings/errors; `python3 -m ontos map` also failed because the Python module was unavailable. Existing `Ontos_Context_Map.md` and the v0.6.1 spec were loaded directly.
- Implementation code matched the approved v1.1 spec in `folio/pipeline/enrich_data.py`, `folio/enrich.py`, `folio/links.py`, and `folio/graph.py`.
- `folio/provenance.py` remained untouched by `git diff main..HEAD`, as required by spec §3.6.
- Requested tests passed: `python3 -m pytest tests/test_enrich_data.py tests/test_enrich.py tests/test_links_cli.py tests/test_graph_cli.py -q` reported `149 passed in 0.33s`.
- One stale relationship-proposal test assertion remains in `tests/test_enrich_integration.py:625`, where the assertion still reads `p.get("status")` instead of checking `lifecycle_state`.

## Key Decisions
- Verdict was set to `Needs Fixes` because the stale test assertion can pass even when a new-format queued proposal remains unsuppressed.
- No implementation-code bug was filed because the required migration code paths and raw-dict fallback behavior matched the spec.
- Existing untracked files not created by this review were left untouched.

## Alternatives Considered
- Approving with a note was rejected because the user explicitly asked whether any test assertions still reference the old proposal `status` field, and the surviving assertion is a real regression-guard gap.
- Treating legacy `status` fixtures in `tests/test_enrich_integration.py` as findings was rejected except for the assertion: the fixtures can plausibly serve backward-compat coverage, while the assertion no longer validates new-format output.

## Conclusions
Review artifact written to `docs/validation/v0.6.1_code_adversarial_codex.md` with one should-fix finding and a `Needs Fixes` verdict.

## Next Steps
- Update `tests/test_enrich_integration.py:625` to assert against `lifecycle_state != "queued"` with an explicit legacy fallback only if mixed old/new proposal fixtures are intentional.
- Re-run at least `python3 -m pytest tests/test_enrich_integration.py::TestRejectedProposalSuppression::test_suppressed_without_basis_change -q` plus the requested four-file pytest subset after the test assertion is corrected.

## Impacts
- The review adds validation documentation only.
- No product code or tests were modified by this review.
