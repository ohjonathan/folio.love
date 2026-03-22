---
id: claude_code_prompt_entity_registry_pr_a
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: claude-code
created: 2026-03-22
depends_on:
  - v0.5.1_tier3_entity_system_spec
---

# Implementation Prompt: Entity Registry, CLI, and CSV Import (PR A)

**For:** Developer Agent Team (CA lead + spawned developers)
**Approved spec:** `docs/specs/v0.5.1_tier3_entity_system_spec.md` (rev 3)
**Branch:** `feature/v0.5.1-entity-registry` from `main`
**Test command:** `python3 -m pytest tests/ -v`
**Test baseline:** 1243 tests passing on `main`
**Commit format:** `feat(entities): description`
**PR title:** `feat: entity registry, CLI, and CSV import`

---

## Agent Team Activation

This requires an agent team.

1. The CA lead reads this prompt end-to-end, investigates the codebase to
   verify the patterns described below, writes the implementation plan,
   decomposes the work, spawns developers, and owns final verification.
2. One developer is sufficient — the work is a tightly coupled vertical slice
   (data layer → import logic → CLI). Over-decomposing adds coordination
   overhead without saving time.
3. The CA lead verifies the output against the acceptance criteria (§14 of the
   approved spec), runs the full test suite, and runs the smoke tests before
   opening the PR.

---

## Task Context

### What to Build

The **entity registry data layer, CLI commands, and CSV import** — PR A of the
v0.5.1 entity system. This creates the foundation that PR B (ingest-time
resolution) will consume.

### What NOT to Build

PR A builds the data layer. It does NOT implement ingest-time resolution. These
are explicit exclusions — violating them means the PR will fail review:

- Do NOT modify `registry.json` or `RegistryEntry`
- Do NOT modify `folio/pipeline/interaction_analysis.py`
- Do NOT modify `folio/output/interaction_markdown.py`
- Do NOT modify `folio/output/frontmatter.py`
- Do NOT modify `folio/tracking/registry.py`
- Do NOT add entity fields to note frontmatter
- Do NOT implement ingest-time resolution (PR B)
- Do NOT implement LLM soft match (PR B)
- Do NOT create entity markdown stub files
- Do NOT implement `folio entities create`, `edit`, `merge`, or `delete`
- Do NOT implement cross-type entity lookup (resolution is type-strict, D7)

### What Already Exists

