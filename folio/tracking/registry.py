"""Registry: fast library index backed by registry.json."""

import fcntl
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml as yaml_lib

from .sources import check_staleness, compute_file_hash

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 2


def _str_or_none(value: object) -> str | None:
    """Cast a value to ``str`` if non-None.

    YAML parsers auto-coerce bare dates like ``2026-03-30`` to
    ``datetime.date`` objects.  ``json.dumps`` cannot serialise those,
    so all rebuilt frontmatter strings pass through this helper.
    """
    if value is None:
        return None
    return str(value)


@dataclass
class RegistryEntry:
    """A single managed document in the registry.

    Schema v2 generalizes the registry to support source-less managed
    documents (e.g. context docs).  Source-backed fields are optional;
    source-less rows leave them as ``None``.
    """
    id: str
    title: str
    markdown_path: str          # relative to library_root
    deck_dir: str               # relative to library_root
    source_relative_path: Optional[str] = None   # None for source-less docs
    source_hash: Optional[str] = None             # None for source-less docs
    version: Optional[int] = None                 # None for source-less docs
    converted: Optional[str] = None               # None for source-less docs
    source_type: Optional[str] = None
    type: Optional[str] = None
    subtype: Optional[str] = None                 # round-trip context subtypes
    modified: Optional[str] = None
    client: Optional[str] = None
    engagement: Optional[str] = None
    authority: Optional[str] = None
    curation_level: Optional[str] = None
    staleness_status: str = "current"  # current | stale | missing
    # FR-700 reviewability
    review_status: Optional[str] = None
    review_flags: Optional[list[str]] = field(default=None)
    extraction_confidence: Optional[float] = None
    grounding_summary: Optional[dict] = field(default=None)

    def to_dict(self) -> dict:
        """Serialize to a dict suitable for JSON storage.

        Review field semantics:
        - ``None`` means the field has not been computed (legacy doc or LLM failure).
        - ``[]`` / ``{}`` means the field was computed and is clean (no issues).
        We preserve empty list/dict so downstream consumers can distinguish
        "not computed" from "computed, clean".
        """
        d = {k: v for k, v in asdict(self).items() if v is not None}
        # Preserve empty list / dict for review fields (FR-700)
        if self.review_flags is not None:
            d["review_flags"] = self.review_flags
        if self.grounding_summary is not None:
            d["grounding_summary"] = self.grounding_summary
        return d


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
        # Ensure decks key exists and is a dict
        if "decks" not in data:
            data["decks"] = {}
        if not isinstance(data["decks"], dict):
            logger.warning("Registry 'decks' is not a dict — marking corrupt")
            return _empty_registry(_corrupt=True)
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load registry: %s — marking corrupt", e)
        return _empty_registry(_corrupt=True)


def save_registry(registry_path: Path, data: dict) -> None:
    """Write registry atomically."""
    data.pop("_corrupt", None)  # internal flag, not persisted
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["_schema_version"] = _SCHEMA_VERSION
    _atomic_write_json(registry_path, data)


def upsert_entry(registry_path: Path, entry: RegistryEntry) -> None:
    """Add or update a registry entry."""
    data = load_registry(registry_path)
    # M1: rebuild on corrupt to avoid clobbering the full index
    if data.get("_corrupt"):
        library_root = registry_path.parent
        data = rebuild_registry(library_root)
    data["decks"][entry.id] = entry.to_dict()
    save_registry(registry_path, data)


def remove_entry(registry_path: Path, deck_id: str) -> None:
    """Remove a registry entry by ID."""
    data = load_registry(registry_path)
    data["decks"].pop(deck_id, None)
    save_registry(registry_path, data)


