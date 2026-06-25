---
id: log_20260625_v1-5-1-release-publish
type: log
status: complete
event_type: release
source: codex
branch: main
created: 2026-06-25
concepts:
  - release
  - pypi
  - github_release
  - versioning
  - latest_model_policy
---

# v1.5.1 release publish

## Summary

Published Folio `v1.5.1` to PyPI and created the matching GitHub release. This
is a maintenance release that aligns PyPI, GitHub tags/releases, and package
metadata with the post-`v1.5.0` repository state while explicitly not shipping
the pending `v1.6.0` latest-model policy feature.

## Goal

Bring the public package index, Git tag, GitHub Release, and package metadata
back into alignment after the post-`v1.5.0` repo work landed on `main`.

## Changes Made

- Bumped package metadata to `1.5.1` in `pyproject.toml`.
- Bumped `folio.__version__` to `1.5.1` in `folio/__init__.py`.
- Added `CHANGELOG.md` entry `## [v1.5.1] - 2026-06-25`.
- Refreshed `Ontos_Context_Map.md` through activation.
- Committed release prep as `e5d4c7928e6961d6839692f3db4798e63c48bb7d`
  (`chore: prepare folio-love v1.5.1 release`).
- Pushed `main` and waited for the GitHub `Tests` workflow to pass.
- Created and pushed annotated tag `v1.5.1` at the release-prep commit.
- Triggered the existing `Publish to PyPI` trusted-publishing workflow via the
  tag push.
- Verified PyPI publication at `https://pypi.org/project/folio-love/1.5.1/`
  with both wheel and sdist.
- Created the GitHub release:
  `https://github.com/ohjonathan/folio.love/releases/tag/v1.5.1`.

## Key Decisions

- Released as `v1.5.1`, not `v1.6.0`, because
  `docs/trackers/folio-latest-model-policy-v1-6-0.md` still shows the model
  policy lifecycle at scaffold state with `-A.proposal` and Phase A pending.
- Kept the release notes explicit that runtime behavior is unchanged from
  `v1.5.0`.
- Used the existing tag-triggered PyPI trusted-publishing workflow rather than
  a local upload.
- Created the GitHub release only after PyPI publication and fresh install
  verification succeeded.

## Alternatives Considered

- Tagging the current repo state as `v1.6.0`: rejected because the planned
  model-policy feature has not completed proposal, spec, review board,
  implementation, or verification phases.
- Skipping the patch release because the current package code is behaviorally
  unchanged from `v1.5.0`: rejected because the user explicitly asked to align
  PyPI/tagging with the latest repo progress.
- Local `twine upload`: rejected because the repository already has a trusted
  publishing workflow tied to `v*` tags.

## Testing

- `ontos activate`: completed with `usable_with_warnings`.
- `scripts/llm-dev doctor`: passed.
- `git diff --check`: passed before commit.
- Focused future-manifest test command
  `./.venv/bin/python -m pytest tests/test_config.py tests/test_model_policy.py tests/test_llm_providers.py -q`
  failed because `tests/test_model_policy.py` does not exist yet; this is
  expected while `v1.6.0` remains pre-implementation and was not used as a
  `v1.5.1` gate.
- Local full test suite:
  `./.venv/bin/python -m pytest tests/ -q`: `2162 passed, 6 skipped,
  5 warnings`.
- Local package build:
  `./.venv/bin/python -m build --outdir /tmp/folio-love-build-1.5.1` produced
  `folio_love-1.5.1-py3-none-any.whl` and `folio_love-1.5.1.tar.gz`.
- `./.venv/bin/python -m twine check /tmp/folio-love-build-1.5.1/*`: passed
  for both artifacts.
- Local artifact metadata inspection confirmed wheel `Name: folio-love`,
  wheel `Version: 1.5.1`, wheel `folio.__version__ = "1.5.1"`, and sdist
  `pyproject.toml` version `1.5.1`.
- GitHub `Tests` workflow on `main` passed for Python 3.10 and 3.13:
  `https://github.com/ohjonathan/folio.love/actions/runs/28193043770`.
- GitHub `Publish to PyPI` workflow for tag `v1.5.1` passed:
  `https://github.com/ohjonathan/folio.love/actions/runs/28193138153`.
- PyPI JSON reported `info.version = 1.5.1` and both uploaded files:
  `folio_love-1.5.1-py3-none-any.whl` and `folio_love-1.5.1.tar.gz`.
- Fresh PyPI install smoke test in `/tmp/folio-love-pypi-verify-1.5.1`
  confirmed `importlib.metadata.version("folio-love") == "1.5.1"` and
  `folio.__version__ == "1.5.1"`.
- `python3 -m pip index versions folio-love --no-cache-dir` reported latest
  version `1.5.1`.

## Impacts

- `pip install folio-love==1.5.1` is now available.
- GitHub release `v1.5.1` is published and marked latest.
- The release tag `v1.5.1` points to
  `e5d4c7928e6961d6839692f3db4798e63c48bb7d`.
- The pending latest-model policy remains a future `v1.6.0` lifecycle item.
