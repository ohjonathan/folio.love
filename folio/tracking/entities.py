"""Entity registry: canonical entity store backed by entities.json."""

import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from .registry import _atomic_write_json as atomic_write_json

logger = logging.getLogger(__name__)

_ENTITY_SCHEMA_VERSION = 1
VALID_ENTITY_TYPES = frozenset({"person", "department", "system", "process"})
# Entity types that can be auto-extracted from interaction notes (PR B seam)
EXTRACTION_ENTITY_TYPES = frozenset({"person", "department"})
_WIKILINK_UNSAFE_CHARS = set("[]|#^")
_WHITESPACE_RE = re.compile(r"\s+")
_PERSON_COMMA_RE = re.compile(
    r"^(?P<last>[^,]+),\s*(?P<first>[^,]+?)(?:\s+(?P<suffix>Jr\.?|Sr\.?|II|III|IV|V|VI|VII|VIII|IX))?$",
    re.IGNORECASE,
)
_PERSON_NAME_TOKEN_RE = re.compile(r"^[^\W\d_]+(?:[.'-][^\W\d_]+)*\.?$")
_PERSON_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix"})
_NON_PERSON_COMMA_TOKENS = frozenset(
    {
        "associates",
        "architecture",
        "company",
        "compliance",
        "consulting",
        "corp",
        "corporation",
        "department",
        "engineering",
        "finance",
        "group",
        "holdings",
        "inc",
        "legal",
        "llc",
        "llp",
        "marketing",
        "operations",
        "partners",
        "payment",
        "payments",
        "platform",
        "product",
        "products",
        "review",
        "sales",
        "security",
        "services",
        "solutions",
        "support",
        "systems",
        "team",
        "technology",
        "treasury",
    }
)


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


def normalize_entity_name(name: str) -> str:
    """Collapse whitespace and sanitize for consistent name matching."""
    collapsed = _WHITESPACE_RE.sub(" ", str(name or "")).strip()
    sanitized = sanitize_wikilink_name(collapsed)
    return _WHITESPACE_RE.sub(" ", sanitized).strip()


def canonicalize_person_import_name(name: str) -> tuple[str, list[str]]:
    """Return canonical person name for import plus any implicit aliases."""
    normalized = normalize_entity_name(name)
    transposed = _transpose_person_name(normalized)
    canonical = transposed or normalized

    aliases: list[str] = []
    if canonical and canonical.lower() != normalized.lower():
        aliases.append(normalized)
    return canonical, aliases


def person_name_variants(name: str) -> list[str]:
    """Generate ordered exact-match person name variants.

    Variants are exact lookup candidates only. Single-token suffix-stripped
    fragments are intentionally excluded to avoid partial-name matching.
    """
    normalized = normalize_entity_name(name)
    variants: list[str] = []
    _append_variant(variants, normalized)

    transposed = _transpose_person_name(normalized)
    _append_variant(variants, transposed)

    if not transposed:
        stripped = _strip_person_id_suffix(normalized)
        if stripped and len(stripped.split()) > 1:
            _append_variant(variants, stripped)

    stripped_transposed = _strip_person_id_suffix(transposed)
    if stripped_transposed and len(stripped_transposed.split()) > 1:
        _append_variant(variants, stripped_transposed)

    return variants


def lookup_person_matches(
    registry: "EntityRegistry",
    *names: str,
    confirmed_only: bool = False,
) -> list[tuple[str, str, "EntityEntry"]]:
    """Look up person entities across ordered exact-match fallback phases."""
    phases: list[list[str]] = [[], [], []]
    for name in names:
        for phase_idx, candidates in enumerate(_person_lookup_phases(name)):
            for candidate in candidates:
                if candidate not in phases[phase_idx]:
                    phases[phase_idx].append(candidate)

    for candidates in phases:
        matches = _lookup_person_candidates(
            registry,
            candidates,
            confirmed_only=confirmed_only,
        )
        if matches:
            return matches

    return []


