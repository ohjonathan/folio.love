"""CSV import for entity registry."""

import csv
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .tracking.entities import (
    EntityAliasCollisionError,
    EntityEntry,
    EntityRegistry,
    EntitySlugCollisionError,
    canonicalize_person_import_name,
    lookup_person_matches,
    normalize_entity_name,
    person_name_variants,
    slugify,
)

logger = logging.getLogger(__name__)

_KNOWN_COLUMNS = frozenset(
    {"name", "title", "level", "org_level", "department", "reports_to", "aliases", "client"}
)


@dataclass
class ImportResult:
    """Summary of a CSV import operation."""

    people_imported: int = 0
    people_updated: int = 0
    people_skipped: int = 0
    departments_created: int = 0
    org_chart_detected: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _PreparedRow:
    row_idx: int
    raw_name: str
    canonical_name: str
    explicit_aliases: list[str]
    implicit_aliases: list[str]
    row: dict[str, str]


def import_csv(registry: EntityRegistry, csv_path: Path) -> ImportResult:
    """Import entities from a CSV org chart file.

    All-or-nothing at the file level: the entire CSV is parsed and validated
    before any writes to entities.json.
    """
    result = ImportResult()

    raw_bytes = csv_path.read_bytes()
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raw_bytes = raw_bytes[3:]

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(f"Cannot read {csv_path}: expected UTF-8 encoding.")

    rows_raw: list[list[str]] = []
    try:
        reader = csv.reader(io.StringIO(text), strict=True)
        for row in reader:
            rows_raw.append(row)
    except csv.Error as e:
        raise ValueError(
            f"Cannot parse {csv_path} at line {reader.line_num}: {e}"
        )

    if not rows_raw:
        result.warnings.append("CSV file is empty.")
        return result

    headers = [h.strip().lower() for h in rows_raw[0]]
    if "name" not in headers:
        raise ValueError(
            f"Missing required 'name' column in {csv_path}. "
            f"Found columns: {', '.join(headers)}"
        )

    result.org_chart_detected = _detect_org_chart_headers(headers)

    for h in headers:
        if h and h not in _KNOWN_COLUMNS:
            result.warnings.append(f"Unrecognized column '{h}' (ignored).")

    parsed_rows: list[dict[str, str]] = []
    for row_idx, row in enumerate(rows_raw[1:], start=2):
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))
            result.warnings.append(
                f"Row {row_idx}: fewer columns than headers, padded with empty values."
            )
        elif len(row) > len(headers):
            result.warnings.append(
                f"Row {row_idx}: more columns than headers, extra columns ignored."
            )
            row = row[:len(headers)]

        row_dict: dict[str, str] = {}
        for i, header in enumerate(headers):
            val = row[i].strip() if row[i] else ""
            if val:
                row_dict["level" if header == "org_level" else header] = val
        parsed_rows.append(row_dict)

    prepared_rows = _prepare_rows(parsed_rows, result)
    departments_to_create: set[str] = set()
    person_keys: dict[int, str] = {}
    row_status: dict[int, str] = {}

    for prepared in prepared_rows:
        key, status = _create_or_update_person(
            registry=registry,
            prepared=prepared,
            result=result,
            authoritative=result.org_chart_detected,
        )
        if key is None:
            continue
        person_keys[prepared.row_idx] = key
        row_status[prepared.row_idx] = status

        department = prepared.row.get("department", "")
        if department:
            departments_to_create.add(department)

    _create_departments(registry, departments_to_create, result)
    dept_changed = _link_departments(registry, prepared_rows, person_keys)

    if result.org_chart_detected:
        reports_changed = _link_reports_to(registry, prepared_rows, person_keys, result)
    else:
        reports_changed = set()

    for row_idx in dept_changed | reports_changed:
        if row_status.get(row_idx) != "unchanged":
            continue
        result.people_skipped -= 1
        result.people_updated += 1
        row_status[row_idx] = "updated"

    registry.save()
    return result


