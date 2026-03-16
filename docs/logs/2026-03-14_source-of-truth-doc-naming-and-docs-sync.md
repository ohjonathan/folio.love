---
id: log_20260314_source-of-truth-doc-naming-and-docs-sync
type: log
status: active
event_type: chore
source: codex
branch: main
created: 2026-03-14
---

# source-of-truth doc naming and docs sync

## Summary

Updated the canonical product and architecture doc naming so the live
source-of-truth docs no longer carry `_v2` suffixes, synced all repo references
to the renamed files, refreshed the Ontos context map, and prepared the latest
doc changes for push on `main`.

## Goal

- Remove `_v2` naming from the live source-of-truth roadmap and ontology docs
- Keep the repo internally consistent after the rename
- Push the latest docs updates without touching unrelated local-only workspace
  files

## Key Decisions

- Renamed the canonical roadmap to `docs/product/04_Implementation_Roadmap.md`
- Renamed the canonical ontology to
  `docs/architecture/Folio_Ontology_Architecture.md`
- Removed `_v2` from the live doc IDs/title where it was part of the canonical
  label
- Left `_v2` references only in historical archive material rather than
  rewriting archival history
- Regenerated `Ontos_Context_Map.md` after the rename instead of editing it by
  hand

## Changes Made

- Updated path references across prompts, specs, validation docs, logs, and the
  generated context map
- Refreshed the roadmap status section so Tier 1 closeout and Tier 2
  accelerated validation are reflected in the canonical roadmap
- Included the current user-authored docs changes in the final git push request

## Alternatives Considered

- Keeping the `_v2` filenames and only changing prose references
- Renaming the files but leaving the internal doc IDs/title unchanged
- Rewriting archived Ontos history to remove `_v2` naming retroactively

## Impacts

- The live roadmap and ontology now read as the single source-of-truth docs
  instead of version-suffixed variants
- Future references should use the non-`_v2` canonical paths
- Ontos-generated context now points at the renamed canonical docs
- Historical archive material still preserves older naming where appropriate

## Testing

- `git diff --check` on the roadmap update passed before the earlier push
- `ontos map` regenerated the context map successfully after the doc rename
- Follow-up whitespace cleanup was committed after the rename sweep
