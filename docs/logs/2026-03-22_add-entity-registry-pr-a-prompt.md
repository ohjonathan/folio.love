---
id: log_20260322_entity-registry-pr-a-implementation-and-review
type: log
status: active
event_type: entity-registry-pr-a-implementation-and-review
source: cli
branch: feature/v0.5.1-entity-registry
created: 2026-03-22
---

# Entity Registry PR A — Implementation and Review

## Goal

Implement the entity registry data layer, CSV import, and CLI commands
for v0.5.1 of folio.love (PR A of the entity system).

## Summary

Built the entity registry from spec through 4 rounds of PR review:
- Core data layer (`folio/tracking/entities.py`): EntityEntry, EntityRegistry,
  slugify (with NFC normalization), sanitize_wikilink_name, atomic save,
  CRUD operations, alias collision detection, save-without-load guard.
- CSV import (`folio/entity_import.py`): org chart import with department
  auto-creation, reports_to resolution, slug collision rejection (case-insensitive),
  self-referencing guard, strict CSV parsing with line-number error reporting.
- CLI (`folio/cli.py`): `folio entities` group with list/show/import/confirm/reject,
  type-specific detail for non-person entities, canonical name resolution for
  cross-references, entity count in `folio status`.

## Key Decisions

- Case-insensitive canonical name matching for slug collisions (P1 finding)
- Strict CSV parsing (`csv.reader(strict=True)`) for malformed quoting abort (B2)
- `_loaded` guard on save() to prevent data clobbering (B2)
- `to_json()` public method instead of exposing `_data` (S5)
- `reader.line_num` for accurate error line reporting (P3 minor)

## Alternatives Considered

- Renaming `_atomic_write_json` globally: deferred, used alias import instead (S6)
- Inline slug collision logic vs `_check_alias_collisions` helper: chose helper for testability (B1)

## Impacts

- 78 new entity tests (27 core + 28 import + 23 CLI), all passing
- 0 regressions against 1243 baseline
- README updated with full entity system documentation
- PR #34 created, reviewed through 4 rounds, ready to merge

## Testing

```
pytest tests/test_entities.py tests/test_entity_import.py tests/test_cli_entities.py -v
# 78 passed in 0.17s
pytest tests/ -q
# 1316 passed, 3 skipped
```