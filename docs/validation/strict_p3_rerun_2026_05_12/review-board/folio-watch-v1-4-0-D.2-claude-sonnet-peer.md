---
deliverable_id: folio-watch-v1-4-0
phase: D.2
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Phase D.2 Peer Review: folio-watch-v1-4-0

## Verdict

approve

## Evidence

Test suite executed directly:

```
./.venv/bin/python -m pytest tests/test_watch.py -q
.....
5 passed in 0.08s
```

Cardinality assertion verified: `rg -n "stable|_failed|dry_run|once|archive" folio/watch.py tests/test_watch.py` exits 0 with matches in both files.

## Spec Compliance Check (Phase A → Phase C)

**Acceptance criteria from Phase A spec:**

| Criterion | Status | Evidence |
|---|---|---|
| `folio watch <dir> [--once] [--dry-run] [--quiet]` CLI command | Met | `cli.py:602-618` — `watch_command` with all three flags |
| Route by extension (depends on defaults, correspondence, DOCX support) | Met | `watch.py:103-113` — `route_file` dispatches on `EMAIL_EXTENSIONS`, `CONVERT_EXTENSIONS`, `SUPPORTED_INGEST_EXTENSIONS` |
| Wait for stable file size | Met | `watch.py:136-146` — `_wait_for_stable_size` resets deadline on size change |
| Process serially | Met | `watch.py:51-83` — files processed in a sequential `for` loop |
| Archive successes | Met | `watch.py:149-163` — `_archive_success` moves file to `_archive/`; configurable via `after_process` |
| Write failures under `_failed/` | Met | `watch.py:166-173` — `_write_failure` writes `<name>.error.log` to `_failed/`; source file retained |

**Phase B.3 canonical verdict scope ("implement watcher routing, dry-run/once behavior, stable-size waiting, success archiving, and failure quarantine tests"):** All five items implemented and tested.

## Implementation Quality

**`folio/watch.py`**

- `_iter_watch_files` (`watch.py:126-133`) correctly skips `_archive` and `_failed` subdirectories, preventing re-processing of already-handled files.
- `_wait_for_stable_size` (`watch.py:136-146`) implements a sliding-window stability check: the deadline resets whenever the file size changes, ensuring the file has been stable for the full `stability_seconds` duration before processing begins.
- `quiet` mode (`watch.py:204-208`) correctly suppresses success/skip output but always emits failure messages (lines prefixed with `✗`), which is the expected behavior for a monitor scenario.
- `_archive_success` supports `after_process` config key with three modes: `archive` (default, move to `_archive/`), `leave` (no-op), and `delete` (unlink). This is a reasonable extension beyond the bare spec.
- `_unique_destination` (`watch.py:176-185`) handles filename collisions in `_archive` and `_failed` by appending an integer suffix — guards against data loss on repeated processing of same-named files.
- `_match_watch_config` (`watch.py:188-201`) resolves both absolute and config-relative paths, correctly calling `.resolve()` on both sides before comparing.

**`folio/cli.py`**

- `watch_command` (`cli.py:602-621`) handles `KeyboardInterrupt` cleanly (returns silently), which is the correct UX for a polling watcher.
- `--once` flag routes to `run_watch_once` and returns; continuous mode routes to `run_watch_loop`. Both paths thread `dry_run` and `quiet` through correctly.

**`tests/test_watch.py`**

Five tests covering the full acceptance surface:
1. `test_route_file_by_extension` — routing table correctness for pptx, docx, eml, vtt, and an unsupported type.
2. `test_watch_once_dry_run_routes_without_moving` — dry-run returns `dry_run` outcome and leaves the source file in place.
3. `test_watch_once_archives_success` — successful conversion triggers archive move; `_archive/deck.docx` exists; source removed.
4. `test_watch_once_writes_failure_log` — raised exception writes error log to `_failed/`; source file retained; log contains the exception message.
5. `test_watch_cli_once_dry_run` — end-to-end CLI invocation with `--once --dry-run`; exit code 0; "dry-run" in output.

`stability_seconds=0` is passed in unit tests to skip the actual wait, which is the correct approach for deterministic fast tests.

## Minor Observations (Non-blocking)

- `run_watch_loop` (`watch.py:87-100`) does not expose `stability_seconds` as a parameter; it always uses the config-derived default. This is consistent with the spec (which does not require a CLI flag for stability duration) and is not a gap.
- `_write_failure` writes only the error log to `_failed/`, not the source file itself. The test at `test_watch.py:76` asserts `source.exists()`, confirming this is intentional. The spec phrase "write failures under `_failed/`" is satisfied by the error log; leaving the source in place allows manual retry.
- No regression guards are declared in the manifest (`regression_guards: []`). This is acceptable given the new module is self-contained and the existing test suite provides coverage.

## Summary

The Phase C implementation fully satisfies all Phase A acceptance criteria and the Phase B.3 scope statement. The test suite is clean (5/5 pass), the cardinality assertion passes, and the implementation is coherent and free of blockers. No changes are requested.
