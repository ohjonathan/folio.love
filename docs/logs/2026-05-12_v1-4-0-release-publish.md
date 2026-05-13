---
id: log_20260512_v1-4-0-release-publish
type: log
status: active
event_type: release
source: codex
branch: main
created: 2026-05-12
---

# v1.4.0 release publish

## Summary

Published Folio `v1.4.0` as the first public PyPI/GitHub release since
`v0.6.4`. The release prep commit bumped `pyproject.toml` from `1.0.0` to
`1.4.0` and added a top-level `CHANGELOG.md` entry covering the May 2026
GitHub issue closeout features.

## Changes Made

- Committed `chore: prepare folio-love v1.4.0 release` on `main`
  (`b69c5add2e46b72a5880ce1fd1f69756894c2e4c`).
- Created and pushed annotated tag `v1.4.0` at the same commit.
- Triggered the existing `Publish to PyPI` GitHub Actions workflow via the
  tag push.
- Verified PyPI publication at
  `https://pypi.org/project/folio-love/1.4.0/` with both wheel and sdist.
- Created the GitHub release:
  `https://github.com/ohjonathan/folio.love/releases/tag/v1.4.0`.

## Goal

Bring GitHub tagging/releases and PyPI publication back in sync with the
current package state after PR #74 landed the strict-P3 GitHub issue closeout
work.

## Key Decisions

- Released as `v1.4.0`, not `v1.0.0`, because `v1.0.0` was already the April
  `folio enrich diagnose` package metadata, while the merged May work includes
  feature slices through `folio-watch-v1-4-0`.
- Pushed the release-prep commit to `main` and waited for the `Tests` workflow
  before tagging.
- Used the existing tag-triggered PyPI trusted-publishing workflow rather than
  a local `twine upload`.
- Created the GitHub release only after the PyPI workflow succeeded and the
  `1.4.0` PyPI endpoint showed both artifacts.

## Alternatives Considered

- Tagging current `main` as `v1.0.0`: rejected because it would publish May
  features under the older April changelog/version line.
- Local PyPI upload: rejected because the repository already has a trusted
  publishing workflow tied to `v*` tags.
- Creating the GitHub release before PyPI verification: rejected to avoid a
  release page pointing to an artifact that had not appeared publicly yet.

## Testing

- Local full test suite: `./.venv/bin/python -m pytest tests -q`:
  `2100 passed, 6 skipped`.
- Local package build: `./.venv/bin/python -m build`.
- Package validation: `./.venv/bin/python -m twine check dist/*`: both wheel
  and sdist passed.
- Local metadata inspection confirmed `Name: folio-love`, `Version: 1.4.0`,
  `Requires-Python: >=3.10`.
- GitHub `Tests` workflow on `main` passed for Python 3.10 and 3.13.
- GitHub `Publish to PyPI` workflow for tag `v1.4.0` passed and generated
  PyPI attestations.

## Impacts

- `pip install folio-love==1.4.0` is now available.
- GitHub release `v1.4.0` is published and aligned with the PyPI artifact.
- The release tag remains pinned to the release-prep commit; this session log
  is intentionally outside the release artifact itself.
