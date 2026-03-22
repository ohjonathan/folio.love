---
id: log_20260322_pypi-v020-release-prep
type: log
status: complete
event_type: pypi-v020-release-prep
source: cli
branch: main
created: 2026-03-22
concepts:
  - pypi
  - release
  - ci-cd
  - versioning
---

# PyPI v0.2.0 Release Prep

## Summary

Prepared folio-love v0.2.0 for PyPI publication. Bumped version, cleaned up
stale artifacts, added a GitHub Actions publish workflow, ran full regression
suite, and verified the built package with twine.

## Changes Made

- Bumped `version` from `0.1.0` → `0.2.0` in `pyproject.toml` and `folio/__init__.py`
- Added `.github/workflows/publish.yml` (Trusted Publishing on `v*` tag push)
- Deleted stale `dist/` build artifacts (old 0.1.0 whl/tar.gz)
- Removed `AGENTS.md.bak` from repo root
- Tagged `v0.2.0`

## Testing

- Full test suite: **1183 passed, 3 skipped** (pytest)
- `python -m build`: sdist + wheel built cleanly
- `twine check dist/*`: **PASSED** for both artifacts

## Key Decisions

- Version 0.2.0 chosen (22 commits since v0.1.0 including field hardening,
  enterprise operability, performance patches, and CI)
- Publish workflow uses Trusted Publishing (no API token secret needed once
  configured on pypi.org)