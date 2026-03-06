"""Version tracking: change detection, version history, text caching."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from ..pipeline.text import SlideText

#: Values accepted as slide text: raw strings or SlideText objects.
SlideTextLike = Union[str, "SlideText"]

logger = logging.getLogger(__name__)

# Cache format version. Increment when the data shape of .texts_cache.json changes.
# On mismatch, the cache is invalidated (forces honest "all added" changeset).
_TEXTS_CACHE_VERSION = 2  # v2: post-reconciliation texts with gap-filled empties


def _to_str(val: SlideTextLike) -> str:
    """Convert a slide text value to a plain string.

    Accepts both raw strings and SlideText objects (via .full_text).
    """
    if isinstance(val, str):
        return val
    return getattr(val, "full_text", str(val))


@dataclass
class ChangeSet:
    """What changed between two versions of a deck."""
    added: list[int] = field(default_factory=list)
    removed: list[int] = field(default_factory=list)
    modified: list[int] = field(default_factory=list)
    unchanged: list[int] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.modified)

    def to_dict(self) -> dict:
        return {
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "unchanged": self.unchanged,
        }


@dataclass
class VersionInfo:
    """Metadata for a single version."""
    version: int
    timestamp: str
    source_hash: str
    source_path: str
    note: Optional[str]
    slide_count: int
    changes: ChangeSet

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "source_hash": self.source_hash,
            "source_path": self.source_path,
            "note": self.note,
            "slide_count": self.slide_count,
            "changes": self.changes.to_dict(),
        }


def detect_changes(
    old_texts: dict[int, SlideTextLike],
    new_texts: dict[int, SlideTextLike],
) -> ChangeSet:
    """Detect changes between two versions of slide text.

    Args:
        old_texts: Previous version's slide texts {slide_num: str or SlideText}.
        new_texts: Current version's slide texts {slide_num: str or SlideText}.

    Returns:
        ChangeSet describing what changed.
    """
    old_slides = set(old_texts.keys())
    new_slides = set(new_texts.keys())

    added = sorted(new_slides - old_slides)
    removed = sorted(old_slides - new_slides)

    common = old_slides & new_slides
    modified = []
    unchanged = []

    for slide_num in sorted(common):
        old_text = _normalize_text(_to_str(old_texts[slide_num]))
        new_text = _normalize_text(_to_str(new_texts[slide_num]))
        if old_text != new_text:
            modified.append(slide_num)
        else:
            unchanged.append(slide_num)

    changes = ChangeSet(
        added=added,
        removed=removed,
        modified=modified,
        unchanged=unchanged,
    )

    if changes.has_changes:
        logger.info(
            "Changes detected: %d added, %d removed, %d modified, %d unchanged",
            len(added), len(removed), len(modified), len(unchanged),
        )
    else:
        logger.info("No changes detected across %d slides", len(unchanged))

    return changes


def compute_version(
    deck_dir: Path,
    source_hash: str,
    source_path: str,
    slide_count: int,
    new_texts: dict[int, SlideTextLike],
    note: Optional[str] = None,
) -> VersionInfo:
    """Compute version info for a conversion, including change detection.

    Args:
        deck_dir: Directory for this deck (contains version_history.json).
        source_hash: Current source file hash.
        source_path: Relative path to source.
        slide_count: Number of slides.
        new_texts: Current slide texts (str or SlideText values).
        note: Optional version note.

    Returns:
        VersionInfo for this conversion.
    """
    history_path = deck_dir / "version_history.json"
    cache_path = deck_dir / ".texts_cache.json"

    # Load previous texts for change detection
    old_texts = load_texts_cache(cache_path)

    # Detect changes
    changes = detect_changes(old_texts, new_texts)

    # Determine version number
    history = load_version_history(history_path)
    if history:
        version_num = history[-1]["version"] + 1
    else:
        version_num = 1
        # First version: all slides are "added"
        if not changes.has_changes:
            changes = ChangeSet(
                added=sorted(new_texts.keys()),
                removed=[],
                modified=[],
                unchanged=[],
            )

    timestamp = datetime.now(timezone.utc).isoformat()

    version_info = VersionInfo(
        version=version_num,
        timestamp=timestamp,
        source_hash=source_hash,
        source_path=source_path,
        note=note,
        slide_count=slide_count,
        changes=changes,
    )

    # Persist
    history.append(version_info.to_dict())
    save_version_history(history_path, history)
    save_texts_cache(cache_path, new_texts)

    return version_info


def load_version_history(history_path: Path) -> list[dict]:
    """Load version history from JSON file."""
    if not history_path.exists():
        return []
    try:
        data = json.loads(history_path.read_text())
        return data.get("versions", []) if isinstance(data, dict) else data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load version history: %s", e)
        return []


def save_version_history(history_path: Path, versions: list[dict]):
    """Save version history with atomic write."""
    data = {"versions": versions}
    _atomic_write_json(history_path, data)


def load_texts_cache(cache_path: Path) -> dict[int, str]:
    """Load cached slide texts for change detection.

    Invalidates the cache if the version marker is missing or mismatched,
    preventing spurious change detection after upgrades (B3 fix).
    """
    if not cache_path.exists():
        return {}
    try:
        raw = json.loads(cache_path.read_text())
        if not isinstance(raw, dict):
            return {}
        # Check version marker
        stored_version = raw.get("_cache_version")
        if stored_version != _TEXTS_CACHE_VERSION:
            logger.info(
                "Texts cache version mismatch (stored=%s, current=%s) — invalidating",
                stored_version, _TEXTS_CACHE_VERSION,
            )
            return {}
        return {int(k): v for k, v in raw.items() if k != "_cache_version"}
    except (json.JSONDecodeError, OSError, ValueError) as e:
        logger.warning("Failed to load texts cache: %s", e)
        return {}


def save_texts_cache(cache_path: Path, texts: dict) -> None:
    """Save slide texts cache for future change detection."""
    # Store with string keys for JSON compatibility; extract full_text from SlideText
    data = {str(k): _to_str(v) for k, v in texts.items()}
    data["_cache_version"] = _TEXTS_CACHE_VERSION
    _atomic_write_json(cache_path, data)


def _normalize_text(text: str) -> str:
    """Normalize text for comparison (collapse whitespace, strip)."""
    import re
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _atomic_write_json(path: Path, data: dict):
    """Write JSON atomically: write to temp file, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2))
    tmp_path.rename(path)
