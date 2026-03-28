"""Heading-aware markdown section parser for enrich body targeting.

Implements spec D10: heading-aware parsing for identifying machine-owned
sections. Regex-only global replacement is forbidden; this module provides
subtree selection by heading boundaries.

Reuses the fenced-code-block detection pattern from
``folio/output/diagram_notes.py`` to ensure headings inside fences are
ignored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Fenced code block detection (reused from diagram_notes.py:493-506)
# ---------------------------------------------------------------------------

def _fenced_block_ranges(content: str) -> list[tuple[int, int]]:
    """Return (start, end) char ranges of all fenced code blocks in content."""
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


# ---------------------------------------------------------------------------
# Heading regex
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Section:
    """A parsed markdown heading section."""

    heading: str        # e.g. "## Summary"
    level: int          # 2 for ##, 3 for ###
    start: int          # char offset of heading line start
    end: int            # char offset of next same-or-higher heading (or EOF)
    body_start: int     # char offset after heading line
    children: list["Section"] = field(default_factory=list)


# ---------------------------------------------------------------------------
# MarkdownDocument
# ---------------------------------------------------------------------------

class MarkdownDocument:
    """Heading-aware markdown document parser.

    Parses a markdown string into a tree of ``Section`` objects,
    respecting fenced code blocks (headings inside fences are not real
    headings).
    """

    def __init__(self, content: str) -> None:
        self._content = content
        self._fence_ranges = _fenced_block_ranges(content)
        self._all_sections: list[Section] = []
        self._top_level: list[Section] = []
        self._parse()

    # -- public API ----------------------------------------------------------

    @property
    def content(self) -> str:
        """The original document content."""
        return self._content

    @property
    def sections(self) -> list[Section]:
        """Flat list of all top-level Section objects."""
        return list(self._top_level)

    @property
    def all_sections(self) -> list[Section]:
        """Flat list of *every* Section (including nested children)."""
        return list(self._all_sections)

    def get_section(self, heading: str) -> Section | None:
        """Find a section by exact heading match (e.g. ``"## Summary"``)."""
        for section in self._all_sections:
            if section.heading == heading:
                return section
        return None

    def get_subtree(self, heading: str) -> str | None:
        """Return full content under heading including children."""
        section = self.get_section(heading)
        if section is None:
            return None
        return self._content[section.body_start:section.end]

    def get_managed_sections(self, doc_type: str) -> dict[str, Section]:
        """Return only machine-owned sections for the given document type.

        For ``"evidence"``: every ``### Analysis`` subsection under any
        ``## Slide N`` parent, plus ``## Related``.

        For ``"interaction"``: ``## Entities Mentioned`` and
        ``## Impact on Hypotheses``, plus ``## Related``.

        If expected managed sections cannot be found, returns empty dict
        (triggers protected fallback per D11).
        """
        if doc_type == "evidence":
            return self._get_evidence_managed()
        elif doc_type == "interaction":
            return self._get_interaction_managed()
        return {}

    def replace_section_body(self, section: Section, new_body: str) -> str:
        """Return new full document content with section body replaced.

        Replaces the content between ``section.body_start`` and
        ``section.end`` with ``new_body``, preserving heading and
        neighboring sections.
        """
        return (
            self._content[:section.body_start]
            + new_body
            + self._content[section.end:]
        )

    def insert_before_section(self, heading: str, content: str) -> str:
        """Insert content before the named section.

        Returns new full document content. If the section is not found,
        returns the original content unchanged.
        """
        section = self.get_section(heading)
        if section is None:
            return self._content
        return (
            self._content[:section.start]
            + content
            + self._content[section.start:]
        )

    def remove_section(self, heading: str) -> str:
        """Remove a section and its content.

        Returns new full document content with the section removed.
        If the section is not found, returns the original content unchanged.
        """
        section = self.get_section(heading)
        if section is None:
            return self._content
        return (
            self._content[:section.start]
            + self._content[section.end:]
        )

    # -- internal parsing ----------------------------------------------------

    def _parse(self) -> None:
        """Parse heading tree from content."""
        # Collect all real headings (not inside fenced code blocks)
        raw_headings: list[tuple[int, int, str, int]] = []
        for m in _HEADING_RE.finditer(self._content):
            if _is_inside_code_block(m.start(), self._fence_ranges):
                continue
            level = len(m.group(1))
            heading_text = f"{m.group(1)} {m.group(2)}"
            # body_start is one char after the heading line ends
            line_end = m.end()
            if line_end < len(self._content) and self._content[line_end] == "\n":
                body_start = line_end + 1
            else:
                body_start = line_end
            raw_headings.append((m.start(), level, heading_text, body_start))

        if not raw_headings:
            return

        # Assign end offsets: each heading extends until the next heading
        # of same or higher level, or EOF
        sections: list[Section] = []
        for i, (start, level, heading, body_start) in enumerate(raw_headings):
            # Find end: next heading with level <= this one, or EOF
            end = len(self._content)
            for j in range(i + 1, len(raw_headings)):
                if raw_headings[j][1] <= level:
                    end = raw_headings[j][0]
                    break
            sections.append(Section(
                heading=heading,
                level=level,
                start=start,
                end=end,
                body_start=body_start,
            ))

        self._all_sections = sections

        # Build tree: assign children
        for i, section in enumerate(sections):
            for j in range(i + 1, len(sections)):
                child_candidate = sections[j]
                if child_candidate.level <= section.level:
                    break
                if child_candidate.level == section.level + 1:
                    section.children.append(child_candidate)

        # Top-level: sections that are not children of anything
        child_set: set[int] = set()
        for section in sections:
            for child in section.children:
                child_set.add(id(child))
        self._top_level = [s for s in sections if id(s) not in child_set]

    def _get_evidence_managed(self) -> dict[str, Section]:
        """Get managed sections for evidence notes."""
        managed: dict[str, Section] = {}

        # Find all ## Slide N sections and their ### Analysis children
        _slide_re = re.compile(r"^## Slide \d+")
        for section in self._all_sections:
            if section.level == 2 and _slide_re.match(section.heading):
                for child in section.children:
                    if child.heading == "### Analysis":
                        # Key by parent slide heading for uniqueness
                        key = f"{section.heading} > ### Analysis"
                        managed[key] = child

        # Also include ## Related if it exists
        related = self.get_section("## Related")
        if related is not None:
            managed["## Related"] = related

        return managed

    def _get_interaction_managed(self) -> dict[str, Section]:
        """Get managed sections for interaction notes.

        Note: ``## Impact on Hypotheses`` is listed as allowed in the spec
        (D10, §14.1) but no mutation logic exists for it in v1. It is
        excluded from the managed set to avoid false conflict positives
        when humans edit that section.
        """
        managed: dict[str, Section] = {}

        entities = self.get_section("## Entities Mentioned")
        if entities is not None:
            managed["## Entities Mentioned"] = entities

        related = self.get_section("## Related")
        if related is not None:
            managed["## Related"] = related

        return managed
