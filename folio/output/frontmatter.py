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
    source_type: str,
    version_info: VersionInfo,
    analyses: dict[int, SlideAnalysis],
    subtype: str = "research",
    client: Optional[str] = None,
    engagement: Optional[str] = None,
    industry: Optional[list[str]] = None,
    extra_tags: Optional[list[str]] = None,
    existing_frontmatter: Optional[dict] = None,
    reconciliation_metadata: Optional[dict] = None,
) -> str:
    """Generate YAML frontmatter conforming to Folio Ontology v2 schema.

    Args:
        title: Human-readable deck title.
        deck_id: Date-based ID following convention.
        source_relative_path: Relative path to source file.
        source_hash: SHA256 hash (12 char prefix).
        source_type: Source format ("deck" or "pdf").
        version_info: Current version metadata.
        analyses: Per-slide LLM analyses.
        subtype: Evidence subtype (default "research").
        client: Client name (optional at L0).
        engagement: Engagement identifier (optional at L0).
        industry: Industry tags (optional).
        extra_tags: Manual tags to merge with auto-generated.
        existing_frontmatter: Preserved fields from prior conversion.
        reconciliation_metadata: Text reconciliation diagnostics.

    Returns:
        YAML frontmatter string including --- delimiters.
    """
    # Collect frameworks and slide types from analyses
    frameworks = _collect_unique(analyses, "framework", exclude={"none", "pending"})
    slide_types = _collect_unique(analyses, "slide_type", exclude={"unknown", "pending"})

    # Auto-generate tags from frameworks and slide types, merge manual tags
    tags = _generate_tags(frameworks, slide_types, title)
    if extra_tags:
        tags = sorted(set(tags) | set(extra_tags))

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Preserve id and created from existing frontmatter on reconversion
    preserved_id = deck_id
    preserved_created = now_str
    if existing_frontmatter:
        preserved_id = existing_frontmatter.get("id", deck_id)
        preserved_created = existing_frontmatter.get("created", now_str)

    # Build frontmatter in semantic group order:
    # Identity > Lifecycle > Source > Temporal > Engagement > Content > Extensions
    frontmatter = {
        # Identity
        "id": preserved_id,
        "title": title,
        "type": "evidence",
        "subtype": subtype,
        # Lifecycle
        "status": "active",
        "authority": "captured",
        "curation_level": "L0",
        # Source
        "source": source_relative_path,
        "source_hash": source_hash,
        "source_type": source_type,
        "version": version_info.version,
        # Temporal
        "created": preserved_created,
        "modified": now_str,
        "converted": now_str,
        # Content classification
        "slide_count": version_info.slide_count,
    }

    # Engagement (optional)
    if client:
        frontmatter["client"] = client
    if engagement:
        frontmatter["engagement"] = engagement
    if industry:
        frontmatter["industry"] = sorted(industry)

    # Content tags
    if frameworks:
        frontmatter["frameworks"] = sorted(frameworks)
    if slide_types:
        frontmatter["slide_types"] = sorted(slide_types)
    if tags:
        frontmatter["tags"] = sorted(tags)

    # Reconciliation metadata
    if reconciliation_metadata:
        frontmatter.update(reconciliation_metadata)

    # Grounding summary from evidence
    grounding = _compute_grounding_summary(analyses)
    if grounding["total_claims"] > 0:
        frontmatter["grounding_summary"] = grounding

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
    """Collect unique values of a field across all slide analyses.

    Skips slides where evidence exists but none is validated (all unvalidated).
    Slides with no evidence (no grounding attempted) are still included.
    """
    exclude = exclude or set()
    values = set()
    for analysis in analyses.values():
        evidence = getattr(analysis, "evidence", [])
        if evidence and not any(ev.get("validated", False) for ev in evidence):
            continue  # All evidence unvalidated — skip
        value = getattr(analysis, field, "")
        if value and value not in exclude:
            values.add(value)
    return sorted(values)


def _compute_grounding_summary(analyses: dict[int, SlideAnalysis]) -> dict:
    """Compute aggregate grounding statistics from all slide analyses."""
    total = 0
    high = 0
    medium = 0
    low = 0
    validated = 0
    unvalidated = 0
    pass_1 = 0
    pass_2 = 0
    pass_2_slides = set()

    for slide_num, analysis in analyses.items():
        for ev in getattr(analysis, "evidence", []):
            total += 1
            conf = ev.get("confidence", "medium")
            if conf == "high":
                high += 1
            elif conf == "medium":
                medium += 1
            else:
                low += 1

            if ev.get("validated", False):
                validated += 1
            else:
                unvalidated += 1

            pass_num = ev.get("pass", 1)
            if pass_num == 2:
                pass_2 += 1
                pass_2_slides.add(slide_num)
            else:
                pass_1 += 1

    summary = {
        "total_claims": total,
        "high_confidence": high,
        "medium_confidence": medium,
        "low_confidence": low,
        "validated": validated,
        "unvalidated": unvalidated,
    }

    if pass_2 > 0:
        summary["pass_1_claims"] = pass_1
        summary["pass_2_claims"] = pass_2
        summary["pass_2_slides"] = len(pass_2_slides)

    return summary


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
    noise = {
        "the", "a", "an", "and", "or", "for", "of", "in", "to", "is", "by",
        "v1", "v2", "v3", "v4", "v5", "final", "draft", "rev", "copy", "version",
    }
    for word in title_words:
        if word not in noise and len(word) > 2:
            tags.add(word)

    return sorted(tags)
