"""Version tracking: change detection, version history, text caching."""

import json
import logging
import re
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


class VersionHistoryError(RuntimeError):
    """Raised when persisted version history is unreadable or malformed."""


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

    Uses positional identity: slide number = identity. Reordered slides appear
    as multiple "modified" entries (conservative, never misses a change).
    Content-based reorder detection deferred to Tier 2+. See spec D3.

    Note: Version tracking is TEXT-ONLY. Image-only edits (same text, different
    slide visuals) correctly produce has_changes=False here while triggering an
    analysis cache miss (image hash changed). This extends the D1 contract:
    version tracking tracks text content semantics, analysis caching tracks
    API input fidelity (text + image). Both are correct for their concerns.

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
    history = load_version_history(history_path, strict=True)
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

    # Persist with rollback: if history write fails after cache write,
    # restore the previous texts cache before re-raising.
    history.append(version_info.to_dict())
    had_cache = cache_path.exists()
    save_texts_cache(cache_path, new_texts)
    try:
        save_version_history(history_path, history)
    except OSError as err:
        try:
            _restore_texts_cache(cache_path, old_texts, had_cache=had_cache)
        except OSError as rollback_err:
            raise OSError(
                f"{err}; rollback of texts cache also failed: {rollback_err}"
            ) from rollback_err
        raise

    return version_info


def load_version_history(history_path: Path, strict: bool = False) -> list[dict]:
    """Load version history from JSON file.

    Schema-validates loaded data: rejects non-list payloads, strips entries
    missing a valid integer 'version' key. In strict mode, malformed history
    raises VersionHistoryError so conversion does not silently reset to v1.
    """
    if not history_path.exists():
        return []

    def _fail(message: str, exc: Exception | None = None) -> list[dict]:
        if strict:
            raise VersionHistoryError(message) from exc
        logger.warning(message)
        return []

    try:
        data = json.loads(history_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return _fail(f"Failed to load version history: {e}", e)

    # Extract versions list from wrapper dict or bare list
    if isinstance(data, dict):
        versions = data.get("versions", [])
    elif isinstance(data, list):
        versions = data
    else:
        return _fail(
            f"Version history has unexpected shape ({type(data).__name__})"
        )

    if not isinstance(versions, list):
        return _fail(
            f"Version history 'versions' is not a list ({type(versions).__name__})"
        )

    # Validate each entry: must be a dict with an integer 'version' key
    valid = []
    for i, entry in enumerate(versions):
        if not isinstance(entry, dict):
            if strict:
                raise VersionHistoryError(f"Version history entry {i} is not a dict")
            logger.warning("Version history entry %d is not a dict — skipping", i)
            continue
        v = entry.get("version")
        if not isinstance(v, int):
            if strict:
                raise VersionHistoryError(
                    f"Version history entry {i} has no valid 'version' key"
                )
            logger.warning(
                "Version history entry %d has no valid 'version' key — skipping", i
            )
            continue
        valid.append(entry)

    if len(valid) < len(versions):
        logger.warning(
            "Stripped %d malformed entries from version history (%d remaining)",
            len(versions) - len(valid), len(valid),
        )
    return valid


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
        logger.warning(
            "Failed to load texts cache (%s). Next conversion will report "
            "all slides as added/modified (one-time self-correction).", e,
        )
        return {}


def save_texts_cache(cache_path: Path, texts: dict) -> None:
    """Save slide texts cache for future change detection.

    No _EXTRACTION_VERSION marker needed: text diffs are self-correcting.
    If extraction logic changes, the new text will differ from cached text,
    and detect_changes() will honestly report the difference. See spec D2.
    """
    # Store with string keys for JSON compatibility; extract full_text from SlideText
    data = {str(k): _to_str(v) for k, v in texts.items()}
    data["_cache_version"] = _TEXTS_CACHE_VERSION
    _atomic_write_json(cache_path, data)


def _normalize_text(text: str) -> str:
    """Normalize text for comparison (collapse whitespace, strip).

    This intentionally differs from analysis.py:_text_hash(), which hashes
    raw text for API input reproduction. A whitespace-only change will NOT
    trigger a new version here (correct: semantic content unchanged) but WILL
    cause an analysis cache miss (correct: different API prompt bytes). See D1.

    Similarly, image-only edits are invisible to version tracking (text didn't
    change) but trigger analysis cache misses (image hash changed). Both
    disagreements are correct: versioning tracks text semantics, caching
    tracks full API input fidelity.
    """
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _atomic_write_json(path: Path, data: dict):
    """Write JSON atomically: write to temp file, then rename.

    Intentionally does not catch OSError. Version data is correctness-critical:
    if version_history.json can't be written, the next conversion would start
    at v1, losing all provenance. Contrast with analysis.py:_save_cache() which
    catches OSError because analysis results are already in memory. See spec D4.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2))
    tmp_path.rename(path)


def _restore_texts_cache(
    cache_path: Path,
    old_texts: dict[int, SlideTextLike],
    *,
    had_cache: bool,
) -> None:
    """Restore the previous texts cache after a failed history write."""
    if had_cache:
        save_texts_cache(cache_path, old_texts)
    elif cache_path.exists():
        cache_path.unlink()
