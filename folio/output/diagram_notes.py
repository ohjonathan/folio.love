"""Standalone diagram note assembly: emission, freeze detection, and hydration."""

import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from ..pipeline.analysis import (
    DiagramAnalysis,
    DiagramEdge,
    DiagramGraph,
    DiagramGroup,
    DiagramNode,
)

logger = logging.getLogger(__name__)

# Diagram type label mapping for human-readable titles
_TYPE_LABELS: dict[str, str] = {
    "architecture": "Architecture",
    "data-flow": "Data Flow",
    "sequence": "Sequence",
    "entity-relationship": "Entity Relationship",
    "state-machine": "State Machine",
    "network": "Network",
    "deployment": "Deployment",
    "class": "Class",
    "unsupported": "Unsupported",
    "unknown": "Unknown",
}

# Managed keys that are overwritten from fresh analysis on non-frozen reconversion
_MANAGED_KEYS = {
    "type", "diagram_type", "title", "source_deck", "source_page",
    "extraction_confidence", "confidence_reasoning",
    "review_required", "review_questions", "abstained",
    "components", "technologies", "tags",
    "_extraction_metadata",
}

# Preserved keys that survive non-frozen reconversion
_PRESERVED_KEYS = {"human_overrides", "_review_history", "folio_freeze"}

# Shared noise words for tag generation (m6 fix: single source of truth)
NOISE_WORDS = frozenset({
    "the", "a", "an", "and", "or", "for", "of", "in", "to", "is", "by",
    "v1", "v2", "v3", "v4", "v5", "final", "draft", "rev", "copy", "version",
})

# Generic terms filtered from technology tags (m7 fix)
_GENERIC_TECH_TERMS = frozenset({
    "service", "system", "component", "module", "layer", "server", "client",
    "platform", "framework", "tool", "application", "app", "api",
})


@dataclass(frozen=True)
class DiagramNoteRef:
    """Reference to a standalone diagram note for deck transclusion."""
    basename: str          # basename without .md, used for Obsidian links
    path: Path
    has_diagram_section: bool
    has_components_section: bool


@dataclass
class FrozenDiagramPayload:
    """Hydrated analysis from a frozen standalone note."""
    analysis: DiagramAnalysis
    note_ref: DiagramNoteRef
    frontmatter: dict[str, Any]


def _diagram_type_label(diagram_type: str) -> str:
    """Convert diagram_type to a human-readable label."""
    if diagram_type in _TYPE_LABELS:
        return _TYPE_LABELS[diagram_type]
    # Fallback: title-case with hyphens replaced by spaces
    return diagram_type.replace("-", " ").title()


def build_note_basename(created_date: str, deck_slug: str, page_number: int) -> str:
    """Build stable standalone note basename (without .md).

    Args:
        created_date: Date in YYYYMMDD form.
        deck_slug: Slug derived from deck name.
        page_number: 1-indexed page number.

    Returns:
        Basename like ``20260314-system-design-review-diagram-p007``.
    """
    return f"{created_date}-{deck_slug}-diagram-p{page_number:03d}"


def _build_note_frontmatter(
    analysis: DiagramAnalysis,
    deck_slug: str,
    deck_title: str,
    page_number: int,
    *,
    existing_frontmatter: dict | None = None,
) -> dict[str, Any]:
    """Build frontmatter dict for a standalone diagram note."""
    type_label = _diagram_type_label(analysis.diagram_type)
    title = f"{deck_title} — {type_label} (Page {page_number})"

    # Components: deduped sorted node labels from graph
    components: list[str] = []
    technologies: list[str] = []
    if analysis.graph and analysis.graph.nodes:
        seen_labels: set[str] = set()
        seen_techs: set[str] = set()
        for node in analysis.graph.nodes:
            if node.label and node.label not in seen_labels:
                seen_labels.add(node.label)
                components.append(node.label)
            if node.technology and node.technology not in seen_techs:
                seen_techs.add(node.technology)
                technologies.append(node.technology)
        components = sorted(components)
        technologies = sorted(technologies)

    # Tags: diagram + type + title words + technology slugs
    tags: set[str] = {"diagram"}
    if analysis.diagram_type and analysis.diagram_type != "unknown":
        tags.add(analysis.diagram_type)
    # Title words from deck_title (m6 fix: use shared NOISE_WORDS)
    title_words = re.findall(r"[a-z][a-z-]+", deck_title.lower().replace("_", "-"))
    for word in title_words:
        if word not in NOISE_WORDS and len(word) > 2:
            tags.add(word)
    # Technology slugs (m7 fix: filter generic terms)
    for tech in technologies:
        slug = tech.strip("[]").lower().replace(" ", "-").replace("_", "-")
        if slug and slug not in _GENERIC_TECH_TERMS:
            tags.add(slug)

    # Build ordered frontmatter
    fm: dict[str, Any] = {
        "type": "diagram",
        "diagram_type": analysis.diagram_type,
        "title": title,
        "source_deck": f"[[{deck_slug}]]",
        "source_page": page_number,
        "extraction_confidence": analysis.diagram_confidence,
        "confidence_reasoning": analysis.confidence_reasoning or "",
        "review_required": analysis.review_required,
        "review_questions": list(analysis.review_questions),
        "abstained": analysis.abstained,
        "folio_freeze": False,
        "components": components,
        "technologies": technologies,
        "tags": sorted(tags),
        "human_overrides": {},
        "_review_history": [],
    }

    # m1 fix: always emit _extraction_metadata (even as {} when empty)
    fm["_extraction_metadata"] = dict(analysis._extraction_metadata) if analysis._extraction_metadata else {}

    # Preserve user-authored keys from existing note
    if isinstance(existing_frontmatter, dict):
        for key in _PRESERVED_KEYS:
            if key in existing_frontmatter:
                fm[key] = existing_frontmatter[key]
        # Preserve unknown user-authored keys
        all_known = _MANAGED_KEYS | _PRESERVED_KEYS
        for key, value in existing_frontmatter.items():
            if key not in all_known:
                fm[key] = value

    return fm