def rebuild_registry(library_root: Path) -> dict:
    """Bootstrap a registry by walking existing markdown files.

    Scans ``library_root`` for Folio markdown files and creates a registry
    entry for each note carrying either:
    - ``source`` + ``source_hash`` (evidence-style docs)
    - ``source_transcript`` + ``source_hash`` (interaction docs)
    - ``type: context`` (source-less managed docs)
    """
    library_root = Path(library_root).resolve()
    data = _empty_registry()

    for md_file in sorted(library_root.rglob("*.md")):
        fm = _read_frontmatter(md_file)
        if fm is None:
            continue

        # Context docs: source-less managed documents
        if fm.get("type") == "context":
            deck_id = fm.get("id", md_file.stem)
            md_rel = str(md_file.relative_to(library_root)).replace("\\", "/")
            deck_dir_rel = str(md_file.parent.relative_to(library_root)).replace("\\", "/")
            if deck_dir_rel == ".":
                deck_dir_rel = ""
            entry = RegistryEntry(
                id=deck_id,
                title=str(fm.get("title", md_file.stem)),
                markdown_path=md_rel,
                deck_dir=deck_dir_rel,
                type="context",
                subtype=_str_or_none(fm.get("subtype")),
                modified=_str_or_none(fm.get("modified")),
                client=_str_or_none(fm.get("client")),
                engagement=_str_or_none(fm.get("engagement")),
                authority=_str_or_none(fm.get("authority")),
                curation_level=_str_or_none(fm.get("curation_level")),
                staleness_status="current",
                review_status=fm.get("review_status"),
                review_flags=fm.get("review_flags"),
                extraction_confidence=fm.get("extraction_confidence"),
            )
            data["decks"][entry.id] = entry.to_dict()
            continue

        source_field = None
        if "source" in fm:
            source_field = "source"
        elif "source_transcript" in fm:
            source_field = "source_transcript"

        # Must have a supported source tracking field to be a Folio document
        if source_field is None or "source_hash" not in fm:
            continue

        deck_id = fm.get("id", md_file.stem)
        md_rel = str(md_file.relative_to(library_root)).replace("\\", "/")
        deck_dir_rel = str(md_file.parent.relative_to(library_root)).replace("\\", "/")
        if deck_dir_rel == ".":
            deck_dir_rel = ""

        # Compute staleness
        staleness = check_staleness(md_file, fm[source_field], fm["source_hash"])

        entry = RegistryEntry(
            id=deck_id,
            title=fm.get("title", md_file.stem),
            markdown_path=md_rel,
            deck_dir=deck_dir_rel,
            source_relative_path=fm[source_field],
            source_hash=fm["source_hash"],
            source_type=fm.get("source_type"),
            version=fm.get("version", 1),
            converted=fm.get("converted", ""),
            type=fm.get("type", "evidence"),
            subtype=fm.get("subtype"),
            modified=fm.get("modified"),
            client=fm.get("client"),
            engagement=fm.get("engagement"),
            authority=fm.get("authority"),
            curation_level=fm.get("curation_level"),
            staleness_status=staleness["status"],
            review_status=fm.get("review_status"),
            review_flags=fm.get("review_flags"),
            extraction_confidence=fm.get("extraction_confidence"),
            grounding_summary=fm.get("grounding_summary"),
        )
        data["decks"][entry.id] = entry.to_dict()

    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    logger.info("Registry bootstrapped: %d entries", len(data["decks"]))
    return data


