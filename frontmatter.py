"""Frontmatter generation: Folio v2 schema with ontology-aware fields."""

import re
from datetime import datetime, timezone
from typing import Optional

import yaml

from ..pipeline.analysis import SlideAnalysis
from ..tracking.versions import VersionInfo


def generate(
    title: str,
    deck_id: str,
    source_relative_path: str,
    source_hash: str,
    version_info: VersionInfo,
    analyses: dict[int, SlideAnalysis],
    client: Optional[str] = None,
    engagement: Optional[str] = None,
) -> str:
    """Generate YAML frontmatter conforming to Folio Ontology v2 schema.

    Args:
        title: Human-readable deck title.
        deck_id: Date-based ID following convention.
        source_relative_path: Relative path to source file.
        source_hash: SHA256 hash (12 char prefix).
        version_info: Current version metadata.
        analyses: Per-slide LLM analyses.
        client: Client name (optional at L0).
        engagement: Engagement identifier (optional at L0).

    Returns:
        YAML frontmatter string including --- delimiters.
    """
    # Collect frameworks and slide types from analyses
    frameworks = _collect_unique(analyses, "framework", exclude={"none", "pending"})
    slide_types = _collect_unique(analyses, "slide_type", exclude={"unknown", "pending"})

    # Auto-generate tags from frameworks and slide types
    tags = _generate_tags(frameworks, slide_types, title)

    frontmatter = {
        # Identity
        "id": deck_id,
        "title": title,
        "type": "evidence",
        "subtype": "research",
        # Source tracking
        "source": source_relative_path,
        "source_hash": source_hash,
        "source_type": "deck",
        "version": version_info.version,
        "converted": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Organization
        "status": "current",
        # Ontology
        "authority": "captured",
        "curation_level": "L0",
        # Content classification
        "slide_count": version_info.slide_count,
    }

    # Optional fields
    if client:
        frontmatter["client"] = client
    if engagement:
        frontmatter["engagement"] = engagement
    if frameworks:
        frontmatter["frameworks"] = sorted(frameworks)
    if slide_types:
        frontmatter["slide_types"] = sorted(slide_types)
    if tags:
        frontmatter["tags"] = sorted(tags)

    # Use block style for lists, flow style would be less readable
    yaml_str = yaml.dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    return f"---\n{yaml_str}---"


def _collect_unique(
    analyses: dict[int, SlideAnalysis],
    field: str,
    exclude: set[str] | None = None,
) -> list[str]:
    """Collect unique values of a field across all slide analyses."""
    exclude = exclude or set()
    values = set()
    for analysis in analyses.values():
        value = getattr(analysis, field, "")
        if value and value not in exclude:
            values.add(value)
    return sorted(values)


def _generate_tags(
    frameworks: list[str],
    slide_types: list[str],
    title: str,
) -> list[str]:
    """Auto-generate tags from analysis results and title.

    This provides a starting point. Human curation at L1 will refine.
    """
    tags = set()

    # Add frameworks as tags
    tags.update(frameworks)

    # Extract meaningful words from title
    title_words = re.findall(r"[a-z][a-z-]+", title.lower().replace("_", "-"))
    # Filter out noise words
    noise = {"the", "a", "an", "and", "or", "for", "of", "in", "to", "is", "by"}
    for word in title_words:
        if word not in noise and len(word) > 2:
            tags.add(word)

    return sorted(tags)
