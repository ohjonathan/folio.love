"""Entity registry: canonical entity store backed by entities.json."""

import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .registry import _atomic_write_json as atomic_write_json

logger = logging.getLogger(__name__)

_ENTITY_SCHEMA_VERSION = 1
VALID_ENTITY_TYPES = frozenset({"person", "department", "system", "process"})
# Entity types that can be auto-extracted from interaction notes (PR B seam)
EXTRACTION_ENTITY_TYPES = frozenset({"person", "department"})
_WIKILINK_UNSAFE_CHARS = set("[]|#^")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class EntityRegistryError(Exception):
    """Base exception for entity registry operations."""


class EntitySlugCollisionError(EntityRegistryError):
    """Two distinct canonical names produce the same slug within a type."""


class EntityAliasCollisionError(EntityRegistryError):
    """An alias or name collides with an existing canonical name or alias."""


class EntityAmbiguousError(EntityRegistryError):
    """A lookup matched multiple entities."""


class EntitySchemaVersionError(EntityRegistryError):
    """Schema version is newer than supported."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    """Derive entity key from canonical name.

    NFC-normalizes, lowercases, replaces runs of non-alphanumeric
    characters with ``_``, strips leading/trailing underscores.
    """
    s = unicodedata.normalize("NFC", name)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def sanitize_wikilink_name(name: str) -> str:
    """Strip characters unsafe in Obsidian wikilinks and trim whitespace."""
    return "".join(c for c in name if c not in _WIKILINK_UNSAFE_CHARS).strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_entity_registry() -> dict:
    return {
        "_schema_version": _ENTITY_SCHEMA_VERSION,
        "updated_at": _now_iso(),
        "entities": {t: {} for t in VALID_ENTITY_TYPES},
    }


# ---------------------------------------------------------------------------
# EntityEntry dataclass
# ---------------------------------------------------------------------------

@dataclass
class EntityEntry:
    """A single entity in the registry."""

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

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage.

        Excludes ``None`` fields.  Preserves empty ``aliases`` list so
        downstream can distinguish "no aliases" from "not computed".
        """
        d = {k: v for k, v in asdict(self).items() if v is not None}
        # Always include aliases (even if empty list)
        if self.aliases is not None:
            d["aliases"] = self.aliases
        return d


def entity_from_dict(d: dict) -> EntityEntry:
    """Construct an EntityEntry from a dict, ignoring unknown keys."""
    known = {f.name for f in EntityEntry.__dataclass_fields__.values()}
    filtered = {k: v for k, v in d.items() if k in known}
    return EntityEntry(**filtered)


# ---------------------------------------------------------------------------
# EntityRegistry
# ---------------------------------------------------------------------------

