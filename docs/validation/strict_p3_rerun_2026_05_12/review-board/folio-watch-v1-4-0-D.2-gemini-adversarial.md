---
deliverable_id: folio-watch-v1-4-0
phase: D.2
role: adversarial
family: gemini
status: completed
evidence_labels_used:
  - static-inspection
---
# Phase D.2 Implementation Review - folio-watch-v1-4-0 - gemini adversarial

## Verdict
request changes

## Findings
There is a blocking implementation finding in `folio/watch.py` regarding the failure quarantine requirement:

- **Incomplete Failure Quarantine Leading to Infinite Retry Loop**: The `_write_failure` function correctly creates an error log in the `_failed` directory, but it fails to move or delete the original source file from the watched directory. Because `run_watch_loop` continuously polls the directory via `run_watch_once`, and `_iter_watch_files` does not exclude previously failed files, the watcher will pick up the same failing file on every single iteration. This results in an infinite processing loop that will rapidly generate endless error logs (e.g., `file.error.log-1`, `file.error.log-2`, etc.) and consume system resources unnecessarily. To resolve this, `_write_failure` must either move the failing file into the `_failed` quarantine directory along with the log, or otherwise ensure the file is removed from the active polling area.

## Test Assessment
Based on static inspection, the test surface in `tests/test_watch.py` covers basic routing, success archival, and dry-run execution. However, the failure quarantine coverage is flawed and inadequate:

1. The test `test_watch_once_writes_failure_log` explicitly asserts the incorrect behavior (`assert source.exists()`) by ensuring the file remains in the watched directory after a failure, rather than asserting it has been moved to quarantine.
2. There are no tests verifying the behavior of `run_watch_loop` or consecutive `run_watch_once` executions to catch the infinite retry loop issue described above.

The test suite must be updated to enforce that failed files are properly quarantined out of the source directory and not re-processed on subsequent polling intervals.
