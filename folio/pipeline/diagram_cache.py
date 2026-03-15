"""Diagram-specific cache layer for PR 4 extraction stages.

Maintains three separate cache files per deck directory:
- .analysis_cache_diagram_pass_a.json   (Pass A extraction results)
- .analysis_cache_diagram_post_b.json   (Post-mutation results)
- .analysis_cache_diagram_final.json    (Final verified results)

Each file uses image-hash keyed entries with stage-specific version
markers and dependency hashes.  Does NOT modify consulting-slide caches.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Version constants
# ---------------------------------------------------------------------------

DIAGRAM_CACHE_VERSION = 1
DIAGRAM_SCHEMA_VERSION = "1.0"
DIAGRAM_PIPELINE_VERSION = "pr4-extraction-v1"
DIAGRAM_IMAGE_STRATEGY_VERSION = "tiles-v1"

# Stage file names
_PASS_A_FILENAME = ".analysis_cache_diagram_pass_a.json"
_POST_B_FILENAME = ".analysis_cache_diagram_post_b.json"
_FINAL_FILENAME = ".analysis_cache_diagram_final.json"


# ---------------------------------------------------------------------------
# Prompt version derivation
# ---------------------------------------------------------------------------

def _prompt_version(prompt_text: str) -> str:
    """Derive a version key from a prompt text (SHA-256[:12])."""
    return hashlib.sha256(prompt_text.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Dependency hash helpers
# ---------------------------------------------------------------------------

def _stable_hash(*parts: str) -> str:
    """Compute SHA-256[:16] from ordered string parts (null-delimited)."""
    combined = "\x00".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def text_inventory_hash(text_inventory: str) -> str:
    """Hash the exact text inventory string given to Pass A/B."""
    return _stable_hash(text_inventory)


def page_profile_hash(
    classification: str,
    escalation_level: str,
    render_dpi: int,
    crop_box: tuple[float, float, float, float],
    rotation: int,
    word_count: int,
    vector_count: int,
    char_count: int,
    has_bounded_texts: bool,
) -> str:
    """Build a deterministic stable signature from page profile fields."""
    return _stable_hash(
        classification,
        escalation_level,
        str(render_dpi),
        f"{crop_box[0]:.2f},{crop_box[1]:.2f},{crop_box[2]:.2f},{crop_box[3]:.2f}",
        str(rotation),
        str(word_count),
        str(vector_count),
        str(char_count),
        str(has_bounded_texts),
    )


def pass_a_graph_hash(diagram_type: str, graph_dict: dict) -> str:
    """Hash normalized Pass A payload that feeds Pass B."""
    nodes_str = json.dumps(graph_dict.get("nodes", []), sort_keys=True)
    edges_str = json.dumps(graph_dict.get("edges", []), sort_keys=True)
    groups_str = json.dumps(graph_dict.get("groups", []), sort_keys=True)
    return _stable_hash(diagram_type, nodes_str, edges_str, groups_str)


def post_b_graph_hash(
    diagram_type: str,
    graph_dict: dict,
    sanity_triggered: bool,
) -> str:
    """Hash post-B graph and abstention-relevant state."""
    graph_str = json.dumps(graph_dict, sort_keys=True)
    return _stable_hash(diagram_type, graph_str, str(sanity_triggered))


# ---------------------------------------------------------------------------
# Top-level marker helpers
# ---------------------------------------------------------------------------

def _make_markers(
    provider: str,
    model: str,
    prompt_version_value: str,
) -> dict:
    """Build the top-level marker dict for a cache file."""
    return {
        "_cache_version": DIAGRAM_CACHE_VERSION,
        "_provider_version": provider,
        "_model_version": model,
        "_schema_version": DIAGRAM_SCHEMA_VERSION,
        "_pipeline_version": DIAGRAM_PIPELINE_VERSION,
        "_image_strategy_version": DIAGRAM_IMAGE_STRATEGY_VERSION,
        "_diagram_prompt_version": prompt_version_value,
    }


def _markers_match(cache: dict, markers: dict) -> bool:
    """Check if all top-level markers match."""
    for key, value in markers.items():
        if cache.get(key) != value:
            return False
    return True


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------

def _cache_path(cache_dir: Path, filename: str) -> Path:
    return cache_dir / filename


def load_stage_cache(
    cache_dir: Path | None,
    stage: str,
    provider: str,
    model: str,
    prompt_text: str,
) -> dict:
    """Load a stage cache file.  Returns empty dict on any failure or version mismatch.

    Args:
        cache_dir: Directory containing cache files, or None.
        stage: One of "pass_a", "post_b", "final".
        provider: Current provider name.
        model: Current model name.
        prompt_text: Current prompt text (for prompt version check).

    Returns:
        The cache dict (entries keyed by image hash), or empty dict.
    """
    if cache_dir is None:
        return {}

    filenames = {
        "pass_a": _PASS_A_FILENAME,
        "post_b": _POST_B_FILENAME,
        "final": _FINAL_FILENAME,
    }
    filename = filenames.get(stage)
    if filename is None:
        logger.warning("Unknown diagram cache stage: %s", stage)
        return {}

    path = _cache_path(cache_dir, filename)
    if not path.exists():
        return {}

    try:
        cache = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load diagram cache %s: %s", path.name, e)
        return {}

    if not isinstance(cache, dict):
        return {}

    # Validate markers
    expected_markers = _make_markers(provider, model, _prompt_version(prompt_text))
    if not _markers_match(cache, expected_markers):
        logger.info(
            "Diagram cache %s invalidated: version mismatch",
            path.name,
        )
        return {}

    return cache


def load_stale_entry(
    cache_dir: Path | None,
    stage: str,
    image_hash: str,
) -> dict | None:
    """Load a single entry from disk WITHOUT marker validation.

    Used for IoU-based ID inheritance when the active cache has been
    invalidated by a marker change. Returns the raw entry dict or None.
    """
    if cache_dir is None:
        return None

    filenames = {
        "pass_a": _PASS_A_FILENAME,
        "post_b": _POST_B_FILENAME,
        "final": _FINAL_FILENAME,
    }
    filename = filenames.get(stage)
    if filename is None:
        return None

    path = _cache_path(cache_dir, filename)
    if not path.exists():
        return None

    try:
        cache = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(cache, dict):
        return None

    entry = cache.get(image_hash)
    if isinstance(entry, dict):
        return entry
    return None


def save_stage_cache(
    cache_dir: Path | None,
    stage: str,
    cache: dict,
    provider: str,
    model: str,
    prompt_text: str,
) -> None:
    """Save a stage cache file with updated markers.

    Always writes immediately (per-miss durability).
    """
    if cache_dir is None:
        return

    filenames = {
        "pass_a": _PASS_A_FILENAME,
        "post_b": _POST_B_FILENAME,
        "final": _FINAL_FILENAME,
    }
    filename = filenames.get(stage)
    if filename is None:
        logger.warning("Unknown diagram cache stage: %s", stage)
        return

    # Inject/update markers
    markers = _make_markers(provider, model, _prompt_version(prompt_text))
    cache.update(markers)

    path = _cache_path(cache_dir, filename)
    try:
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(cache, indent=2, default=str))
        tmp_path.rename(path)
    except OSError as e:
        logger.warning("Failed to write diagram cache %s: %s", path.name, e)


def check_entry(
    cache: dict,
    image_hash: str,
    dependency_hashes: dict[str, str],
) -> dict | None:
    """Check if a cache entry exists and all dependency hashes match.

    Returns the cached entry dict if valid, or None.
    m7: Looks for both prefixed (_dep_) and raw dep keys for backward compat.
    """
    entry = cache.get(image_hash)
    if not isinstance(entry, dict):
        return None

    for key, expected in dependency_hashes.items():
        dep_key = key if key.startswith("_dep_") else f"_dep_{key}"
        # Check both prefixed and legacy raw key
        actual = entry.get(dep_key, entry.get(key))
        if actual != expected:
            logger.debug(
                "Diagram cache entry %s: dependency %s mismatch",
                image_hash[:8], key,
            )
            return None

    return entry


def store_entry(
    cache: dict,
    image_hash: str,
    data: dict,
    dependency_hashes: dict[str, str],
    provider: str,
    model: str,
) -> None:
    """Store a cache entry with dependency hashes and provenance.

    m7: Dep hash keys are stored with `_dep_` prefix to avoid collision
    with data keys.
    """
    entry = dict(data)
    # m7: Prefix dep keys to prevent collision with data keys
    for k, v in dependency_hashes.items():
        dep_key = k if k.startswith("_dep_") else f"_dep_{k}"
        entry[dep_key] = v
    entry["_provider"] = provider
    entry["_model"] = model
    cache[image_hash] = entry