def _lookup_person_candidates(
    registry: "EntityRegistry",
    candidates: list[str],
    *,
    confirmed_only: bool,
) -> list[tuple[str, str, "EntityEntry"]]:
    seen: set[tuple[str, str]] = set()
    matches: list[tuple[str, str, EntityEntry]] = []
    for candidate in candidates:
        for match in registry.lookup(
            candidate,
            entity_type="person",
            confirmed_only=confirmed_only,
        ):
            key = (match[0], match[1])
            if key in seen:
                continue
            seen.add(key)
            matches.append(match)
    return matches


def _append_variant(variants: list[str], candidate: Optional[str]) -> None:
    if not candidate:
        return
    if candidate not in variants:
        variants.append(candidate)


def _person_lookup_phases(name: str) -> list[list[str]]:
    normalized = normalize_entity_name(name)
    phases: list[list[str]] = [[], [], []]
    _append_variant(phases[0], normalized)

    transposed = _transpose_person_name(normalized)
    _append_variant(phases[1], transposed)

    strip_source = transposed or normalized
    for candidate in _strip_person_id_suffix_candidates(strip_source):
        if candidate not in phases[0] and candidate not in phases[1]:
            phases[2].append(candidate)

    return phases


def _transpose_person_name(name: str) -> Optional[str]:
    match = _PERSON_COMMA_RE.match(name)
    if not match:
        return None
    last = normalize_entity_name(match.group("last"))
    first = normalize_entity_name(match.group("first"))
    suffix = normalize_entity_name(match.group("suffix") or "")
    if not _is_person_like_comma_name(name, last=last, first=first, suffix=suffix):
        return None
    if not first or not last:
        return None
    transposed = f"{first} {last}"
    if suffix:
        transposed = f"{transposed} {suffix}"
    return transposed


def _is_person_like_comma_name(
    original: str,
    *,
    last: str,
    first: str,
    suffix: str,
) -> bool:
    if not original or any(char.isdigit() for char in original):
        return False
    if "&" in original or "/" in original:
        return False

    last_tokens = last.split()
    first_tokens = first.split()
    if not last_tokens or not first_tokens:
        return False
    if len(last_tokens) > 3 or len(first_tokens) > 3:
        return False

    for token in last_tokens + first_tokens:
        if not _PERSON_NAME_TOKEN_RE.fullmatch(token):
            return False
        normalized_token = token.rstrip(".").lower()
        if normalized_token in _NON_PERSON_COMMA_TOKENS:
            return False

    if suffix:
        normalized_suffix = suffix.rstrip(".").lower()
        if normalized_suffix not in _PERSON_SUFFIXES:
            return False

    return True


def _strip_person_id_suffix(name: Optional[str]) -> Optional[str]:
    if not name:
        return None

    tokens = name.split()
    stripped = False
    result: list[str] = []
    for idx, token in enumerate(tokens):
        next_token = tokens[idx + 1] if idx + 1 < len(tokens) else None
        base = _strip_person_id_suffix_token(token, next_token=next_token)
        if base is None:
            result.append(token)
            continue
        result.append(base)
        stripped = True
    if not stripped:
        return None
    return " ".join(result)


def _strip_person_id_suffix_candidates(name: Optional[str]) -> list[str]:
    if not name:
        return []

    tokens = name.split()
    candidates: list[str] = []
    for idx, token in enumerate(tokens):
        next_token = tokens[idx + 1] if idx + 1 < len(tokens) else None
        for base in _strip_person_id_suffix_token_candidates(token, next_token=next_token):
            rewritten = list(tokens)
            rewritten[idx] = base
            candidate = " ".join(rewritten)
            if candidate != name and candidate not in candidates:
                candidates.append(candidate)
    return candidates