def _build_note_body(
    analysis: DiagramAnalysis,
    deck_slug: str,
    page_number: int,
    frontmatter: dict[str, Any],
) -> tuple[str, bool, bool]:
    """Build standalone note body.

    Returns:
        (body_text, has_diagram_section, has_components_section)
    """
    title = frontmatter["title"]
    lines: list[str] = []

    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"Extracted from [[{deck_slug}]], page {page_number}.")
    lines.append("")

    has_diagram = False
    has_components = False

    if analysis.abstained and analysis.graph is None:
        # Graphless abstained: omit Diagram, Components, Connections, Summary
        reasoning = analysis.confidence_reasoning or "Diagram extraction abstained."
        lines.append(f"> {reasoning}")
        lines.append("")
        # Extraction notes with review questions if any
        if analysis.review_questions or analysis.uncertainties:
            lines.append("## Extraction Notes")
            lines.append("")
            for item in (analysis.uncertainties or []):
                lines.append(f"> {item}")
            for item in (analysis.review_questions or []):
                lines.append(f"> {item}")
            lines.append("")
    else:
        # Has graph (whether accepted or abstained-with-graph)
        if analysis.abstained and analysis.graph is not None:
            lines.append(
                "> Candidate extraction rendered for reviewer context. "
                "This diagram abstained from final acceptance."
            )
            lines.append("")

        # Diagram section
        if analysis.mermaid:
            has_diagram = True
            lines.append("## Diagram")
            lines.append("")
            lines.append("```mermaid")
            lines.append(analysis.mermaid)
            lines.append("```")
            lines.append("")
        else:
            # Missing mermaid on rendered graph — warn but keep valid
            lines.append("## Diagram")
            lines.append("")
            lines.append("> Mermaid rendering not available for this diagram.")
            lines.append("")
            has_diagram = True

        # Components section
        if analysis.component_table:
            has_components = True
            lines.append("## Components")
            lines.append("")
            lines.append(analysis.component_table)
            lines.append("")
        else:
            lines.append("## Components")
            lines.append("")
            lines.append("> No component table available.")
            lines.append("")
            has_components = True

        # Connections section
        if analysis.connection_table:
            lines.append("## Connections")
            lines.append("")
            lines.append(analysis.connection_table)
            lines.append("")
        else:
            lines.append("## Connections")
            lines.append("")
            lines.append("> No connection table available.")
            lines.append("")

        # Summary
        if analysis.description:
            lines.append("## Summary")
            lines.append("")
            lines.append(analysis.description)
            lines.append("")
        else:
            lines.append("## Summary")
            lines.append("")
            lines.append("> No description available.")
            lines.append("")

        # Extraction Notes
        lines.append("## Extraction Notes")
        lines.append("")
        has_notes = False
        for item in (analysis.uncertainties or []):
            lines.append(f"> {item}")
            has_notes = True
        for item in (analysis.review_questions or []):
            lines.append(f"> {item}")
            has_notes = True
        if not has_notes:
            if analysis.abstained and analysis.graph is not None:
                lines.append(
                    "> Candidate extraction — not accepted due to low confidence."
                )
            else:
                lines.append("> No uncertainties flagged.")
        lines.append("")

    # Divider and source image
    lines.append("---")
    lines.append("")
    lines.append(f"![[slides/slide-{page_number:03d}.png]]")

    return "\n".join(lines), has_diagram, has_components


