---
id: log_20260604_v1-5-0-release-publish
type: log
status: active
event_type: release
source: codex
branch: main
created: 2026-06-04
concepts:
  - release
  - pypi
  - github_release
  - issue_75
  - issue_76
---

# v1.5.0 release publish

## Summary

Published Folio `v1.5.0` to PyPI and created the matching GitHub release for
the merged GitHub issue #75 and #76 closeout work. The release includes VTT/SRT
timestamp normalization, slide-scoped diagram retries, first-class
`concept-map` and `process` diagram extraction, and stronger diagram
provider-failure recovery.

## Changes Made

- Merged release prep PR #80 into `main`
  (`a10ed012eb8e8d828ef196112530a7f7832b63e8`).
- Bumped package metadata to `1.5.0` in `pyproject.toml` and
  `folio/__init__.py`.
- Moved the issue #75/#76 changelog entries into `## [v1.5.0] - 2026-06-04`.
- Updated `README.md` with the new diagram retry flags:
  `--diagrams-only`, `--slides`, `--retry-failed-diagrams`, and
  `--retry-review-required-diagrams`.
- Created and pushed annotated tag `v1.5.0` at the merge commit.
- Triggered the existing `Publish to PyPI` GitHub Actions workflow via the
  tag push.
- Verified PyPI publication at
  `https://pypi.org/project/folio-love/1.5.0/` with both wheel and sdist.
- Created the GitHub release:
  `https://github.com/ohjonathan/folio.love/releases/tag/v1.5.0`.

## Goal

Publish the post-merge GitHub issue #75/#76 work as an installable public
release and bring GitHub tags, GitHub Releases, PyPI artifacts, package
metadata, changelog, and client-facing README documentation back into alignment.

## Key Decisions

- Released as `v1.5.0` because issue #76 adds user-facing `folio convert`
  functionality, while issue #75 contributes a transcript timestamp bug fix.
- Used the existing tag-triggered PyPI trusted-publishing workflow rather than
  a local upload.
- Created the GitHub release only after the PyPI workflow succeeded and the
  `1.5.0` PyPI endpoint showed both artifacts.
- Kept this release-publish session log outside the release tag, matching the
  `v1.4.0` release pattern.

## Alternatives Considered

- Re-publishing as `1.4.0`: rejected because PyPI already contained
  `folio-love==1.4.0`.
- Releasing as `1.4.1`: rejected because the diagram retry CLI additions are
  user-facing feature work rather than only patch-level repair.
- Creating the GitHub release before PyPI verification: rejected to avoid a
  GitHub release page pointing to artifacts that had not appeared publicly yet.

## Testing

- Local full test suite during release readiness review:
  `./.venv/bin/python -m pytest tests/ -q`: `2162 passed, 6 skipped`.
- Local package build during release readiness review:
  `./.venv/bin/python -m build --outdir /tmp/folio-love-build`, producing
  wheel and sdist artifacts.
- GitHub `Tests` workflow on `main` passed for commit
  `a10ed012eb8e8d828ef196112530a7f7832b63e8`:
  `https://github.com/ohjonathan/folio.love/actions/runs/26983267058`.
- GitHub `Publish to PyPI` workflow for tag `v1.5.0` passed:
  `https://github.com/ohjonathan/folio.love/actions/runs/26983286468`.
- PyPI index inspection showed `folio-love (1.5.0)` as latest with available
  versions `1.5.0, 1.4.0, 0.6.4, 0.4.0, 0.3.0, 0.2.0, 0.1.0`.
- Fresh PyPI install smoke test in `/tmp/folio-love-pypi-verify` confirmed
  `importlib.metadata.version("folio-love") == "1.5.0"` and
  `folio.__version__ == "1.5.0"`.

## Impacts

- `pip install folio-love==1.5.0` is now available.
- GitHub release `v1.5.0` is published and aligned with the PyPI artifact.
- Client-facing documentation now covers the new diagram retry workflow.
- The remaining post-release technical follow-up is to audit/update the
  deprecated default Anthropic model before the next release.