def _strip_person_id_suffix_token(
    token: str,
    *,
    next_token: Optional[str],
) -> Optional[str]:
    """Strip a likely appended user-ID suffix from a title-cased name token.

    We prefer the longest exact surname fragment match, but fall back when the
    winning split leaves a trailing vowel on the base token. That tends to mean
    we split too early and consumed the real name's final vowel as if it were
    part of a user-ID prefix, for example ``Christopherasmith``.
    """
    if not re.fullmatch(r"[A-Z][a-z]+", token):
        return None
    if len(token) < 10 or not next_token:
        return None

    next_key = re.sub(r"[^A-Za-z]", "", next_token).lower()
    if len(next_key) < 4:
        return None

    candidates: list[Tuple[int, int, str, str]] = []
    for split_idx in range(4, len(token) - 4):
        base = token[:split_idx]
        suffix = token[split_idx:].lower()
        if len(base) < 4 or len(suffix) < 5:
            continue
        for initials_len in (2, 1, 0):
            fragment = suffix[initials_len:]
            if len(fragment) < 3 or not next_key.startswith(fragment):
                continue
            candidates.append((len(fragment), initials_len, base, suffix[:initials_len]))

    if not candidates:
        return None

    best_choice = max(candidates, key=lambda choice: (choice[0], choice[1], choice[2]))
    exact_zero_choice = max(
        (
            choice for choice in candidates
            if choice[1] == 0 and choice[0] == len(next_key)
        ),
        default=None,
        key=lambda choice: choice[2],
    )
    exact_one_choice = max(
        (
            choice for choice in candidates
            if choice[1] == 1 and choice[0] == len(next_key)
        ),
        default=None,
        key=lambda choice: choice[2],
    )

    if best_choice[1] == 2 and any(char in "aeiou" for char in best_choice[3]):
        # If the 2-initial split starts with vowels, prefer a cleaner exact
        # surname match that does not lop off the real name ending.
        if exact_one_choice and exact_one_choice[2][-1].lower() not in "aeiou":
            return exact_one_choice[2]
        if exact_zero_choice is not None:
            return exact_zero_choice[2]
    if (
        exact_zero_choice is not None
        and best_choice[1] == 1
        and best_choice[2][-1].lower() in "aeiou"
    ):
        return exact_zero_choice[2]

    return best_choice[2]


def _strip_person_id_suffix_token_candidates(
    token: str,
    *,
    next_token: Optional[str],
) -> list[str]:
    if not re.fullmatch(r"[A-Z][a-z]+", token):
        return []
    if len(token) < 10 or not next_token:
        return []

    next_key = re.sub(r"[^A-Za-z]", "", next_token).lower()
    if len(next_key) < 4:
        return []

    candidates: list[str] = []
    for split_idx in range(4, len(token) - 4):
        base = token[:split_idx]
        suffix = token[split_idx:].lower()
        if len(base) < 4 or len(suffix) < 5:
            continue
        for initials_len in (2, 1, 0):
            fragment = suffix[initials_len:]
            if len(fragment) < 3 or fragment != next_key:
                continue
            if base not in candidates:
                candidates.append(base)

    return candidates


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_entity_registry() -> dict:
    return {
        "_schema_version": _ENTITY_SCHEMA_VERSION,
        "updated_at": _now_iso(),
        "entities": {t: {} for t in VALID_ENTITY_TYPES},
        "rejected_merges": [],
    }


def _compute_entity_merge_basis_fingerprint(
    subject_type: str,
    left_key: str,
    right_key: str,
    reasons: list[str],
) -> str:
    """Compute the basis_fingerprint for an entity-merge suggestion.

    Uses canonical JSON serialization (sort_keys, fixed separators,
    ensure_ascii=False) so the hash is injective even if reason labels
    later contain delimiter-like characters. Per parent proposal §7
    entity-merge fingerprint clause.
    """
    payload = {
        "subject_type": subject_type,
        "entity_keys": sorted([left_key, right_key]),
        "reasons": sorted(reasons),
    }
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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
    source: str = "import"                       # provenance label
    first_seen: str = ""                         # ISO 8601, never overwritten
    created_at: str = ""                         # ISO 8601
    updated_at: str = ""                         # ISO 8601
    proposed_match: Optional[str] = None         # entity key, PR B populates
    # Person-specific
    title: Optional[str] = None
    org_level: Optional[str] = None
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