`folio ingest` (v0.5.0, PR #32) is merged to `main`. It extracts entities from
transcripts and renders them as unresolved `[[wikilinks]]`. The entity system
in this PR makes those names resolvable by creating a registry to match them
against. Key shipped baseline:

- `InteractionAnalysisResult.entities: dict[str, list[str]]` with keys
  `people`, `departments`, `systems`, `processes`
- `_coerce_entities()` deduplicates case-insensitively, preserves original case
- `interaction_markdown.py` renders `- [[EntityName]]` in `## Entities Mentioned`
- `registry.json` tracks interaction entries alongside evidence entries
- `folio status`/`scan`/`refresh`/`promote` all work with interactions

---

## Codebase Patterns to Follow

### Atomic Write Pattern

`folio/tracking/registry.py:289-323` — `_atomic_write_json(path, data)`:

```python
def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    tmp_path = path.with_suffix(".tmp")
    try:
        lock_fd = open(lock_path, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            tmp_path.write_text(json.dumps(data, indent=2))
            tmp_path.rename(path)
        except OSError as e:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise OSError(
                f"Failed to write registry {path}: {e}. "
                f"Check disk space and permissions."
            ) from e
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
    except OSError:
        if 'lock_fd' not in dir():
            raise
```

The entity registry MUST use this identical function. Import it directly:
`from .registry import _atomic_write_json`. Same package, `_` prefix is
advisory in Python. This avoids duplicating the locking logic (precedent:
`versions.py` has its own copy, but importing is cleaner).

### RegistryEntry Serialization Convention

`registry.py:45-60` — `to_dict()` excludes `None` fields, preserves empty
`list`/`dict`. `entry_from_dict()` at line 264 filters unknown keys for
forward compatibility. The entity dataclass should follow both conventions.

### CLI Pattern

`folio/cli.py` — single file, 1087 lines. All 7 commands are flat
`@cli.command()` decorators on the main `cli` Click group. No nested groups
exist yet. The entity commands introduce the **first Click group**.

Every command follows this pattern:
```python
@cli.command()
@click.argument(...)
@click.option(...)
@click.pass_context
def command_name(ctx, ...):
    config = ctx.obj["config"]  # FolioConfig
    library_root = config.library_root.resolve()
    # ...
```

CLI entry point is at `folio/cli.py:1085-1087`:
```python
def main():
    cli()
```

Imports at top of `cli.py`:
```python
import click
from .config import FolioConfig
# ... other imports
logger = logging.getLogger(__name__)
```

Error handling pattern: `click.echo(f"✗ ...", err=True)` + `sys.exit(1)`.
Output icons: `✓` success, `✗` error, `⚠` warning, `!` flag.

### Test Patterns

`tests/test_registry.py` — helpers:
```python
def _make_folio_markdown(path: Path, frontmatter: dict) -> None:
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{yaml_str}---\n\n# Content\n")

def _make_source(path: Path, content: str = "binary data") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

def _sample_entry(**overrides) -> RegistryEntry:
    defaults = dict(id="test_evidence_...", title="Test Deck", ...)
    defaults.update(overrides)
    return RegistryEntry(**defaults)
```

`tests/test_cli_tier2.py` — CLI test setup:
```python
from click.testing import CliRunner
from folio.cli import cli

def _make_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(config, default_flow_style=False))
```

CLI tests invoke via:
```python
runner = CliRunner()
result = runner.invoke(cli, ["--config", str(config_path), "command", ...])
assert result.exit_code == 0
```

### Package Layout

```
folio/
├── cli.py              # All CLI commands (modify)
├── config.py           # FolioConfig — library_root: Path
├── ingest.py           # folio ingest (do not modify)
├── tracking/
│   ├── __init__.py     # Currently: from . import registry (modify)
│   ├── registry.py     # _atomic_write_json, RegistryEntry (do not modify)
│   ├── sources.py      # check_staleness, compute_file_hash
│   └── versions.py     # version tracking
├── pipeline/           # analysis, extraction (do not modify)
├── output/             # frontmatter, markdown (do not modify)
└── llm/                # providers
tests/
├── conftest.py         # 5 shared fixtures (tmp_output, sample_pptx, etc.)
├── test_registry.py    # 641 lines, pattern to follow
├── test_cli_tier2.py   # CliRunner pattern
└── fixtures/
    └── ingest/         # 9 transcript fixtures
```

---

## File Map

### New Files

| File | Purpose |
|------|---------|
| `folio/tracking/entities.py` | `EntityEntry` dataclass, `EntityRegistry` class, `slugify()`, exceptions |
| `folio/entity_import.py` | `import_csv()`, `ImportResult`, CSV parsing, two-pass resolution |
| `tests/test_entities.py` | ~22 unit + durability tests |
| `tests/test_entity_import.py` | ~21 import tests |
| `tests/test_cli_entities.py` | ~15 CLI tests |
| `tests/fixtures/test_org_chart.csv` | CSV fixture |
| `tests/fixtures/test_entities.json` | Pre-populated registry fixture |

### Modified Files

| File | Change | Lines |
|------|--------|-------|
| `folio/cli.py` | Add `entities` Click group (5 subcommands); add entity count in `status` | After line 673 for status; new group at end before `main()` |
| `folio/tracking/__init__.py` | Add `from . import entities` | Line 3 |

---

## Implementation Spec

### 1. `folio/tracking/entities.py` — Core Module

#### Constants

```python
_ENTITY_SCHEMA_VERSION = 1
VALID_ENTITY_TYPES = frozenset({"person", "department", "system", "process"})
_WIKILINK_UNSAFE_CHARS = set("[]|#^")
```

#### `EntityEntry` Dataclass

Single flat dataclass with optional type-specific fields (same pattern as
`RegistryEntry` which puts all fields in one class):

```python
@dataclass
class EntityEntry:
    # Common fields (all types)
    canonical_name: str
    type: str                                    # person|department|system|process
    aliases: list[str] = field(default_factory=list)
    needs_confirmation: bool = False
    source: str = "import"                       # import|extracted|manual
    first_seen: str = ""                         # ISO 8601, never overwritten
    created_at: str = ""                         # ISO 8601
    updated_at: str = ""                         # ISO 8601
    proposed_match: Optional[str] = None         # entity key, PR B populates
    # Person-specific
    title: Optional[str] = None
    department: Optional[str] = None             # → department entity key
    reports_to: Optional[str] = None             # → person entity key
    client: Optional[str] = None
    # Department-specific
    head: Optional[str] = None                   # → person entity key
    # System/Process-specific
    owner_dept: Optional[str] = None             # → department entity key
    status: Optional[str] = None
```

**`to_dict()`**: Exclude `None` fields. Preserve empty `aliases` list (same
semantics as `RegistryEntry.to_dict()` preserving empty review fields).

**`entity_from_dict(d: dict) -> EntityEntry`**: Standalone function. Filter
unknown keys via `EntityEntry.__dataclass_fields__` for forward compatibility.

#### `slugify(name: str) -> str`

Derive entity key from canonical name:
- Lowercase
- Replace runs of non-alphanumeric characters with `_`
- Strip leading/trailing underscores

```
"Jane Smith"       → "jane_smith"
"SAP ERP"          → "sap_erp"
"Incident Triage"  → "incident_triage"
"Jane  Smith"      → "jane_smith"  (same as "Jane Smith" — collision!)
```

#### `sanitize_wikilink_name(name: str) -> str`

Strip characters `[]|#^` and leading/trailing whitespace from entity names
before storage or wikilink rendering.

#### Exceptions

```python
class EntityRegistryError(Exception): ...
class EntitySlugCollisionError(EntityRegistryError): ...
class EntityAliasCollisionError(EntityRegistryError): ...
class EntityAmbiguousError(EntityRegistryError): ...
class EntitySchemaVersionError(EntityRegistryError): ...
```

#### `EntityRegistry` Class

Stateful class — loads into memory, provides queries, saves atomically. This
is different from `registry.py` which uses module-level functions, but the
entity system has richer query semantics (alias lookup, confirmed-only filter)
that benefit from a class.

```python
class EntityRegistry:
    def __init__(self, registry_path: Path):
        self._path = registry_path
        self._data: dict = _empty_entity_registry()
        self._loaded = False
```

**`load()`**: Read `entities.json`. Handle:
- Missing file → initialize empty registry, set `_loaded = True`
- JSON parse error → raise `EntityRegistryError` with diagnostic message
  (spec §7.9: do not auto-repair, suggest user fix or restore from VCS)
- `_schema_version` > current → raise `EntitySchemaVersionError`
- `_schema_version` < current → apply forward migrations (v1 is only version)
- Invalid entries (missing `canonical_name` or `type`) → log warning per entry,
  skip invalid, load valid

**`save()`**: Set `updated_at`, call `_atomic_write_json(self._path, self._data)`.

**`add_entity(entry: EntityEntry) -> str`**: Returns entity key.
- Derive slug from `canonical_name` via `slugify()`
- Check slug collision within `entry.type` namespace → raise `EntitySlugCollisionError`
- Check alias collision: each alias checked against all canonical names and
  aliases in the same type namespace → raise `EntityAliasCollisionError`
- Sanitize `canonical_name` and each alias via `sanitize_wikilink_name()`
- Set `created_at`, `updated_at`, `first_seen` to current UTC ISO timestamp
- Store in `self._data["entities"][entry.type][slug]`

**`update_entity(entity_type: str, key: str, updates: dict, preserve_existing: bool = False) -> bool`**:
- If `preserve_existing=True`: only fill `None`/absent fields (import merge)
- If `preserve_existing=False`: overwrite fields
- Never overwrite `first_seen`
- Always update `updated_at`
- Returns `True` if any field changed

**`remove_entity(entity_type: str, key: str) -> Optional[EntityEntry]`**:
Remove and return, or `None` if not found.

**`get_entity(entity_type: str, key: str) -> Optional[EntityEntry]`**:
Get by exact type + key.

**`lookup(name: str, entity_type: Optional[str] = None, confirmed_only: bool = False) -> list[tuple[str, str, EntityEntry]]`**:
- Case-insensitive match against canonical names and aliases
- If `entity_type` provided: search only that namespace (type-strict, D7)
- If `entity_type` is `None`: search all namespaces (used by CLI `show`/`confirm`/`reject`)
- If `confirmed_only=True`: skip entities where `needs_confirmation == True`
  (**This is the PR B seam** — resolution only matches confirmed entities)
- Returns list of `(entity_type, entity_key, EntityEntry)` tuples

**`lookup_unique(name, entity_type=None, confirmed_only=False) -> Optional[tuple]`**:
Like `lookup()` but returns single match or `None`. Raises `EntityAmbiguousError`
if multiple matches.

**`iter_entities(entity_type=None, unconfirmed_only=False)`**:
Yield `(type, key, EntityEntry)` tuples with optional filters.

**`count_by_type() -> dict[str, dict[str, int]]`**:
Returns `{"person": {"total": 5, "unconfirmed": 1}, ...}`

**`confirm_entity(entity_type: str, key: str) -> bool`**:
Set `needs_confirmation = False`, clear `proposed_match`. Returns `True` if changed.

**`entity_count() -> int`**, **`unconfirmed_count() -> int`**: Convenience totals.

**`_empty_entity_registry() -> dict`**: Module-level helper:
```python
def _empty_entity_registry() -> dict:
    return {
        "_schema_version": _ENTITY_SCHEMA_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "entities": {t: {} for t in VALID_ENTITY_TYPES},
    }
```

---

### 2. `folio/entity_import.py` — CSV Import

Place at package root (parallel to `ingest.py`): domain operation that calls
into the tracking layer.

#### `ImportResult` Dataclass

```python
@dataclass
class ImportResult:
    people_imported: int = 0
    people_updated: int = 0
    people_skipped: int = 0
    departments_created: int = 0
    warnings: list[str] = field(default_factory=list)
```

#### `import_csv(registry: EntityRegistry, csv_path: Path) -> ImportResult`

All-or-nothing at the file level (spec §9.7):

**Phase 0 — Parse CSV:**
1. Read file as bytes. Strip UTF-8 BOM (`\xef\xbb\xbf`) if present.
2. Decode as UTF-8. Raise on `UnicodeDecodeError`:
   `"Cannot read {path}: expected UTF-8 encoding."`
3. Parse with `csv.reader`. First row = headers.
4. Normalize headers: strip whitespace.
5. Require `name` column (case-insensitive header match). Raise if missing.
6. Warn on unrecognized columns (known: `name`, `title`, `department`,
   `reports_to`, `aliases`, `client`).
7. Parse all rows. Pad short rows (warn), truncate long rows (warn).
   On `csv.Error` (broken quoting): abort with error identifying line number.

**Phase 1 — Create/update person entities (no `reports_to` yet):**
- Iterate parsed rows. Track seen names (case-insensitive) for duplicate
  detection within CSV.
- For each row:
  - Skip empty `name` with warning.
  - Skip duplicate name within CSV with warning (first occurrence wins).
  - Sanitize canonical name via `sanitize_wikilink_name()`.
  - Check if entity exists in registry by slug:
    - Exists + confirmed: update null fields only (`preserve_existing=True`).
      Count as "updated" if changed, "skipped" if not.
    - Exists + unconfirmed: **upgrade** — set `source="import"`,
      `needs_confirmation=False`, fill in fields. Count as "updated".
    - Does not exist: create new entity. Count as "imported".
  - On alias collision (name matches existing alias): warn + skip row.
  - On slug collision (different name, same slug): warn + skip row.
  - Collect unique department values for auto-creation.
- Parse aliases from semicolon-delimited string. Sanitize each.

**Phase 2 — Auto-create department entities:**
- For each unique department value from CSV rows:
  - Skip if department entity already exists.
  - Create with `source="import"`, `needs_confirmation=False`.
  - On slug collision: warn.

**Phase 3 — Link person.department to department keys:**
- For each row with a department value, update the person entity's
  `department` field to the department entity key (slug).

**Phase 4 — Resolve `reports_to` (two-pass, spec §9.5):**
- For each row with a `reports_to` value:
  - Look up target person entity by slugified name.
  - If found: set `reports_to` to entity key.
  - If not found: store raw name as-is, warn.
- This pass runs AFTER all person entities are created (Phase 1), so
  row order in the CSV does not matter.

**Phase 5 — Save:**
- `registry.save()` — single atomic write.
- Return `ImportResult` with counts and warnings.

---

### 3. `folio/cli.py` — Entity Commands

#### `entities` Click Group

First nested group in the codebase. Use `invoke_without_command=True` so bare
`folio entities` runs the list view:

```python
@cli.group(invoke_without_command=True)
@click.option("--type", "entity_type",
              type=click.Choice(["person", "department", "system", "process"]),
              default=None, help="Filter by entity type.")
@click.option("--unconfirmed", is_flag=True, default=False,
              help="Show only unconfirmed entities.")
@click.option("--json", "json_output", is_flag=True, default=False,
              help="Output as JSON.")
@click.pass_context
def entities(ctx, entity_type, unconfirmed, json_output):
    """Manage entities in the library."""
    if ctx.invoked_subcommand is None:
        # Default: list entities
        _entities_list(ctx, entity_type, unconfirmed, json_output)
```

Place the group definition and all subcommands before the `main()` function
at the end of `cli.py`. Use lazy imports (`from .tracking.entities import ...`)
inside the command functions to avoid circular imports, consistent with how
`status` imports registry.

#### `_entities_list()` (default when no subcommand)

Load `EntityRegistry` from `library_root / "entities.json"`. If file doesn't
exist, print `"No entities in library."` and return. Otherwise:

- If `--json`: output `registry._data` as JSON via `json.dumps()`.
- Otherwise: group by type, show counts and confirmation status per spec §8.1.

#### `folio entities show <name>` (spec §8.2)

- `lookup()` with `entity_type` from `--type` flag (or `None` to search all).
- If multiple matches: list them, ask user to re-run with `--type`.
- If single match: show detail view.
- "Mentioned in" count: scan `library_root.rglob("*.md")` for
  `[[{canonical_name}]]` in file content. Count files, not occurrences.

#### `folio entities import <csv>` (spec §8.3)

- Delegate to `import_csv()` from `folio.entity_import`.
- Print summary from `ImportResult`.
- Print each warning with `⚠` prefix.

#### `folio entities confirm <name>` (spec §8.4)

- `lookup()` to find entity. Disambiguation via `--type`.
- If `needs_confirmation` is already `False`: print no-op message.
- Otherwise: `registry.confirm_entity()` + `registry.save()`.

#### `folio entities reject <name>` (spec §8.5)

- `lookup()` to find entity. Disambiguation via `--type`.
- If `needs_confirmation` is `False`: error — cannot reject confirmed entity.
- Otherwise: `registry.remove_entity()` + `registry.save()`.

#### `folio status` Integration (spec §12.1)

After line 673 of `cli.py` (after the `"Missing source"` line), add:

```python
entities_path = library_root / "entities.json"
if entities_path.exists():
    try:
        from .tracking.entities import EntityRegistry, EntityRegistryError
        ent_reg = EntityRegistry(entities_path)
        ent_reg.load()
        total_ent = ent_reg.entity_count()
        unconf = ent_reg.unconfirmed_count()
        if total_ent > 0:
            if unconf:
                click.echo(f"  Entities: {total_ent} ({unconf} unconfirmed)")
            else:
                click.echo(f"  Entities: {total_ent}")
    except Exception:
        click.echo("  ⚠ entities.json unreadable")
```

#### `folio/tracking/__init__.py`

Add one line:
```python
from . import entities  # noqa: F401
```

---

### 4. Test Fixtures

#### `tests/fixtures/test_org_chart.csv`

From spec §13.4:
```csv
name,title,department,reports_to,aliases
Alice Chen,CEO,Executive,,Alice;the CEO
Bob Martinez,CTO,Engineering,Alice Chen,Bob;the CTO
Carol Davis,VP Operations,Operations,Alice Chen,Carol
Diana Lee,Senior Engineer,Engineering,Bob Martinez,Diana
Eve Wilson,Analyst,Operations,Carol Davis,
```

#### `tests/fixtures/test_entities.json`

Pre-populated registry with the 5 people + 3 departments from above, all
confirmed. This fixture is created now for CLI tests and will also be used by
PR B resolution tests.

Generate this programmatically in a test helper or write it by hand as a JSON
file. All entries should have `needs_confirmation: false`, `source: "import"`,
and plausible timestamps.

---

### 5. Test Plan

All tests from spec §13.1 are **required**. The spec lists them in tables — use
those exact test names.

#### `tests/test_entities.py` (~22 tests)

Follow `test_registry.py` patterns. Create helpers:

```python
def _sample_entity(**overrides) -> EntityEntry:
    defaults = dict(
        canonical_name="Jane Smith",
        type="person",
        aliases=[],
        needs_confirmation=False,
        source="import",
        # ... timestamps
    )
    defaults.update(overrides)
    return EntityEntry(**defaults)
```

**Tests from spec §13.1 unit tests table:**
- `test_empty_registry_creation`
- `test_entity_key_derivation`
- `test_slug_collision_rejected`
- `test_slug_collision_across_types_allowed`
- `test_add_entity_basic`
- `test_add_entity_with_aliases`
- `test_add_entity_duplicate_key`
- `test_alias_collision_detection`
- `test_lookup_exact_match`
- `test_lookup_alias_match`
- `test_lookup_case_insensitive`
- `test_lookup_confirmed_only`
- `test_lookup_no_match`
- `test_lookup_ambiguous_within_type`
- `test_first_seen_preserved_on_update`
- `test_wikilink_sanitization`

**Tests from spec §13.1 durability tests table:**
- `test_atomic_write`
- `test_corrupt_json_error`
- `test_invalid_entry_skipped`
- `test_schema_version_migration`
- `test_schema_version_too_new`
- `test_read_only_fallback`

#### `tests/test_entity_import.py` (~21 tests)

**Tests from spec §13.1 import tests table:**
- `test_import_minimal_csv`
- `test_import_full_csv`
- `test_import_department_auto_creation`
- `test_import_reports_to_resolution`
- `test_import_reports_to_unresolved`
- `test_import_reports_to_order_independent`
- `test_import_duplicate_skip`
- `test_import_duplicate_update`
- `test_import_upgrades_extracted_entity`
- `test_import_alias_collision_warning`
- `test_import_duplicate_rows`
- `test_import_aliases_semicolon_split`
- `test_import_empty_csv`
- `test_import_idempotent`
- `test_import_utf8_bom`
- `test_import_non_utf8_error`
- `test_import_malformed_row_warning`
- `test_import_unparseable_row_aborts`
- `test_import_unrecognized_columns_warning`
- `test_import_slug_collision_skips_row`
- `test_import_batch_rollback`

#### `tests/test_cli_entities.py` (~15 tests)

Use `CliRunner` pattern from `test_cli_tier2.py`. Create helpers for
`_make_config()` and `_make_entity_registry()`.

**Tests from spec §13.1 CLI tests table:**
- `test_entities_list_empty`
- `test_entities_list_grouped`
- `test_entities_list_type_filter`
- `test_entities_list_unconfirmed_filter`
- `test_entities_show_found`
- `test_entities_show_not_found`
- `test_entities_show_ambiguous`
- `test_entities_show_with_type_flag`
- `test_entities_confirm`
- `test_entities_confirm_already_confirmed`
- `test_entities_reject`
- `test_entities_reject_confirmed_error`
- `test_entities_import_success`
- `test_entities_import_file_not_found`
- `test_entities_json_output`

---

## Implementation Order

Implement in this sequence — each step depends on the previous:

1. **`folio/tracking/entities.py`** — EntityEntry + slugify + sanitize + exceptions
2. **`folio/tracking/entities.py`** — EntityRegistry load/save + schema + corruption recovery
3. **`folio/tracking/entities.py`** — CRUD + lookup + iteration + confirmation
4. **`folio/tracking/__init__.py`** — add `from . import entities`
5. **`tests/test_entities.py`** — all 22 tests. Run and verify.
6. **`tests/fixtures/test_org_chart.csv`** + **`tests/fixtures/test_entities.json`**
7. **`folio/entity_import.py`** — full import logic
8. **`tests/test_entity_import.py`** — all 21 tests. Run and verify.
9. **`folio/cli.py`** — entities group + 5 subcommands + status integration
10. **`tests/test_cli_entities.py`** — all 15 tests. Run and verify.

Commit after each logical unit (e.g., after step 5, after step 8, after step 10).

---

## Acceptance Criteria (spec §14, PR A)

Every item must be checked off before the PR is opened:

- [ ] `entities.json` created with `_schema_version: 1` on first entity write
- [ ] All four entity types supported: person, department, system, process
- [ ] Entity keys are deterministic slugs of canonical names
- [ ] Slug collisions rejected with clear error
- [ ] Aliases stored and used for lookup
- [ ] `folio entities` lists entities grouped by type with confirmation status
- [ ] `folio entities --type <t>` filters by type
- [ ] `folio entities --unconfirmed` filters to unconfirmed entities
- [ ] `folio entities show <name>` displays entity detail with disambiguation
- [ ] `folio entities import <csv>` imports people from org chart CSV
- [ ] Import handles UTF-8 BOM, warns on unrecognized columns, aborts on unparseable rows
- [ ] Two-pass import resolves `reports_to` independent of row order
- [ ] Import upgrades existing extracted entities to confirmed/import
- [ ] Department auto-creation from import
- [ ] Duplicate handling: skip unchanged, update new fields, warn on alias collision
- [ ] `folio entities confirm <name>` sets `needs_confirmation: false`
- [ ] `folio entities reject <name>` removes unconfirmed entities
- [ ] Atomic writes with corruption recovery behavior
- [ ] All PR A tests pass
- [ ] No regressions in existing CI test suite (1243 baseline)
- [ ] `folio status` shows entity count line when entities exist
- [ ] `registry.json` completely unmodified by any entity operation
- [ ] No changes to interaction pipeline files

## Smoke Tests

Run these manually after all tests pass:

```bash
folio entities                                           # → "No entities in library." or empty
folio entities import tests/fixtures/test_org_chart.csv  # → Imported 5 people, 3 departments
folio entities                                           # → grouped list with counts
folio entities show "Alice Chen"                         # → detail view with aliases
folio entities --unconfirmed                             # → empty (all imported = confirmed)
folio entities --json                                    # → valid JSON to stdout
folio status                                             # → includes "Entities: 8" line
```

---

## Standing Instructions for Developer Agents

- If the spec is unclear or you discover a gap, **stop and message the CA lead**.
  Do not improvise product decisions.
- Create branch `feature/v0.5.1-entity-registry` from `main` (if not already created).
- Commit after each logical unit. Format: `feat(entities): description`.
- Run `python3 -m pytest tests/ -v` after each commit.
- Do not add docstrings, comments, or type annotations to code you didn't write.
- Follow existing code style and patterns exactly.
