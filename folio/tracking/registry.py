"""Registry: fast library index backed by registry.json."""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml as yaml_lib

from .sources import check_staleness, compute_file_hash

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 1


@dataclass
class RegistryEntry:
    """A single deck in the registry."""
    id: str
    title: str
    markdown_path: str          # relative to library_root
    deck_dir: str               # relative to library_root
    source_relative_path: str   # frontmatter source field
    source_hash: str
    source_type: str
    version: int
    converted: str
    modified: Optional[str] = None
    client: Optional[str] = None
    engagement: Optional[str] = None
    authority: Optional[str] = None
    curation_level: Optional[str] = None
    staleness_status: str = "current"  # current | stale | missing

    def to_dict(self) -> dict:
        """Serialize to a dict suitable for JSON storage."""
        return {k: v for k, v in asdict(self).items() if v is not None}


def load_registry(registry_path: Path) -> dict:
    """Load registry from JSON file.

    Returns the full registry dict including ``_schema_version``,
    ``updated_at``, and ``decks``.  Returns a fresh empty registry
    if the file does not exist or is unreadable.
    """
    if not registry_path.exists():
        return _empty_registry()
    try:
        data = json.loads(registry_path.read_text())
        if not isinstance(data, dict):
            logger.warning("Registry is not a dict — marking corrupt")
            return _empty_registry(_corrupt=True)
        # Ensure decks key exists
        if "decks" not in data:
            data["decks"] = {}
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load registry: %s — marking corrupt", e)
        return _empty_registry(_corrupt=True)


def save_registry(registry_path: Path, data: dict) -> None:
    """Write registry atomically."""
    data.pop("_corrupt", None)  # internal flag, not persisted
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    data.setdefault("_schema_version", _SCHEMA_VERSION)
    _atomic_write_json(registry_path, data)


def upsert_entry(registry_path: Path, entry: RegistryEntry) -> None:
    """Add or update a registry entry."""
    data = load_registry(registry_path)
    data["decks"][entry.id] = entry.to_dict()
    save_registry(registry_path, data)


def remove_entry(registry_path: Path, deck_id: str) -> None:
    """Remove a registry entry by ID."""
    data = load_registry(registry_path)
    data["decks"].pop(deck_id, None)
    save_registry(registry_path, data)


def rebuild_registry(library_root: Path) -> dict:
    """Bootstrap a registry by walking existing markdown files.

    Scans ``library_root`` for Folio markdown files (ones with
    ``source`` and ``source_hash`` in YAML frontmatter) and creates
    a registry entry for each.
    """
    library_root = Path(library_root).resolve()
    data = _empty_registry()

    for md_file in sorted(library_root.rglob("*.md")):
        fm = _read_frontmatter(md_file)
        if fm is None:
            continue
        # Must have source tracking fields to be a Folio document
        if "source" not in fm or "source_hash" not in fm:
            continue

        deck_id = fm.get("id", md_file.stem)
        md_rel = str(md_file.relative_to(library_root)).replace("\\", "/")
        deck_dir_rel = str(md_file.parent.relative_to(library_root)).replace("\\", "/")
        if deck_dir_rel == ".":
            deck_dir_rel = ""

        # Compute staleness
        staleness = check_staleness(md_file, fm["source"], fm["source_hash"])

        entry = RegistryEntry(
            id=deck_id,
            title=fm.get("title", md_file.stem),
            markdown_path=md_rel,
            deck_dir=deck_dir_rel,
            source_relative_path=fm["source"],
            source_hash=fm["source_hash"],
            source_type=fm.get("source_type", "deck"),
            version=fm.get("version", 1),
            converted=fm.get("converted", ""),
            modified=fm.get("modified"),
            client=fm.get("client"),
            engagement=fm.get("engagement"),
            authority=fm.get("authority"),
            curation_level=fm.get("curation_level"),
            staleness_status=staleness["status"],
        )
        data["decks"][entry.id] = entry.to_dict()

    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    logger.info("Registry bootstrapped: %d entries", len(data["decks"]))
    return data


def reconcile_from_frontmatter(library_root: Path, data: dict) -> dict:
    """Reconcile registry entries against their actual markdown frontmatter.

    Updates registry fields that are frontmatter-authoritative
    (title, client, engagement, authority, curation_level) so the
    registry stays consistent after manual edits.
    """
    library_root = Path(library_root).resolve()
    changed = 0
    for deck_id, entry_data in list(data.get("decks", {}).items()):
        md_rel = entry_data.get("markdown_path", "")
        md_path = library_root / md_rel
        if not md_path.exists():
            continue
        fm = _read_frontmatter(md_path)
        if fm is None:
            continue
        # Reconcile frontmatter-authoritative fields
        authoritative = [
            "title", "client", "engagement", "authority", "curation_level",
        ]
        for field_name in authoritative:
            fm_val = fm.get(field_name)
            reg_val = entry_data.get(field_name)
            if fm_val is not None and fm_val != reg_val:
                entry_data[field_name] = fm_val
                changed += 1
        # Also reconcile the ID if frontmatter has one
        fm_id = fm.get("id")
        if fm_id and fm_id != deck_id:
            data["decks"][fm_id] = entry_data
            entry_data["id"] = fm_id
            del data["decks"][deck_id]
            changed += 1
    if changed:
        logger.info("Registry reconciled: %d field(s) updated from frontmatter", changed)
    return data


def resolve_entry_source(library_root: Path, entry: RegistryEntry) -> Path:
    """Resolve the absolute source path for a registry entry."""
    library_root = Path(library_root).resolve()
    md_path = library_root / entry.markdown_path
    md_dir = md_path.parent
    return (md_dir / entry.source_relative_path).resolve()


def refresh_entry_status(library_root: Path, entry: RegistryEntry) -> RegistryEntry:
    """Recompute staleness_status for a registry entry.

    Mutates ``entry.staleness_status`` in-place and returns the
    same entry for convenience.
    """
    library_root = Path(library_root).resolve()
    md_path = library_root / entry.markdown_path
    result = check_staleness(md_path, entry.source_relative_path, entry.source_hash)
    entry.staleness_status = result["status"]
    return entry


def entry_from_dict(d: dict) -> RegistryEntry:
    """Construct a RegistryEntry from a registry dict entry.

    Ignores unknown keys for forward compatibility.
    """
    known_fields = {f.name for f in RegistryEntry.__dataclass_fields__.values()}
    filtered = {k: v for k, v in d.items() if k in known_fields}
    return RegistryEntry(**filtered)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_registry(_corrupt: bool = False) -> dict:
    d = {
        "_schema_version": _SCHEMA_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "decks": {},
    }
    if _corrupt:
        d["_corrupt"] = True
    return d


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically: write to temp file, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2))
    tmp_path.rename(path)


def _read_frontmatter(md_path: Path) -> Optional[dict]:
    """Read YAML frontmatter from a markdown file.

    Returns None if the file has no valid frontmatter.
    """
    try:
        content = md_path.read_text()
        lines = content.split("\n")
        if not lines or lines[0].strip() != "---":
            return None
        end_idx = None
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end_idx = i
                break
        if end_idx is None:
            return None
        yaml_block = "\n".join(lines[1:end_idx])
        result = yaml_lib.safe_load(yaml_block)
        if not isinstance(result, dict):
            return None
        return result
    except (yaml_lib.YAMLError, OSError):
        return None
