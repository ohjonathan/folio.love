---
deliverable_id: folio-watch-v1-4-0
phase: B.1
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# B.1 Peer Review: folio-watch-v1-4-0

## Verdict

approve

## Evidence Reviewed

| Artifact | Path |
|---|---|
| Pre-A triage | `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md` |
| Phase A spec | `docs/validation/strict_p3_rerun_2026_05_12/folio-watch-v1-4-0_phase_a_spec.md` |
| Manifest | `frameworks/manifests/folio-watch-v1-4-0.yaml` |

## Stale Evidence Assessment

The pre_a triage (`2026-05-12`) contains an explicit evidence rule: *"prior `folio_*_v1_*` artifacts and the preserved dirty attempt are implementation history only; they are not lifecycle evidence for this rerun."* The spec anchors its scope authority to that triage document by path. The manifest's `pre_a.artifact_path` resolves to the same fresh triage file under `docs/validation/strict_p3_rerun_2026_05_12/`. No reference to prior-cycle artifacts appears in either document as lifecycle evidence. Stale evidence reuse is not present.

## Spec Adequacy

The spec is intentionally terse but covers the minimum viable surface needed to drive implementation:

- **CLI shape**: `folio watch <dir> [--once] [--dry-run] [--quiet]` — matches issue #62 exactly.
- **Routing**: "Route by extension" with a dependency declaration on defaults, correspondence, and DOCX slices (making the composition dependency explicit in prose, even if `sibling_deliverable_ids` is empty in the manifest).
- **Behavioral guarantees**: stable-size wait, serial processing, success archive, `_failed/` quarantine — these four constitute the acceptance floor for the feature.
- **Non-goals**: explicitly excludes prior artifacts as evidence and forbids API keys.
- **Validation chain**: pytest smoke check, `llm-dev verify`, negative lifecycle control, and the three-family B.1/D.2/D.5 dispatch are all cited.

The spec does not capture every edge case from issue #62 (duplicate hash detection, notification backends, daemon healthcheck, config-file reload). These are defensible out-of-scope choices for a v1 slice; the core drop-zone capability is fully described.

## Manifest Adequacy

- `manifest_version: 1.6.0` — satisfies the strict-P3 rerun requirement.
- `lifecycle_receipt_inventory_path` present at `docs/validation/strict_p3_rerun_2026_05_12/review-board/folio-watch-v1-4-0-lifecycle-receipts.yaml`.
- Model assignments for B.1 (`claude-sonnet: peer`, `codex: alignment`, `gemini: adversarial`), D.2, D.5, and remaining phases match the triage spec.
- Cardinality assertion (`rg "stable|_failed|dry_run|once|archive" folio/watch.py tests/test_watch.py`) anchors the five core behavioral keywords to both the implementation and test files — tight contract, low false-positive risk.
- `G-branch-1` gate prerequisite verifies the active branch (`codex/github-issues-closeout-strict-p3-rerun`), preventing slip onto a stale branch.
- Allowed paths cover `folio/watch.py`, `folio/cli.py`, and `tests/test_watch.py`; the `review-board/` wildcard pattern permits this artifact.

## Soft Notes (non-blocking)

1. **`sibling_deliverable_ids: []`** — The manifest does not formally enumerate the cross-slice dependencies on `folio-config-defaults-v1-2-0`, `folio-correspondence-ingest-v1-3-0`, and `folio-document-format-coverage-v1-1-1`, even though the spec prose names them. There is no automated ordering enforcement. This is acceptable provided the implementation degrades gracefully when those capabilities are absent.

2. **`regression_guards: []`** — `folio/cli.py` is shared across all slices on this branch. An empty regression guard list means no automated check that existing CLI subcommands are unaffected. The risk is modest (adding a new `watch` subcommand does not structurally conflict with existing ones), but a guard against `folio ingest --help` exit-0 would be cheap insurance.

3. **`composition_targets: []`** — The watcher requires config-defaults resolution at runtime but does not list the defaults slice as a composition target. This is consistent with how other slices in this rerun are structured, so it is not a defect unique to this manifest.

None of these notes constitute blockers. The spec and manifest together provide sufficient precision to drive a focused implementation of the watch/drop-zone feature without reusing stale evidence.