def _prepare_rows(parsed_rows: list[dict[str, str]], result: ImportResult) -> list[_PreparedRow]:
    prepared_rows: list[_PreparedRow] = []
    seen_candidates: dict[str, int] = {}

    for row_idx, row in enumerate(parsed_rows, start=2):
        raw_name = normalize_entity_name(row.get("name", ""))
        if not raw_name:
            result.warnings.append(f"Row {row_idx}: empty name, skipped.")
            continue

        canonical_name, implicit_aliases = canonicalize_person_import_name(raw_name)
        explicit_aliases = _parse_aliases(row.get("aliases", ""))

        first_seen_row = _find_duplicate_row(
            raw_name=raw_name,
            canonical_name=canonical_name,
            seen_candidates=seen_candidates,
        )
        if first_seen_row is not None:
            result.warnings.append(
                f"Row {row_idx}: duplicate name '{raw_name}' "
                f"(first seen row {first_seen_row}), skipped."
            )
            continue

        for candidate in _row_lookup_candidates(raw_name, canonical_name):
            seen_candidates[candidate.lower()] = row_idx

        prepared_rows.append(
            _PreparedRow(
                row_idx=row_idx,
                raw_name=raw_name,
                canonical_name=canonical_name,
                explicit_aliases=explicit_aliases,
                implicit_aliases=implicit_aliases,
                row=row,
            )
        )

    return prepared_rows


def _find_duplicate_row(
    *,
    raw_name: str,
    canonical_name: str,
    seen_candidates: dict[str, int],
) -> int | None:
    for candidate in _row_lookup_candidates(raw_name, canonical_name):
        first_seen = seen_candidates.get(candidate.lower())
        if first_seen is not None:
            return first_seen
    return None


def _row_lookup_candidates(raw_name: str, canonical_name: str) -> list[str]:
    candidates: list[str] = []
    for source in (raw_name, canonical_name):
        for candidate in person_name_variants(source):
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def _parse_aliases(raw_aliases: str) -> list[str]:
    aliases: list[str] = []
    for raw_alias in raw_aliases.split(";"):
        alias = normalize_entity_name(raw_alias)
        if alias and alias not in aliases:
            aliases.append(alias)
    return aliases


def _detect_org_chart_headers(headers: list[str]) -> bool:
    """Detect org-chart CSVs conservatively.

    A lone ``level`` column is too weak a signal because it would make the
    import authoritative and allow silent overwrites on generic people CSVs.
    Treat the file as an org chart only when it includes ``reports_to`` or a
    level-plus-department pair.
    """
    header_set = set(headers)
    has_level = "level" in header_set or "org_level" in header_set
    return "reports_to" in header_set or (has_level and "department" in header_set)


def _merge_aliases(*groups: list[str]) -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for alias in group:
            cleaned = normalize_entity_name(alias)
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            aliases.append(cleaned)
    return aliases


def _create_or_update_person(
    *,
    registry: EntityRegistry,
    prepared: _PreparedRow,
    result: ImportResult,
    authoritative: bool,
) -> tuple[Optional[str], str]:
    matches = lookup_person_matches(
        registry,
        prepared.raw_name,
        prepared.canonical_name,
        confirmed_only=False,
    )
    if len(matches) > 1:
        names = ", ".join(match[2].canonical_name for match in matches)
        result.warnings.append(
            f"Row {prepared.row_idx}: ambiguous match for '{prepared.raw_name}' "
            f"({names}), skipped."
        )
        return None, "skipped"

    if matches:
        _etype, key, existing = matches[0]
        updates = {}
        preserve_existing = not authoritative and not existing.needs_confirmation

        if existing.needs_confirmation:
            updates["source"] = "import"
            updates["needs_confirmation"] = False
        if prepared.row.get("title"):
            updates["title"] = prepared.row["title"]
        if prepared.row.get("client"):
            updates["client"] = prepared.row["client"]
        if authoritative and prepared.row.get("level"):
            updates["org_level"] = prepared.row["level"]
        merged_aliases = _merge_aliases(
            list(existing.aliases or []),
            prepared.explicit_aliases,
            prepared.implicit_aliases,
        )
        if merged_aliases != list(existing.aliases or []):
            updates["aliases"] = merged_aliases

        changed = registry.update_entity(
            "person",
            key,
            updates,
            preserve_existing=preserve_existing,
        )
        if changed:
            result.people_updated += 1
        else:
            result.people_skipped += 1
        return key, "updated" if changed else "unchanged"

    creation_aliases = _merge_aliases(
        prepared.explicit_aliases,
        prepared.implicit_aliases,
    )
    entry = EntityEntry(
        canonical_name=prepared.canonical_name,
        type="person",
        aliases=creation_aliases,
        needs_confirmation=False,
        source="import",
    )
    if prepared.row.get("title"):
        entry.title = prepared.row["title"]
    if prepared.row.get("client"):
        entry.client = prepared.row["client"]
    if authoritative and prepared.row.get("level"):
        entry.org_level = prepared.row["level"]

    try:
        key = registry.add_entity(entry)
        result.people_imported += 1
        return key, "created"
    except EntitySlugCollisionError:
        result.warnings.append(
            f"Row {prepared.row_idx}: slug collision for '{prepared.raw_name}', skipped."
        )
        return None, "skipped"
    except EntityAliasCollisionError as e:
        result.warnings.append(f"Row {prepared.row_idx}: {e}, skipped.")
        return None, "skipped"


