---
id: log_20260309_pr-12-tier1-rerun-validation-and-merge-readiness
type: log
status: active
event_type: fix
source: codex
branch: codex/pr-12-review
created: 2026-03-09
---

# pr-12-tier1-rerun-validation-and-merge-readiness

## Summary

Reviewed PR #12 end-to-end after the sandbox staging-dir fix and rerun
documentation landed. Re-verified the changed code paths in
`folio/pipeline/normalize.py` and `folio/converter.py`, reran the full Python
test suite against the PR worktree, and checked the validation docs for
consistency with the code and checked-in artifacts.

The final cleanup pass fixed two remaining documentation issues before merge:
the rerun report now distinguishes checked-in artifacts from locally generated
run logs/JSON, and the rerun session log no longer contains trailing
whitespace.

## Root Cause

The original renderer fix in PR #10 solved the Launch Services / fatigue
problems but still wrote PowerPoint PDFs into per-deck output locations, which
triggered PowerPoint App Sandbox "Grant File Access" dialogs on managed macOS.
That made the reported Tier 1 rerun outcome depend on a local validation-time
workaround until the fixed staging-directory approach was committed in PR #12.

During review, the remaining non-code issues were documentation integrity
problems: the report implied certain rerun artifacts were committed to the repo
when they were only produced locally, and the session log still had formatting
debt that caused `git diff --check` to fail.

## Fix Applied

PR #12 changes PowerPoint export to use a single fixed staging directory at
`~/Documents/.folio_pdf_staging/`, then moves each exported PDF into the normal
downstream output directory. This reduces sandbox prompts from one per file to
at most one per batch session while preserving the existing pipeline contracts
for image extraction, text extraction, versioning, and frontmatter generation.

The final docs cleanup updated the rerun report artifact section to separate:

- checked-in reusable assets (report, session log, chat log, validator, rerun
  scripts)
- locally generated run outputs (preflight log, batch logs, validation JSON)

This keeps the validation evidence honest and reproducible.

## Testing

- `PYTHONPATH=/tmp/folio-pr12 /Users/jonathanoh/Dev/folio.love/.venv/bin/pytest tests -q`
  -> `434 passed, 3 skipped`
- `git -C /tmp/folio-pr12 diff --check`
  -> clean after the final documentation cleanup
- Manual review confirmed the rerun report now matches the committed artifact
  set and the PR branch is merge-ready