def _read_note_frontmatter(note_path: Path) -> dict | None:
    """Parse frontmatter from an existing standalone diagram note."""
    try:
        content = note_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return _parse_frontmatter_from_content(content)


def _parse_frontmatter_from_content(content: str) -> dict | None:
    """Parse YAML frontmatter from already-read markdown content."""
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
    try:
        fm = yaml.safe_load(yaml_block)
        if isinstance(fm, dict):
            return fm
    except yaml.YAMLError:
        pass
    return None


def _has_section_heading(content: str, section_name: str) -> bool:
    """Check if a ## heading exists outside fenced code blocks."""
    code_ranges = _fenced_block_ranges(content)
    for m in re.finditer(rf"^## {re.escape(section_name)}\s*$", content, re.MULTILINE):
        if not _is_inside_code_block(m.start(), code_ranges):
            return True
    return False


def _split_table_cells(line: str) -> list[str]:
    """Split a markdown table row on unescaped pipes, then unescape.

    PR 5's ``_escape_table_cell()`` escapes literal ``|`` as ``\\|``.
    A naive ``split('|')`` corrupts cells containing escaped pipes.
    """
    # Split on pipe NOT preceded by backslash
    parts = re.split(r'(?<!\\)\|', line)
    # Strip outer empty entries from leading/trailing | delimiters
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    # Unescape \| -> | in each cell
    return [p.strip().replace('\\|', '|') for p in parts]


def _parse_table_rows(table_text: str) -> list[dict[str, str]]:
    """Parse a markdown table into a list of header->value dicts."""
    lines = [line.strip() for line in table_text.strip().split("\n") if line.strip()]
    if len(lines) < 3:
        return []  # Need header, separator, at least one row
    # Parse header
    headers = _split_table_cells(lines[0])
    # Skip separator line (lines[1])
    rows = []
    for line in lines[2:]:
        cells = _split_table_cells(line)
        row = {}
        for j, h in enumerate(headers):
            row[h] = cells[j] if j < len(cells) else ""
        rows.append(row)
    return rows


def _hydrate_graph_from_tables(
    component_table: str | None,
    connection_table: str | None,
) -> DiagramGraph | None:
    """Hydrate a DiagramGraph from Components and Connections markdown tables."""
    if not component_table:
        return None

    nodes: list[DiagramNode] = []
    groups: list[DiagramGroup] = []
    label_to_id: dict[str, str] = {}
    group_names: dict[str, str] = {}  # group name -> group id

    comp_rows = _parse_table_rows(component_table)
    if not comp_rows:
        return None

    # m10 fix: dict for O(1) group lookup by ID
    group_by_id: dict[str, DiagramGroup] = {}

    for i, row in enumerate(comp_rows):
        label = row.get("Component", "").strip()
        if not label:
            continue
        # m5 note: IDs are sequential (node_0, node_1...) and may differ from
        # original extraction IDs. human_overrides keyed by original IDs
        # (e.g. node_3) will be orphaned. This is a known limitation of
        # table-based hydration; original IDs are not preserved in tables.
        node_id = f"node_{i}"
        kind = row.get("Type", "unknown").strip() or "unknown"
        tech_raw = row.get("Technology", "").strip()
        technology = tech_raw.strip("[]") if tech_raw else None
        group_name = row.get("Group", "").strip()
        source_text = row.get("Source", "vision").strip() or "vision"
        conf_str = row.get("Confidence", "1.0").strip()
        try:
            confidence = float(conf_str)
        except (ValueError, TypeError):
            confidence = 1.0

        group_id = None
        if group_name:
            if group_name not in group_names:
                gid = f"group_{len(group_names)}"
                group_names[group_name] = gid
                g = DiagramGroup(id=gid, name=group_name, contains=[])
                groups.append(g)
                group_by_id[gid] = g
            group_id = group_names[group_name]
            # m10 fix: O(1) dict lookup instead of O(n) list scan
            group_by_id[group_id].contains.append(node_id)

        nodes.append(DiagramNode(
            id=node_id,
            label=label,
            kind=kind,
            group_id=group_id,
            technology=technology,
            source_text=source_text,
            confidence=confidence,
        ))
        label_to_id[label] = node_id

    edges: list[DiagramEdge] = []
    if connection_table:
        conn_rows = _parse_table_rows(connection_table)
        direction_map = {
            "→": "forward",
            "←": "reverse",
            "↔": "bidirectional",
            "—": "none",
            "?": "none",
        }
        for i, row in enumerate(conn_rows):
            from_label = row.get("From", "").strip()
            to_label = row.get("To", "").strip()
            if not from_label or not to_label:
                continue
            source_id = label_to_id.get(from_label, from_label)
            target_id = label_to_id.get(to_label, to_label)
            dir_symbol = row.get("Direction", "→").strip()
            direction = direction_map.get(dir_symbol, "forward")
            edge_label = row.get("Label", "").strip() or None
            conf_str = row.get("Confidence", "1.0").strip()
            try:
                confidence = float(conf_str)
            except (ValueError, TypeError):
                confidence = 1.0
            edges.append(DiagramEdge(
                id=f"edge_{i}",
                source_id=source_id,
                target_id=target_id,
                label=edge_label,
                direction=direction,
                confidence=confidence,
            ))

    return DiagramGraph(nodes=nodes, edges=edges, groups=groups)


