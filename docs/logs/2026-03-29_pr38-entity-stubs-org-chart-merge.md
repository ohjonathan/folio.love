---
id: log_20260329_pr38-entity-stubs-org-chart-merge
type: log
status: active
event_type: fix
source: cli
branch: codex/entity-stubs-org-chart-merge
created: 2026-03-29
---

# pr38-entity-stubs-org-chart-merge

## Goal

Ship PR #38 for entity stub generation, org-chart hierarchy merge, legacy registry
`type` compatibility, and the follow-up correctness fixes required during review
so the branch could merge cleanly to `main`.

## Key Decisions

- Implemented `folio entities generate-stubs` as a derived artifact generator
  under `_entities/<type>/`, keeping stubs out of `registry.json` and protecting
  manual stubs from overwrite.
- Kept broader person-name matching scoped to org-chart imports while restoring
  conservative semantics for plain CSV imports.
- Treated ambiguous live person matches as `unresolved` during enrich
  fingerprint recomputation so stale canonical entity state cannot keep notes on
  the skip path.
- Tightened shared person normalization to reject non-person comma phrases and
  support Unicode comma-form names such as `Díaz, José`.

## Alternatives Considered

- Broadening generic CSV import matching for all person rows: rejected because
  it silently changed existing shipped behavior outside org-chart mode.
- Adding fuzzy or heuristic person matching beyond ordered exact-match variants:
  rejected because the production-test scope explicitly excluded fuzzy and
  phonetic matching.
- Leaving live fingerprint recomputation on the first ambiguous match: rejected
  because it preserved stale entity resolution state after the registry changed.

## Impacts

- PR #38 moved from repeated review blocks to approved merge-ready state.
- The shared person normalization path now behaves consistently across org-chart
  import, ingest resolution, and enrich-time fingerprint recomputation.
- Legacy registries missing `type` can continue through enrich planning with
  compatibility warnings instead of silently dropping eligible documents.

## Testing

- `./.venv/bin/pytest tests/test_registry.py tests/test_enrich.py tests/test_entity_import.py tests/test_entity_resolution.py tests/test_cli_entities.py -q`
- `./.venv/bin/pytest tests/test_entities.py tests/test_entity_import.py tests/test_entity_resolution.py tests/test_cli_entities.py tests/test_registry.py tests/test_enrich.py -q`
- `./.venv/bin/python -m py_compile folio/cli.py folio/entity_import.py folio/entity_stubs.py folio/enrich.py folio/pipeline/entity_resolution.py folio/tracking/entities.py folio/tracking/registry.py`
