---
deliverable_id: folio-watch-v1-4-0
phase: D.2
role: alignment
family: codex
status: completed
evidence_labels_used:
  - direct-run
---
# D.2 Alignment R2 Review: folio-watch-v1-4-0

## Verdict
approve

## Scope
This round-2 alignment review checked whether the round-1 blocker around failed watch inputs was closed for `folio-watch-v1-4-0`. The review was limited to the requested evidence files: `folio/watch.py`, `tests/test_watch.py`, `docs/validation/strict_p3_rerun_2026_05_12/folio-watch-v1-4-0_phase_a_spec.md`, and `frameworks/manifests/folio-watch-v1-4-0.yaml`.

## Evidence
The Phase A spec requires `folio watch <dir> [--once] [--dry-run] [--quiet]`, stable-size waits, serial processing, success archiving, and failure writes under `_failed/`. The manifest summary also calls out failure quarantine as part of the deliverable contract.

Static inspection confirms the failure path now quarantines the source file. `run_watch_once` catches processing exceptions and calls `_write_failure(...)`; `_write_failure` creates the watch-directory `_failed/` folder, moves the original source file into that folder with a unique destination, and writes a sibling `{quarantined_name}.error.log` file containing the exception type, message, and traceback. The active watch scan explicitly skips `_archive` and `_failed`, so quarantined files are no longer returned by `_iter_watch_files`.

The focused test `test_watch_once_writes_failure_log` covers the blocker directly: it forces `ingest_email` to raise, asserts the result is failed, asserts the output path is `_failed/thread.eml`, asserts a `_failed/thread.eml.error.log*` file exists and includes the failure text, asserts the original active-directory source no longer exists, asserts the quarantined source exists, and then runs `run_watch_once` again and expects an empty result list. That confirms a second watch pass does not reprocess the failed file.

## Direct Run
Command run from the repository root:

```bash
./.venv/bin/python -m pytest tests/test_watch.py -q
```

Result:

```text
.....                                                                    [100%]
5 passed in 0.08s
```

## Blocker Closure
The round-1 blocker is fixed. Failed source files are moved into `_failed/`, the failure log is written alongside the quarantined file, and the second `run_watch_once` does not reprocess the failed file because `_failed/` is excluded from active watch iteration.