def _fenced_block_ranges(content: str) -> list[tuple[int, int]]:
    """Return (start, end) byte ranges of all fenced code blocks in content."""
    ranges = []
    for m in re.finditer(r"^```[^\n]*\n.*?^```", content, re.MULTILINE | re.DOTALL):
        ranges.append((m.start(), m.end()))
    return ranges


def _is_inside_code_block(pos: int, ranges: list[tuple[int, int]]) -> bool:
    """Check if a position falls inside any fenced code block range."""
    for start, end in ranges:
        if start <= pos < end:
            return True
    return False


def _extract_section(content: str, section_name: str) -> str | None:
    """Extract the text under a ## section heading from markdown content.

    Headings inside fenced code blocks are ignored (M5 fix).
    Uses direct boundary detection in original content (S-NEW-1 fix).
    """
    code_ranges = _fenced_block_ranges(content)
    # m-NEW-1 fix: use \s*$ (like _has_section_heading) for consistency
    pattern = rf"^## {re.escape(section_name)}\s*$"

    # Find the target heading outside code blocks
    target_match = None
    for m in re.finditer(pattern, content, re.MULTILINE):
        if not _is_inside_code_block(m.start(), code_ranges):
            target_match = m
            break
    if not target_match:
        return None

    start = target_match.end()

    # Find end boundary: next ## heading outside code blocks, or --- divider, or EOF
    end = len(content)
    for m in re.finditer(r"^## ", content[start:], re.MULTILINE):
        abs_pos = start + m.start()
        if not _is_inside_code_block(abs_pos, code_ranges):
            end = abs_pos
            break
    else:
        # No next heading found — check for --- divider outside code blocks
        for m in re.finditer(r"^---\s*$", content[start:], re.MULTILINE):
            abs_pos = start + m.start()
            if not _is_inside_code_block(abs_pos, code_ranges):
                end = abs_pos
                break

    return content[start:end].strip()


def discover_frozen_notes(
    deck_dir: Path,
    deck_slug: str,
    created_date: str,
    page_profiles: dict[int, Any],
) -> dict[int, FrozenDiagramPayload]:
    """Discover existing standalone notes with folio_freeze: true.

    Scans for diagram notes matching the expected naming pattern and
    hydrates DiagramAnalysis from their markdown tables.

    Args:
        deck_dir: Directory containing the deck and its notes.
        deck_slug: Slug used in note naming.
        created_date: YYYYMMDD date prefix for stable naming.
        page_profiles: Page classification profiles.

    Returns:
        Map of page_number -> FrozenDiagramPayload for frozen notes.
    """
    frozen: dict[int, FrozenDiagramPayload] = {}

    for page_num, profile in page_profiles.items():
        classification = getattr(profile, "classification", "text")
        if classification not in ("diagram", "mixed"):
            continue

        basename = build_note_basename(created_date, deck_slug, page_num)
        note_path = deck_dir / f"{basename}.md"
        if not note_path.exists():
            continue

        # m3 fix: single file read for both frontmatter and content
        try:
            content = note_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            logger.warning("Cannot read note %s", note_path)
            continue

        fm = _parse_frontmatter_from_content(content)
        if not isinstance(fm, dict):
            continue
        if not fm.get("folio_freeze"):
            continue

        comp_table = _extract_section(content, "Components")
        conn_table = _extract_section(content, "Connections")
        description = _extract_section(content, "Summary")
        mermaid_section = _extract_section(content, "Diagram")
        mermaid_code = None
        if mermaid_section:
            # Extract from ```mermaid ... ```
            m = re.search(r"```mermaid\s*\n(.*?)```", mermaid_section, re.DOTALL)
            if m:
                mermaid_code = m.group(1).strip()

        # Hydrate graph from tables
        graph = _hydrate_graph_from_tables(comp_table, conn_table)
        if graph is None and comp_table:
            logger.warning(
                "Malformed frozen note tables in %s — partial graph recovery",
                note_path,
            )

        # Build extraction confidence
        try:
            extraction_conf = float(fm.get("extraction_confidence", 0.0))
        except (TypeError, ValueError):
            extraction_conf = 0.0

        analysis = DiagramAnalysis(
            diagram_type=str(fm.get("diagram_type", "unknown")),
            graph=graph,
            mermaid=mermaid_code,
            description=description,
            component_table=comp_table,
            connection_table=conn_table,
            extraction_confidence=extraction_conf,
            diagram_confidence=extraction_conf,
            confidence_reasoning=str(fm.get("confidence_reasoning", "")),
            review_required=bool(fm.get("review_required", False)),
            review_questions=list(fm.get("review_questions", [])),
            abstained=bool(fm.get("abstained", False)),
            _extraction_metadata=dict(fm.get("_extraction_metadata", {})),
        )

        has_diagram = _has_section_heading(content, "Diagram")
        has_components = _has_section_heading(content, "Components")

        note_ref = DiagramNoteRef(
            basename=basename,
            path=note_path,
            has_diagram_section=has_diagram,
            has_components_section=has_components,
        )

        frozen[page_num] = FrozenDiagramPayload(
            analysis=analysis,
            note_ref=note_ref,
            frontmatter=fm,
        )

    return frozen


