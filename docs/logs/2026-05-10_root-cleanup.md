---
id: log_20260510_root-cleanup
type: log
status: active
event_type: chore
source: codex
branch: main
created: 2026-05-10
---

# root-cleanup

## Goal

Clean the repository root by moving historical review artifacts into the docs
archive and pruning ignored local artifacts while preserving the Python virtual
environment.

## Key Decisions

- Preserved all tracked review artifacts instead of deleting them.
- Archived root review Markdown under `docs/archive/reviews/` by review group:
  Tier 4 proposal R1, PR D Phase B, and PR E.
- Added an archive index so older logs that reference former root paths remain
  understandable.
- Kept `.venv/` and removed only safe ignored local artifacts.

## Alternatives Considered

- Keeping review artifacts in the root: rejected because the root had become
  difficult to scan.
- Deleting historical review artifacts: rejected because they preserve review
  and governance history.
- Pruning `.venv/`: rejected to avoid forcing local environment recreation.

## Impacts

- Root now contains project entrypoints, configuration, and top-level source
  directories instead of review-round artifacts.
- Ontos context and agent files were regenerated with `ontos map --sync-agents`.
- `ontos doctor` reports the context map as valid and AGENTS.md as up to date,
  but still fails on the pre-existing absence of a root `.ontos.toml`.
- `git status --ignored` shows `.venv/` as the remaining ignored root artifact.