def reconcile_from_frontmatter(library_root: Path, data: dict) -> dict:
    """Reconcile registry entries against their actual markdown frontmatter.

    Updates registry fields that are frontmatter-authoritative
    (title, type, client, engagement, authority, curation_level,
    review_status, review_flags) so the registry stays consistent
    after manual edits.
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
        # review_status and review_flags are frontmatter-authoritative so
        # manual edits (e.g. setting review_status: reviewed) are respected.
        #
        # NOT reconciled (converter-authoritative, recomputed on each conversion):
        # - extraction_confidence: derived from evidence by assess_review_state()
        # - grounding_summary: derived from evidence by _compute_grounding_summary()
        # These are intentionally excluded; the registry retains the last-computed
        # values and frontmatter is the source of truth only after re-conversion.
        authoritative = [
            "title", "type", "subtype", "client", "engagement", "authority",
            "curation_level", "review_status", "review_flags",
        ]
        for field_name in authoritative:
            if field_name in fm:
                fm_val = fm[field_name]
                reg_val = entry_data.get(field_name)
                if fm_val != reg_val:
                    entry_data[field_name] = fm_val
                    changed += 1
            else:
                # Key absent from frontmatter = explicit deletion
                if entry_data.get(field_name) is not None:
                    entry_data[field_name] = None
                    changed += 1
        source_field = None
        if "source_transcript" in fm:
            source_field = "source_transcript"
        elif "source" in fm:
            source_field = "source"
        if source_field is not None:
            source_val = fm.get(source_field)
            if source_val != entry_data.get("source_relative_path"):
                entry_data["source_relative_path"] = source_val
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
    """Resolve the absolute source path for a source-backed registry entry.

    Raises ``ValueError`` for source-less entries (e.g. context docs).
    Callers must check ``entry.source_relative_path is not None`` first.
    """
    if entry.source_relative_path is None:
        raise ValueError(f"Entry {entry.id} has no source path (source-less document)")
    library_root = Path(library_root).resolve()
    md_path = library_root / entry.markdown_path
    md_dir = md_path.parent
    return (md_dir / entry.source_relative_path).resolve()


def refresh_entry_status(library_root: Path, entry: RegistryEntry) -> RegistryEntry:
    """Recompute staleness_status for a registry entry.

    Source-less managed docs use file-presence-only staleness.
    Source-backed entries use source-hash comparison.
    Mutates ``entry.staleness_status`` in-place and returns the
    same entry for convenience.
    """
    library_root = Path(library_root).resolve()
    md_path = library_root / entry.markdown_path

    # Source-less managed docs: file-presence-only staleness
    if entry.source_relative_path is None:
        entry.staleness_status = "current" if md_path.exists() else "missing"
        return entry

    result = check_staleness(md_path, entry.source_relative_path, entry.source_hash)
    entry.staleness_status = result["status"]
    return entry


def entry_from_dict(d: dict) -> RegistryEntry:
    """Construct a RegistryEntry from a registry dict entry.

    Ignores unknown keys for forward compatibility.
    Schema v1 rows (missing subtype, optional source fields) are
    loaded transparently thanks to dataclass defaults.
    """
    known_fields = {f.name for f in RegistryEntry.__dataclass_fields__.values()}
    filtered = {k: v for k, v in d.items() if k in known_fields}
    if "type" not in filtered:
        filtered["type"] = _infer_missing_entry_type(d)
    return RegistryEntry(**filtered)


def _infer_missing_entry_type(d: dict) -> str:
    """Infer a missing registry entry type from the stored row shape."""
    if d.get("source_transcript"):
        return "interaction"
    if _looks_like_legacy_interaction_entry(d):
        return "interaction"
    return "evidence"


def _looks_like_legacy_interaction_entry(d: dict) -> bool:
    """Return True when the stored row shape looks like a legacy interaction."""
    source_type = d.get("source_type")
    if source_type is not None:
        return False

    for field_name in ("markdown_path", "deck_dir"):
        if _path_has_segment(d.get(field_name), "interactions"):
            return True

    source_relative_path = d.get("source_relative_path")
    if isinstance(source_relative_path, str):
        path = Path(source_relative_path)
        lowered_parts = {part.lower() for part in path.parts}
        if "transcript" in lowered_parts or "transcripts" in lowered_parts:
            return True

    return False


def _path_has_segment(value: object, segment: str) -> bool:
    if not isinstance(value, str) or not value:
        return False
    return segment.lower() in {part.lower() for part in Path(value).parts}


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
    """Write JSON atomically with file locking.

    Uses an advisory lock (``.lock`` file) to prevent concurrent writers
    from racing, and cleans up the temp file on write failures
    (disk-full, read-only filesystem, etc.).
    """
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
            # Clean up orphan temp file on disk-full / read-only
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
        # If we can't even open the lock file, try without locking
        # (better than crashing, and the atomic rename still helps)
        if 'lock_fd' not in dir():
            raise


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