def _create_departments(
    registry: EntityRegistry,
    departments_to_create: set[str],
    result: ImportResult,
) -> None:
    for dept_name in sorted(departments_to_create):
        normalized = normalize_entity_name(dept_name)
        if not normalized:
            continue
        dept_slug = slugify(normalized)
        if registry.get_entity("department", dept_slug) is not None:
            continue

        dept_entry = EntityEntry(
            canonical_name=normalized,
            type="department",
            needs_confirmation=False,
            source="import",
        )
        try:
            registry.add_entity(dept_entry)
            result.departments_created += 1
        except EntitySlugCollisionError:
            result.warnings.append(
                f"Department slug collision for '{normalized}', skipped."
            )


def _link_departments(
    registry: EntityRegistry,
    prepared_rows: list[_PreparedRow],
    person_keys: dict[int, str],
) -> set[int]:
    changed_rows: set[int] = set()
    for prepared in prepared_rows:
        person_key = person_keys.get(prepared.row_idx)
        department = normalize_entity_name(prepared.row.get("department", ""))
        if not person_key or not department:
            continue
        changed = registry.update_entity(
            "person",
            person_key,
            {"department": slugify(department)},
        )
        if changed:
            changed_rows.add(prepared.row_idx)
    return changed_rows


def _link_reports_to(
    registry: EntityRegistry,
    prepared_rows: list[_PreparedRow],
    person_keys: dict[int, str],
    result: ImportResult,
) -> set[int]:
    changed_rows: set[int] = set()
    for prepared in prepared_rows:
        person_key = person_keys.get(prepared.row_idx)
        reports_to = normalize_entity_name(prepared.row.get("reports_to", ""))
        if not person_key or not reports_to:
            continue

        manager_key = _resolve_or_create_manager(
            registry=registry,
            reports_to=reports_to,
            result=result,
        )
        if manager_key is None:
            continue
        if manager_key == person_key:
            result.warnings.append(
                f"'{prepared.raw_name}' reports_to self — ignored."
            )
            continue
        if _would_create_reports_to_cycle(registry, person_key, manager_key):
            manager_name = registry.resolve_key_to_name(manager_key, "person")
            result.warnings.append(
                f"'{prepared.raw_name}' reports_to '{manager_name}' would create a circular chain — ignored."
            )
            continue
        changed = registry.update_entity("person", person_key, {"reports_to": manager_key})
        if changed:
            changed_rows.add(prepared.row_idx)
    return changed_rows


def _resolve_or_create_manager(
    *,
    registry: EntityRegistry,
    reports_to: str,
    result: ImportResult,
) -> Optional[str]:
    matches = lookup_person_matches(
        registry,
        reports_to,
        confirmed_only=False,
    )
    if len(matches) > 1:
        names = ", ".join(match[2].canonical_name for match in matches)
        result.warnings.append(
            f"Ambiguous reports_to '{reports_to}' ({names}), ignored."
        )
        return None
    if matches:
        _etype, key, entry = matches[0]
        if entry.needs_confirmation:
            registry.update_entity(
                "person",
                key,
                {"source": "import", "needs_confirmation": False},
            )
        return key

    canonical_name, implicit_aliases = canonicalize_person_import_name(reports_to)
    entry = EntityEntry(
        canonical_name=canonical_name,
        type="person",
        aliases=implicit_aliases,
        needs_confirmation=False,
        source="import:chain-completed",
    )
    try:
        key = registry.add_entity(entry)
        result.people_imported += 1
        return key
    except (EntityAliasCollisionError, EntitySlugCollisionError) as exc:
        result.warnings.append(
            f"Could not auto-create reports_to '{reports_to}': {exc}"
        )
        return None


def _would_create_reports_to_cycle(
    registry: EntityRegistry,
    person_key: str,
    manager_key: str,
) -> bool:
    current_key = manager_key
    seen: set[str] = set()

    while current_key:
        if current_key == person_key:
            return True
        if current_key in seen:
            return True
        seen.add(current_key)
        current_entry = registry.get_entity("person", current_key)
        if current_entry is None or not current_entry.reports_to:
            return False
        current_key = current_entry.reports_to

    return False
