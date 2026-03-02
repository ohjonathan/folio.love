"""Markdown assembly: combine all pipeline outputs into final document."""

from pathlib import Path
from typing import Optional

from ..pipeline.analysis import SlideAnalysis
from ..tracking.versions import VersionInfo, ChangeSet


def assemble(
    title: str,
    frontmatter: str,
    source_display_path: str,
    version_info: VersionInfo,
    slide_texts: dict[int, str],
    slide_analyses: dict[int, SlideAnalysis],
    slide_count: int,
    version_history: list[dict],
) -> str:
    """Assemble the complete markdown document.

    Args:
        title: Deck title.
        frontmatter: Pre-generated YAML frontmatter string.
        source_display_path: Source path for display in header.
        version_info: Current version metadata.
        slide_texts: Verbatim text per slide.
        slide_analyses: LLM analysis per slide.
        slide_count: Total number of slides (from images, the authoritative count).
        version_history: Full version history list.

    Returns:
        Complete markdown document as string.
    """
    sections = []

    # Frontmatter
    sections.append(frontmatter)
    sections.append("")

    # Title and header
    sections.append(f"# {title}")
    sections.append("")
    sections.append(f"**Source:** `{source_display_path}`  ")
    sections.append(
        f"**Version:** {version_info.version} | "
        f"**Converted:** {version_info.timestamp[:10]}  "
    )
    status_icon = "✓" if not version_info.changes.has_changes or version_info.version == 1 else "△"
    sections.append(f"**Status:** {status_icon} Current")
    sections.append("")

    # Recent changes (if not first version)
    if version_info.version > 1 and version_info.changes.has_changes:
        sections.append(_format_changes(version_info))
        sections.append("")

    sections.append("---")
    sections.append("")

    # Per-slide sections
    for slide_num in range(1, slide_count + 1):
        slide_section = _format_slide(
            slide_num=slide_num,
            text=slide_texts.get(slide_num),
            analysis=slide_analyses.get(slide_num),
            is_modified=slide_num in version_info.changes.modified,
            is_added=slide_num in version_info.changes.added,
        )
        sections.append(slide_section)

    # Version history table
    if version_history:
        sections.append(_format_version_history(version_history))

    return "\n".join(sections)


def _format_changes(version_info: VersionInfo) -> str:
    """Format the 'Recent Changes' section."""
    changes = version_info.changes
    lines = ["## Recent Changes", ""]

    modified = ", ".join(str(s) for s in changes.modified) if changes.modified else "—"
    added = ", ".join(str(s) for s in changes.added) if changes.added else "—"
    removed = ", ".join(str(s) for s in changes.removed) if changes.removed else "—"

    lines.append("| Slides Modified | Slides Added | Slides Removed |")
    lines.append("|-----------------|--------------|----------------|")
    lines.append(f"| {modified} | {added} | {removed} |")
    lines.append("")

    if version_info.note:
        lines.append(f"**Note:** {version_info.note}")

    return "\n".join(lines)


def _format_slide(
    slide_num: int,
    text: Optional[str],
    analysis: Optional[SlideAnalysis],
    is_modified: bool = False,
    is_added: bool = False,
) -> str:
    """Format a single slide section."""
    lines = []

    # Header with modification marker
    header = f"## Slide {slide_num}"
    if is_modified:
        header += " *(modified)*"
    elif is_added:
        header += " *(new)*"
    lines.append(header)
    lines.append("")

    # Image
    lines.append(f"![Slide {slide_num}](slides/slide-{slide_num:03d}.png)")
    lines.append("")

    # Verbatim text
    if text:
        lines.append("### Text (Verbatim)")
        lines.append("")
        # Blockquote format for visual distinction
        for line in text.split("\n"):
            lines.append(f"> {line}" if line.strip() else ">")
        lines.append("")

    # Analysis
    if analysis and analysis.slide_type != "pending":
        lines.append("### Analysis")
        lines.append("")
        lines.append(f"**Slide Type:** {analysis.slide_type}  ")
        lines.append(f"**Framework:** {analysis.framework}  ")
        if analysis.visual_description:
            lines.append(f"**Visual Description:** {analysis.visual_description}  ")
        if analysis.key_data:
            lines.append(f"**Key Data:** {analysis.key_data}  ")
        if analysis.main_insight:
            lines.append(f"**Main Insight:** {analysis.main_insight}")
        lines.append("")
    elif analysis and analysis.slide_type == "pending":
        lines.append("### Analysis")
        lines.append("")
        lines.append("*[Analysis pending — set ANTHROPIC_API_KEY to enable]*")
        lines.append("")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def _format_version_history(history: list[dict]) -> str:
    """Format the version history table."""
    lines = [
        "## Version History",
        "",
        "| Version | Date | Changes | Note |",
        "|---------|------|---------|------|",
    ]

    for v in reversed(history):
        changes_parts = []
        ch = v.get("changes", {})
        if ch.get("added"):
            count = len(ch["added"])
            changes_parts.append(
                f"Initial ({count} slides)" if v["version"] == 1
                else f"{count} added"
            )
        if ch.get("modified"):
            changes_parts.append(f"{len(ch['modified'])} modified")
        if ch.get("removed"):
            changes_parts.append(f"{len(ch['removed'])} removed")

        changes_str = ", ".join(changes_parts) if changes_parts else "No changes"
        note = v.get("note") or "—"
        date = v["timestamp"][:10]

        lines.append(f"| v{v['version']} | {date} | {changes_str} | {note} |")

    lines.append("")
    return "\n".join(lines)
