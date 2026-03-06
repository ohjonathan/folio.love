"""Source file tracking: relative paths, hashing, staleness detection."""

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SourceInfo:
    """Metadata about a source file."""
    absolute_path: Path
    relative_path: str  # Relative to markdown file, forward slashes
    file_hash: str      # SHA256, first 12 chars
    exists: bool
    file_name: str
    file_size: int


def compute_source_info(
    source_path: Path,
    markdown_path: Path,
) -> SourceInfo:
    """Compute source tracking metadata.

    Args:
        source_path: Absolute path to the source file.
        markdown_path: Path where the markdown file will be written.

    Returns:
        SourceInfo with relative path, hash, and existence check.
    """
    source_path = Path(source_path).resolve()
    markdown_dir = Path(markdown_path).resolve().parent

    relative = _compute_relative_path(source_path, markdown_dir)
    file_hash = compute_file_hash(source_path)

    return SourceInfo(
        absolute_path=source_path,
        relative_path=relative,
        file_hash=file_hash,
        exists=source_path.exists(),
        file_name=source_path.name,
        file_size=source_path.stat().st_size if source_path.exists() else 0,
    )


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file, returning first 12 hex chars.

    12 hex chars = 48 bits, giving ~1-in-280-trillion collision probability
    for realistic deck counts (<10,000). Sufficient for staleness detection;
    not intended as a cryptographic identifier.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:12]


def check_staleness(
    markdown_path: Path,
    stored_relative_path: str,
    stored_hash: str,
) -> dict:
    """Check if the source file has changed since conversion.

    Args:
        markdown_path: Path to the markdown file.
        stored_relative_path: Relative path from frontmatter.
        stored_hash: Hash from frontmatter.

    Returns:
        Dict with 'status' ('current', 'stale', or 'missing') and details.
    """
    source_path = resolve_source_path(markdown_path, stored_relative_path)

    if not source_path.exists():
        return {"status": "missing", "source_path": str(source_path)}

    current_hash = compute_file_hash(source_path)

    if current_hash != stored_hash:
        return {
            "status": "stale",
            "stored_hash": stored_hash,
            "current_hash": current_hash,
        }

    return {"status": "current"}


def resolve_source_path(markdown_path: Path, relative_path: str) -> Path:
    """Resolve a relative source path from a markdown file location.

    Args:
        markdown_path: Path to the markdown file.
        relative_path: Relative path stored in frontmatter.

    Returns:
        Resolved absolute path to the source file.
    """
    markdown_dir = Path(markdown_path).resolve().parent
    # relative_path uses forward slashes; Path handles conversion
    resolved = (markdown_dir / relative_path).resolve()
    return resolved


def _compute_relative_path(source_path: Path, from_dir: Path) -> str:
    """Compute relative path from a directory to a file, using forward slashes."""
    rel = os.path.relpath(str(source_path), str(from_dir))
    # Normalize to forward slashes for cross-platform portability
    return rel.replace("\\", "/")