class EntityRegistry:
    """In-memory entity registry backed by ``entities.json``."""

    def __init__(self, registry_path: Path):
        self._path = registry_path
        self._data: dict = _empty_entity_registry()
        self._loaded = False

    # -- Persistence --------------------------------------------------------

    def load(self) -> None:
        """Load entities.json.  Missing file → empty registry."""
        if not self._path.exists():
            self._data = _empty_entity_registry()
            self._loaded = True
            return

        try:
            raw = self._path.read_text()
        except OSError as e:
            raise EntityRegistryError(
                f"Cannot read {self._path}: {e}"
            ) from e

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise EntityRegistryError(
                f"Cannot parse {self._path}: {e}. "
                f"Fix the JSON syntax or restore from version control."
            ) from e

        if not isinstance(data, dict):
            raise EntityRegistryError(
                f"{self._path} is not a JSON object."
            )

        version = data.get("_schema_version", 1)
        if version > _ENTITY_SCHEMA_VERSION:
            raise EntitySchemaVersionError(
                f"entities.json schema version {version} is newer than "
                f"supported version {_ENTITY_SCHEMA_VERSION}. "
                f"Please upgrade folio."
            )

        # Ensure entities dict structure
        if "entities" not in data or not isinstance(data["entities"], dict):
            data["entities"] = {t: {} for t in VALID_ENTITY_TYPES}

        # Validate and load entries, skipping invalid ones
        for etype in VALID_ENTITY_TYPES:
            if etype not in data["entities"]:
                data["entities"][etype] = {}
                continue
            type_dict = data["entities"][etype]
            if not isinstance(type_dict, dict):
                logger.warning(
                    "Entity type '%s' is not a dict — resetting to empty", etype
                )
                data["entities"][etype] = {}
                continue
            invalid_keys = []
            for key, entry_data in type_dict.items():
                if not isinstance(entry_data, dict):
                    logger.warning(
                        "Skipping invalid entity entry '%s/%s': not a dict",
                        etype, key,
                    )
                    invalid_keys.append(key)
                    continue
                if "canonical_name" not in entry_data or "type" not in entry_data:
                    logger.warning(
                        "Skipping invalid entity entry '%s/%s': "
                        "missing canonical_name or type",
                        etype, key,
                    )
                    invalid_keys.append(key)
            for k in invalid_keys:
                del type_dict[k]

        self._data = data
        self._loaded = True

    def save(self) -> None:
        """Write entities.json atomically.

        Raises ``EntityRegistryError`` if ``load()`` was never called.
        """
        if not self._loaded:
            raise EntityRegistryError(
                "Cannot save without loading first — call load() to "
                "read existing data before writing."
            )
        self._data["updated_at"] = _now_iso()
        self._data.setdefault("_schema_version", _ENTITY_SCHEMA_VERSION)
        atomic_write_json(self._path, self._data)

    # -- CRUD ---------------------------------------------------------------

    def add_entity(self, entry: EntityEntry) -> str:
        """Add a new entity.  Returns entity key (slug).

        Raises ``EntitySlugCollisionError`` or ``EntityAliasCollisionError``
        on conflicts.
        """
        if entry.type not in VALID_ENTITY_TYPES:
            raise EntityRegistryError(
                f"Invalid entity type: {entry.type}"
            )

        # Sanitize names
        entry.canonical_name = sanitize_wikilink_name(entry.canonical_name)
        entry.aliases = [sanitize_wikilink_name(a) for a in entry.aliases]
        entry.aliases = [a for a in entry.aliases if a]  # drop empty after sanitize

        slug = slugify(entry.canonical_name)
        if not slug:
            raise EntityRegistryError(
                f"Cannot derive entity key from name: '{entry.canonical_name}'"
            )

        type_dict = self._data["entities"].setdefault(entry.type, {})

        # Check slug collision
        if slug in type_dict:
            existing = type_dict[slug]
            raise EntitySlugCollisionError(
                f"Slug collision: '{entry.canonical_name}' produces key "
                f"'{slug}' which already exists as "
                f"'{existing.get('canonical_name', slug)}' "
                f"in {entry.type} namespace."
            )

        # Check alias collisions within the same type namespace
        existing_names = set()
        existing_aliases = set()
        for _key, ed in type_dict.items():
            existing_names.add(ed.get("canonical_name", "").lower())
            for a in ed.get("aliases", []):
                existing_aliases.add(a.lower())

        # Check new canonical name against existing aliases
        if entry.canonical_name.lower() in existing_aliases:
            raise EntityAliasCollisionError(
                f"Name '{entry.canonical_name}' collides with an existing "
                f"alias in {entry.type} namespace."
            )

        # Check new aliases against existing canonical names and aliases
        for alias in entry.aliases:
            alias_lower = alias.lower()
            if alias_lower in existing_names or alias_lower in existing_aliases:
                raise EntityAliasCollisionError(
                    f"Alias '{alias}' collides with an existing name or alias "
                    f"in {entry.type} namespace."
                )

        # Set timestamps
        now = _now_iso()
        if not entry.first_seen:
            entry.first_seen = now
        if not entry.created_at:
            entry.created_at = now
        entry.updated_at = now

        type_dict[slug] = entry.to_dict()
        return slug

    def _check_alias_collisions(
        self, entity_type: str, exclude_key: str,
        new_aliases: list[str],
    ) -> list[str]:
        """Return list of colliding aliases (lowercased).

        Checks ``new_aliases`` against all canonical names and aliases
        in the type namespace except the entity with ``exclude_key``.
        """
        type_dict = self._data["entities"].get(entity_type, {})
        existing_names = set()
        existing_aliases = set()
        for k, ed in type_dict.items():
            if k == exclude_key:
                continue
            existing_names.add(ed.get("canonical_name", "").lower())
            for a in ed.get("aliases", []):
                existing_aliases.add(a.lower())
        collisions = []
        for a in new_aliases:
            al = a.lower()
            if al in existing_names or al in existing_aliases:
                collisions.append(a)
        return collisions

    def update_entity(
        self, entity_type: str, key: str, updates: dict,
        preserve_existing: bool = False,
    ) -> bool:
        """Update fields on an existing entity.

        If ``preserve_existing`` is True, only fill ``None``/absent fields.
        Never overwrites ``first_seen``.  Always updates ``updated_at``.
        Validates alias uniqueness before applying alias changes.
        Returns True if any field changed.
        """
        type_dict = self._data["entities"].get(entity_type, {})
        if key not in type_dict:
            return False

        entry = type_dict[key]
        changed = False

        for field_name, value in updates.items():
            if field_name == "first_seen":
                continue  # never overwrite
            if preserve_existing and entry.get(field_name) is not None:
                continue
            # Validate alias uniqueness
            if field_name == "aliases" and isinstance(value, list):
                collisions = self._check_alias_collisions(
                    entity_type, key, value
                )
                if collisions:
                    # Strip colliding aliases, keep the rest
                    value = [a for a in value if a not in collisions]
                    logger.warning(
                        "Dropped colliding aliases for '%s': %s",
                        entry.get("canonical_name", key),
                        ", ".join(collisions),
                    )
            if entry.get(field_name) != value:
                entry[field_name] = value
                changed = True

        if changed:
            entry["updated_at"] = _now_iso()

        return changed

    def remove_entity(
        self, entity_type: str, key: str,
    ) -> Optional[EntityEntry]:
        """Remove and return an entity, or None if not found."""
        type_dict = self._data["entities"].get(entity_type, {})
        entry_data = type_dict.pop(key, None)
        if entry_data is None:
            return None
        return entity_from_dict(entry_data)

    def get_entity(
        self, entity_type: str, key: str,
    ) -> Optional[EntityEntry]:
        """Get entity by exact type + key."""
        type_dict = self._data["entities"].get(entity_type, {})
        entry_data = type_dict.get(key)
        if entry_data is None:
            return None
        return entity_from_dict(entry_data)

    # -- Queries ------------------------------------------------------------

    def lookup(
        self, name: str,
        entity_type: Optional[str] = None,
        confirmed_only: bool = False,
    ) -> list[tuple[str, str, EntityEntry]]:
        """Case-insensitive lookup against canonical names and aliases.

        Returns list of ``(entity_type, entity_key, EntityEntry)`` tuples.
        """
        name_lower = name.strip().lower()
        results = []

        types_to_search = (
            [entity_type] if entity_type else VALID_ENTITY_TYPES
        )

        for etype in types_to_search:
            type_dict = self._data["entities"].get(etype, {})
            for key, entry_data in type_dict.items():
                if confirmed_only and entry_data.get("needs_confirmation"):
                    continue
                canonical = entry_data.get("canonical_name", "")
                aliases = entry_data.get("aliases", [])
                if (
                    canonical.lower() == name_lower
                    or any(a.lower() == name_lower for a in aliases)
                ):
                    results.append((etype, key, entity_from_dict(entry_data)))

        return results

    def lookup_unique(
        self, name: str,
        entity_type: Optional[str] = None,
        confirmed_only: bool = False,
    ) -> Optional[tuple[str, str, EntityEntry]]:
        """Like lookup() but returns single match or None.

        Raises ``EntityAmbiguousError`` if multiple matches.
        """
        matches = self.lookup(name, entity_type, confirmed_only)
        if len(matches) == 0:
            return None
        if len(matches) == 1:
            return matches[0]
        desc = "; ".join(
            f"{m[2].canonical_name} ({m[0]})" for m in matches
        )
        raise EntityAmbiguousError(
            f"Multiple matches for '{name}': {desc}. "
            f"Use --type to disambiguate."
        )

    def iter_entities(
        self, entity_type: Optional[str] = None,
        unconfirmed_only: bool = False,
    ):
        """Yield ``(type, key, EntityEntry)`` tuples."""
        types = [entity_type] if entity_type else VALID_ENTITY_TYPES
        for etype in types:
            type_dict = self._data["entities"].get(etype, {})
            for key, entry_data in type_dict.items():
                if unconfirmed_only and not entry_data.get("needs_confirmation"):
                    continue
                yield (etype, key, entity_from_dict(entry_data))

    def count_by_type(self) -> dict[str, dict[str, int]]:
        """Returns ``{"person": {"total": 5, "unconfirmed": 1}, ...}``."""
        result = {}
        for etype in VALID_ENTITY_TYPES:
            type_dict = self._data["entities"].get(etype, {})
            total = len(type_dict)
            unconfirmed = sum(
                1 for ed in type_dict.values()
                if ed.get("needs_confirmation")
            )
            result[etype] = {"total": total, "unconfirmed": unconfirmed}
        return result

    def confirm_entity(self, entity_type: str, key: str) -> bool:
        """Set ``needs_confirmation=False``, clear ``proposed_match``.

        Returns True if the entity was changed.
        """
        type_dict = self._data["entities"].get(entity_type, {})
        if key not in type_dict:
            return False
        entry = type_dict[key]
        if not entry.get("needs_confirmation"):
            return False
        entry["needs_confirmation"] = False
        entry["proposed_match"] = None
        entry["updated_at"] = _now_iso()
        return True

    def entity_count(self) -> int:
        """Total number of entities across all types."""
        return sum(
            len(self._data["entities"].get(t, {}))
            for t in VALID_ENTITY_TYPES
        )

    def unconfirmed_count(self) -> int:
        """Count of entities with needs_confirmation=True."""
        count = 0
        for t in VALID_ENTITY_TYPES:
            for ed in self._data["entities"].get(t, {}).values():
                if ed.get("needs_confirmation"):
                    count += 1
        return count

    def resolve_key_to_name(
        self, key: str, entity_type: Optional[str] = None,
    ) -> str:
        """Resolve an entity slug to its canonical name.

        Falls back to the raw key if not found.
        """
        types = [entity_type] if entity_type else VALID_ENTITY_TYPES
        for etype in types:
            type_dict = self._data["entities"].get(etype, {})
            if key in type_dict:
                return type_dict[key].get("canonical_name", key)
        return key

    def to_json(self) -> str:
        """Serialize the full registry as a JSON string."""
        return json.dumps(self._data, indent=2)