@dataclass
class PersonMergeSuggestion:
    """A deterministic duplicate-person candidate."""

    left_key: str
    right_key: str
    left_name: str
    right_name: str
    reasons: list[str]
    basis_fingerprint: str = ""
    revived: bool = False


@dataclass
class EntityMergeResult:
    """Result of merging one entity into another."""

    winner_key: str
    loser_key: str
    rewritten_references: int = 0
    dropped_aliases: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _collapse_middle_initials(name: str) -> str:
    tokens = [token for token in normalize_entity_name(name).split() if token]
    filtered: list[str] = []
    for idx, token in enumerate(tokens):
        if 0 < idx < len(tokens) - 1 and len(token.rstrip(".")) == 1:
            continue
        filtered.append(token.rstrip("."))
    return " ".join(filtered)


def _person_comparison_key(name: str) -> str:
    return re.sub(r"[^a-z]", "", normalize_entity_name(name).lower())


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

        # Default rejected_merges to [] for legacy files missing the key.
        # v0.6.5 PROV-equivalent: no schema-version bump; additive top-level key.
        data.setdefault("rejected_merges", [])

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
        extra_exclude_keys: Optional[set[str]] = None,
    ) -> list[str]:
        """Return list of colliding aliases (lowercased).

        Checks ``new_aliases`` against all canonical names and aliases
        in the type namespace except the entity with ``exclude_key``.
        """
        type_dict = self._data["entities"].get(entity_type, {})
        excluded = {exclude_key, *(extra_exclude_keys or set())}
        existing_names = set()
        existing_aliases = set()
        for k, ed in type_dict.items():
            if k in excluded:
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

    def suggest_person_merges(
        self, apply_rejection_memory: bool = True
    ) -> list[PersonMergeSuggestion]:
        """Return deterministic duplicate-person candidates.

        When ``apply_rejection_memory`` is True (default), candidates whose
        ``basis_fingerprint`` matches a stored rejection record are dropped.
        Candidates where the same pair has prior rejections but the current
        fingerprint differs are marked ``revived=True``.
        """
        people: list[tuple[str, EntityEntry]] = [
            (key, entry)
            for _etype, key, entry in self.iter_entities(entity_type="person")
        ]

        pair_reasons: dict[tuple[str, str], set[str]] = {}

        def add_reason(left_key: str, right_key: str, reason: str) -> None:
            if left_key == right_key:
                return
            pair_key = tuple(sorted((left_key, right_key)))
            pair_reasons.setdefault(pair_key, set()).add(reason)

        def bucket_signatures(reason: str, values_by_key: dict[str, set[str]]) -> None:
            buckets: dict[str, list[str]] = {}
            for key, values in values_by_key.items():
                for value in values:
                    if not value:
                        continue
                    buckets.setdefault(value, []).append(key)
            for keys in buckets.values():
                if len(keys) < 2:
                    continue
                ordered = sorted(set(keys))
                for idx, left in enumerate(ordered):
                    for right in ordered[idx + 1:]:
                        add_reason(left, right, reason)

        normalized_map: dict[str, set[str]] = {}
        transposed_map: dict[str, set[str]] = {}
        collapsed_map: dict[str, set[str]] = {}
        stripped_map: dict[str, set[str]] = {}
        alias_map: dict[str, set[str]] = {}

        for key, entry in people:
            names = [entry.canonical_name, *(entry.aliases or [])]
            for raw_name in names:
                normalized = normalize_entity_name(raw_name)
                if not normalized:
                    continue
                normalized_map.setdefault(key, set()).add(_person_comparison_key(normalized))

                transposed = _transpose_person_name(normalized) or normalized
                transposed_map.setdefault(key, set()).add(_person_comparison_key(transposed))

                collapsed = _collapse_middle_initials(transposed)
                collapsed_map.setdefault(key, set()).add(_person_comparison_key(collapsed))

                stripped = _strip_person_id_suffix(transposed) or transposed
                stripped_map.setdefault(key, set()).add(_person_comparison_key(stripped))

                alias_map.setdefault(key, set()).add(normalized.lower())

        bucket_signatures("punctuation_whitespace_normalization", normalized_map)
        bucket_signatures("last_first_transpose", transposed_map)
        bucket_signatures("middle_initial_collapse", collapsed_map)
        bucket_signatures("id_suffix_stripping", stripped_map)
        bucket_signatures("alias_overlap", alias_map)

        # Build rejected-key index: {(subject_type, sorted_lk, sorted_rk): set(fingerprints)}.
        rejected_index: dict[tuple[str, str, str], set[str]] = {}
        for record in self._data.get("rejected_merges", []) or []:
            if not isinstance(record, dict):
                continue
            rec_subject = record.get("subject_type")
            rec_keys = record.get("entity_keys")
            rec_fp = record.get("basis_fingerprint")
            if (
                not isinstance(rec_subject, str)
                or not isinstance(rec_keys, list)
                or len(rec_keys) != 2
                or not isinstance(rec_fp, str)
            ):
                continue
            sorted_rec_keys = tuple(sorted(rec_keys))
            idx_key = (rec_subject, sorted_rec_keys[0], sorted_rec_keys[1])
            rejected_index.setdefault(idx_key, set()).add(rec_fp)

        suggestions: list[PersonMergeSuggestion] = []
        for left_key, right_key in sorted(pair_reasons):
            left = self.get_entity("person", left_key)
            right = self.get_entity("person", right_key)
            if left is None or right is None:
                continue
            reasons = sorted(pair_reasons[(left_key, right_key)])
            basis_fp = _compute_entity_merge_basis_fingerprint(
                "person", left_key, right_key, reasons
            )
            sorted_pair = tuple(sorted((left_key, right_key)))
            idx_key = ("person", sorted_pair[0], sorted_pair[1])
            rejected_fps = rejected_index.get(idx_key, set())

            if apply_rejection_memory and basis_fp in rejected_fps:
                # Exact-fingerprint match: suppressed.
                continue

            revived = apply_rejection_memory and bool(rejected_fps) and basis_fp not in rejected_fps

            suggestions.append(
                PersonMergeSuggestion(
                    left_key=left_key,
                    right_key=right_key,
                    left_name=left.canonical_name,
                    right_name=right.canonical_name,
                    reasons=reasons,
                    basis_fingerprint=basis_fp,
                    revived=revived,
                )
            )
        suggestions.sort(
            key=lambda item: (
                item.left_name.lower(),
                item.right_name.lower(),
                item.left_key,
                item.right_key,
            )
        )
        return suggestions

    def count_entity_merge_suppressions(self) -> int:
        """Return the total count of stored entity-merge rejection records."""
        rejected = self._data.get("rejected_merges", [])
        if not isinstance(rejected, list):
            return 0
        return sum(1 for r in rejected if isinstance(r, dict))

    def reject_person_merge(
        self, left_key: str, right_key: str
    ) -> Tuple[bool, str]:
        """Reject a person-merge suggestion, persisting to ``rejected_merges``.

        Returns ``(True, "rejected")`` when a new record is appended, or
        ``(False, "already rejected")`` when the same pair + fingerprint
        is already recorded (idempotent no-op).

        Raises ``EntityRegistryError`` if either key doesn't resolve to a
        current person entity (covers merged-away loser keys per spec §4.1).
        """
        left = self.get_entity("person", left_key)
        right = self.get_entity("person", right_key)
        if left is None:
            raise EntityRegistryError(
                f"'{left_key}' no longer exists (possibly already merged)"
            )
        if right is None:
            raise EntityRegistryError(
                f"'{right_key}' no longer exists (possibly already merged)"
            )
        if left_key == right_key:
            raise EntityRegistryError(
                "cannot reject merge of an entity with itself"
            )

        # Recompute reasons for this pair by running the same heuristic
        # bucketing used in suggest_person_merges. Cheap — O(people) — and
        # keeps reject_person_merge authoritative even when suggest isn't
        # called first.
        current_suggestions = self.suggest_person_merges(apply_rejection_memory=False)
        sorted_pair = tuple(sorted((left_key, right_key)))
        matching = [
            s for s in current_suggestions
            if tuple(sorted((s.left_key, s.right_key))) == sorted_pair
        ]
        if matching:
            reasons = matching[0].reasons
            basis_fp = matching[0].basis_fingerprint
        else:
            # Pair isn't currently a suggestion (e.g., operator rejecting
            # preemptively). Use empty reasons — fingerprint still well-defined.
            reasons = []
            basis_fp = _compute_entity_merge_basis_fingerprint(
                "person", left_key, right_key, reasons
            )

        rejected_list = self._data.setdefault("rejected_merges", [])
        # Idempotency check on exact (subject_type, sorted_keys, basis_fp).
        for record in rejected_list:
            if not isinstance(record, dict):
                continue
            if record.get("subject_type") != "person":
                continue
            rec_keys = record.get("entity_keys")
            if not isinstance(rec_keys, list) or len(rec_keys) != 2:
                continue
            if tuple(sorted(rec_keys)) != sorted_pair:
                continue
            if record.get("basis_fingerprint") == basis_fp:
                return (False, "already rejected")

        rejected_list.append({
            "subject_type": "person",
            "entity_keys": [sorted_pair[0], sorted_pair[1]],
            "basis_fingerprint": basis_fp,
            "reasons_at_rejection": reasons,
            "rejected_at": _now_iso(),
        })
        self._data["updated_at"] = _now_iso()
        return (True, "rejected")

    def merge_person_entities(self, winner_key: str, loser_key: str) -> EntityMergeResult:
        """Merge one person entity into another."""
        if winner_key == loser_key:
            raise EntityRegistryError("winner and loser must be different people")

        winner = self.get_entity("person", winner_key)
        loser = self.get_entity("person", loser_key)
        if winner is None:
            raise EntityRegistryError(f"Unknown winner person '{winner_key}'")
        if loser is None:
            raise EntityRegistryError(f"Unknown loser person '{loser_key}'")

        result = EntityMergeResult(winner_key=winner_key, loser_key=loser_key)

        winner_entry = self._data["entities"]["person"][winner_key]
        loser_entry = self._data["entities"]["person"][loser_key]

        merged_aliases = [
            alias
            for alias in [*(winner.aliases or []), loser.canonical_name, *(loser.aliases or [])]
            if alias and alias.lower() != winner.canonical_name.lower()
        ]
        deduped_aliases: list[str] = []
        seen_aliases: set[str] = set()
        for alias in merged_aliases:
            lowered = alias.lower()
            if lowered in seen_aliases:
                continue
            seen_aliases.add(lowered)
            deduped_aliases.append(alias)

        collisions = self._check_alias_collisions(
            "person",
            winner_key,
            deduped_aliases,
            extra_exclude_keys={loser_key},
        )
        if collisions:
            result.dropped_aliases.extend(sorted(collisions))
            deduped_aliases = [alias for alias in deduped_aliases if alias not in collisions]
            result.warnings.append(
                f"Dropped colliding aliases: {', '.join(sorted(collisions))}"
            )
        winner_entry["aliases"] = deduped_aliases
        winner_entry["updated_at"] = _now_iso()

        for etype, type_dict in self._data["entities"].items():
            for key, entry_data in type_dict.items():
                if not isinstance(entry_data, dict):
                    continue
                for field_name in ("reports_to", "head", "proposed_match"):
                    if entry_data.get(field_name) != loser_key:
                        continue
                    if etype == "person" and key == winner_key and field_name in {"reports_to", "head"}:
                        entry_data[field_name] = None
                    else:
                        entry_data[field_name] = winner_key
                    entry_data["updated_at"] = _now_iso()
                    result.rewritten_references += 1

        del self._data["entities"]["person"][loser_key]
        winner_entry["updated_at"] = _now_iso()
        loser_entry["updated_at"] = _now_iso()
        return result

    def to_json(self) -> str:
        """Serialize the full registry as a JSON string."""
        return json.dumps(self._data, indent=2)