def emit_diagram_notes(
    deck_dir: Path,
    deck_slug: str,
    deck_title: str,
    created_date: str,
    analyses: dict[int, Any],
    page_profiles: dict[int, Any],
) -> dict[int, DiagramNoteRef]:
    """Emit standalone diagram notes for diagram/mixed pages.

    For frozen notes, returns the existing DiagramNoteRef without rewriting.

    Args:
        deck_dir: Directory containing the deck output.
        deck_slug: Slug for note naming (deck markdown basename without .md).
        deck_title: Human-readable deck title.
        created_date: YYYYMMDD date for stable note naming.
        analyses: Final slide analyses (may include DiagramAnalysis instances).
        page_profiles: Page classification profiles from inspection.

    Returns:
        Map of page_number -> DiagramNoteRef for all diagram-like pages.
    """
    refs: dict[int, DiagramNoteRef] = {}

    for page_num, profile in page_profiles.items():
        classification = getattr(profile, "classification", "text")
        if classification not in ("diagram", "mixed"):
            continue

        analysis = analyses.get(page_num)
        if not isinstance(analysis, DiagramAnalysis):
            continue

        basename = build_note_basename(created_date, deck_slug, page_num)
        note_path = deck_dir / f"{basename}.md"

        # Check for frozen note — return existing ref without rewriting
        # S-NEW-3 fix: single read for both frontmatter and content
        existing_fm = None
        existing_content = None
        if note_path.exists():
            try:
                existing_content = note_path.read_text(encoding="utf-8")
                existing_fm = _parse_frontmatter_from_content(existing_content)
            except (OSError, UnicodeDecodeError):
                pass
        if isinstance(existing_fm, dict) and existing_fm.get("folio_freeze"):
            content = existing_content or ""
            refs[page_num] = DiagramNoteRef(
                basename=basename,
                path=note_path,
                has_diagram_section=_has_section_heading(content, "Diagram"),
                has_components_section=_has_section_heading(content, "Components"),
            )
            continue

        # Build note frontmatter and body
        fm = _build_note_frontmatter(
            analysis, deck_slug, deck_title, page_num,
            existing_frontmatter=existing_fm,
        )
        body, has_diagram, has_components = _build_note_body(
            analysis, deck_slug, page_num, fm,
        )

        # Assemble full note
        yaml_str = yaml.dump(
            fm,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        full_content = f"---\n{yaml_str}---\n\n{body}\n"

        # M1 fix: atomic write (temp file + os.replace)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(deck_dir), suffix=".md.tmp", prefix=".diagram-",
        )
        try:
            # S-NEW-2 fix: set standard permissions (mkstemp creates 0o600)
            os.fchmod(fd, 0o644)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(full_content)
            os.replace(tmp_path, str(note_path))
        except BaseException:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        refs[page_num] = DiagramNoteRef(
            basename=basename,
            path=note_path,
            has_diagram_section=has_diagram,
            has_components_section=has_components,
        )

    return refs
