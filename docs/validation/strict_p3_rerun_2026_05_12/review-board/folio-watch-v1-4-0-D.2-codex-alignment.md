---
deliverable_id: folio-watch-v1-4-0
phase: D.2
role: alignment
family: codex
status: completed
evidence_labels_used:
  - direct-run
---

# D.2 Codex Alignment Review: folio-watch-v1-4-0

## Verdict
request changes

## Evidence

- Read Phase A spec: `docs/validation/strict_p3_rerun_2026_05_12/folio-watch-v1-4-0_phase_a_spec.md`.
- Read Phase B.3 canonical verdict: `docs/validation/strict_p3_rerun_2026_05_12/folio-watch-v1-4-0_B.3_canonical_verdict.md`.
- Inspected implementation and tests: `folio/watch.py`, `folio/cli.py`, `folio/config.py`, and `tests/test_watch.py`.
- Direct run: `./.venv/bin/python -m pytest tests/test_watch.py -q` exited 0 with `5 passed in 0.08s`.

## Blocking Finding

Failure quarantine is not implemented. Phase A requires failures under `_failed/`, and B.3 explicitly includes failure quarantine in Phase C scope. The current failure path in `folio/watch.py` only writes `source.name.error.log` under `_failed/` at `folio/watch.py:166`; it does not move or copy the failed source file out of the watched directory. `run_watch_once` catches the exception at `folio/watch.py:74` and then returns with the original source still present. In continuous mode, `run_watch_loop` calls `run_watch_once` every interval at `folio/watch.py:98`, so the same failed source will be picked up repeatedly, generating repeated failures instead of being quarantined.

The test currently encodes this non-quarantine behavior: `tests/test_watch.py:77` asserts that the failed source still exists. That should be inverted or replaced with an assertion that the input file is placed under `_failed/` using the same collision-safe naming approach as success archives, with the error log kept alongside it.

## Aligned Areas

The rest of the narrow slice appears aligned with Phase A and B.3: `folio watch <dir>` exposes `--once`, `--dry-run`, and `--quiet` in `folio/cli.py:602`; extension routing covers DOCX/PPTX/PDF conversion, email ingest, text/transcript ingest, and skip behavior in `folio/watch.py:103`; dry-run avoids pipeline execution and movement in `folio/watch.py:58`; stable-size waiting is present in `folio/watch.py:136`; and successful inputs are archived by default under `_archive` in `folio/watch.py:149`.

## Requested Change

Move failed source files into `_failed/` after a processing exception, using a unique destination to avoid overwrites, and update `tests/test_watch.py` so the failure case proves quarantine instead of proving the source remains in the active watch directory. After that, rerun the focused pytest command and the lifecycle checks required by the manifest.
