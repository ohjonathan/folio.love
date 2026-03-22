"""CSV import for entity registry."""

import csv
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .tracking.entities import (
    EntityEntry,
    EntityRegistry,
    EntityAliasCollisionError,
    EntitySlugCollisionError,
    sanitize_wikilink_name,
    slugify,
)

logger = logging.getLogger(__name__)

_KNOWN_COLUMNS = frozenset({"name", "title", "department", "reports_to", "aliases", "client"})


@dataclass
class ImportResult:
    """Summary of a CSV import operation."""

    people_imported: int = 0
    people_updated: int = 0
    people_skipped: int = 0
    departments_created: int = 0
    warnings: list[str] = field(default_factory=list)


def import_csv(registry: EntityRegistry, csv_path: Path) -> ImportResult:
    """Import entities from a CSV org chart file.

    All-or-nothing at the file level: the entire CSV is parsed and validated
    before any writes to entities.json.
    """
    result = ImportResult()

    # Phase 0: Parse CSV
    raw_bytes = csv_path.read_bytes()

    # Strip UTF-8 BOM
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raw_bytes = raw_bytes[3:]

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(f"Cannot read {csv_path}: expected UTF-8 encoding.")

    try:
        reader = csv.reader(io.StringIO(text))
        rows_raw = list(reader)
    except csv.Error as e:
        raise ValueError(f"Cannot parse {csv_path}: {e}")

    if not rows_raw:
        result.warnings.append("CSV file is empty.")
        return result

    # Normalize headers
    headers = [h.strip().lower() for h in rows_raw[0]]

    if "name" not in headers:
        raise ValueError(
            f"Missing required 'name' column in {csv_path}. "
            f"Found columns: {', '.join(headers)}"
        )

    # Warn on unrecognized columns
    for h in headers:
        if h and h not in _KNOWN_COLUMNS:
            result.warnings.append(f"Unrecognized column '{h}' (ignored).")

    # Parse data rows
    parsed_rows: list[dict[str, str]] = []
    for row_idx, row in enumerate(rows_raw[1:], start=2):
        if len(row) < len(headers):
            # Pad short rows
            row = row + [""] * (len(headers) - len(row))
            result.warnings.append(f"Row {row_idx}: fewer columns than headers, padded with empty values.")
        elif len(row) > len(headers):
            # Truncate long rows
            result.warnings.append(f"Row {row_idx}: more columns than headers, extra columns ignored.")
            row = row[:len(headers)]

        row_dict = {}
        for i, h in enumerate(headers):
            val = row[i].strip() if row[i] else ""
            if val:
                row_dict[h] = val
        parsed_rows.append(row_dict)

    # Track seen names for duplicate detection within CSV
    seen_names: dict[str, int] = {}  # lower name → first row index
    # Track departments to auto-create
    departments_to_create: set[str] = set()

    # Phase 1: Create/update person entities
    for row_idx, row in enumerate(parsed_rows, start=2):
        name = row.get("name", "").strip()
        if not name:
            result.warnings.append(f"Row {row_idx}: empty name, skipped.")
            continue

        name = sanitize_wikilink_name(name)
        name_lower = name.lower()

        # Duplicate within CSV
        if name_lower in seen_names:
            result.warnings.append(
                f"Row {row_idx}: duplicate name '{name}' "
                f"(first seen row {seen_names[name_lower]}), skipped."
            )
            continue
        seen_names[name_lower] = row_idx

        # Parse aliases
        aliases_raw = row.get("aliases", "")
        aliases = [
            sanitize_wikilink_name(a.strip())
            for a in aliases_raw.split(";")
            if a.strip()
        ] if aliases_raw else []

        slug = slugify(name)
        existing = registry.get_entity("person", slug)

        if existing is not None:
            if existing.needs_confirmation:
                # Upgrade: extracted → import, confirm
                updates = {
                    "source": "import",
                    "needs_confirmation": False,
                }
                if row.get("title"):
                    updates["title"] = row["title"]
                if row.get("client"):
                    updates["client"] = row["client"]
                if aliases:
                    updates["aliases"] = aliases
                registry.update_entity("person", slug, updates)
                result.people_updated += 1
            else:
                # Confirmed: update null fields only
                updates = {}
                if row.get("title"):
                    updates["title"] = row["title"]
                if row.get("client"):
                    updates["client"] = row["client"]
                if aliases:
                    updates["aliases"] = aliases
                changed = registry.update_entity(
                    "person", slug, updates, preserve_existing=True
                )
                if changed:
                    result.people_updated += 1
                else:
                    result.people_skipped += 1
        else:
            # New entity
            entry = EntityEntry(
                canonical_name=name,
                type="person",
                aliases=aliases,
                needs_confirmation=False,
                source="import",
            )
            if row.get("title"):
                entry.title = row["title"]
            if row.get("client"):
                entry.client = row["client"]

            try:
                registry.add_entity(entry)
                result.people_imported += 1
            except EntitySlugCollisionError:
                result.warnings.append(
                    f"Row {row_idx}: slug collision for '{name}', skipped."
                )
                continue
            except EntityAliasCollisionError as e:
                result.warnings.append(
                    f"Row {row_idx}: {e}, skipped."
                )
                continue

        # Track department for auto-creation
        dept = row.get("department", "").strip()
        if dept:
            departments_to_create.add(dept)

    # Phase 2: Auto-create department entities
    for dept_name in sorted(departments_to_create):
        dept_name = sanitize_wikilink_name(dept_name)
        dept_slug = slugify(dept_name)
        if registry.get_entity("department", dept_slug) is not None:
            continue  # already exists

        dept_entry = EntityEntry(
            canonical_name=dept_name,
            type="department",
            needs_confirmation=False,
            source="import",
        )
        try:
            registry.add_entity(dept_entry)
            result.departments_created += 1
        except EntitySlugCollisionError:
            result.warnings.append(
                f"Department slug collision for '{dept_name}', skipped."
            )

    # Phase 3: Link person.department to department keys
    for row in parsed_rows:
        name = row.get("name", "").strip()
        dept = row.get("department", "").strip()
        if not name or not dept:
            continue
        name = sanitize_wikilink_name(name)
        person_slug = slugify(name)
        dept_slug = slugify(sanitize_wikilink_name(dept))
        registry.update_entity("person", person_slug, {"department": dept_slug})

    # Phase 4: Resolve reports_to (two-pass)
    for row in parsed_rows:
        name = row.get("name", "").strip()
        reports_to = row.get("reports_to", "").strip()
        if not name or not reports_to:
            continue
        name = sanitize_wikilink_name(name)
        person_slug = slugify(name)
        target_slug = slugify(sanitize_wikilink_name(reports_to))

        # S3: Reject self-referencing reports_to
        if target_slug == person_slug:
            result.warnings.append(
                f"'{name}' reports_to self — ignored."
            )
            continue

        target = registry.get_entity("person", target_slug)
        if target is not None:
            registry.update_entity("person", person_slug, {"reports_to": target_slug})
        else:
            registry.update_entity("person", person_slug, {"reports_to": reports_to})
            result.warnings.append(
                f"reports_to '{reports_to}' for '{name}' not found in registry."
            )

    # Phase 5: Save
    registry.save()

    return result
