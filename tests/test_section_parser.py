"""Tests for heading-aware markdown section parser."""

import pytest

from folio.pipeline.section_parser import MarkdownDocument, Section


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

EVIDENCE_NOTE = """\
---
id: test_evidence
type: evidence
---

# Market Sizing Analysis

**Source:** `deck.pptx`

---

## Slide 1

![Slide 1](slides/slide-001.png)

### Text (Verbatim)

> This is verbatim text from slide 1.
> It should not be modified.

### Analysis

**Slide Type:** data
**Framework:** none
**Visual Description:** A bar chart showing market growth.
**Key Data:** Revenue grew 15% YoY.
**Main Insight:** The market is expanding rapidly.

**Evidence:**
- claim: Revenue growth is 15% YoY
  - confidence: high
  - validated: yes

---

## Slide 2

![Slide 2](slides/slide-002.png)

### Text (Verbatim)

> Second slide verbatim text.

### Analysis

**Slide Type:** comparison
**Framework:** none
**Visual Description:** Side-by-side competitor analysis.
**Key Data:** Company A leads by 20%.
**Main Insight:** Competitive advantage is narrowing.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1 | 2026-03-01 | Initial conversion |
"""

INTERACTION_NOTE = """\
---
id: test_interaction
type: interaction
---

# CTO Sync Meeting

Source transcript: `transcript.md` | Version: 1

## Summary

The CTO discussed Q2 roadmap priorities focusing on platform stability.

## Key Findings

### Claims

- Platform stability is the top priority for Q2.
  - quote: "We need to stabilize before we grow"
  - details: strategic, high
  - speaker: CTO

### Data Points

- None captured.

### Decisions

- Freeze feature development for 2 weeks.
  - quote: "Let's freeze features for two weeks"
  - details: operational, high
  - speaker: CTO

### Open Questions

- None captured.

## Entities Mentioned

### People

- [[Jane Smith]]
- [[Bob Johnson]]

### Departments

- [[Engineering]]

### Systems

- [[ServiceNow]]

### Processes

- None

## Quotes / Evidence

- "We need to stabilize before we grow"
  - details: strategic, high
  - speaker: CTO
  - validated: yes

## Impact on Hypotheses

[STUB at L0 — filled during L0→L1 promotion by human, refined at L2 by enrichment]
[Prompt: Did this interaction change, support, or challenge any active hypotheses?]

> [!quote]- Raw Transcript
> This is the raw transcript text.
> It should not be modified.
"""


# ---------------------------------------------------------------------------
# Evidence note parsing
# ---------------------------------------------------------------------------

class TestEvidenceNoteParsing:
    """Parse evidence note structure."""

    def test_parses_all_sections(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        headings = [s.heading for s in doc.all_sections]
        assert "# Market Sizing Analysis" in headings
        assert "## Slide 1" in headings
        assert "## Slide 2" in headings
        assert "## Version History" in headings

    def test_top_level_is_h1(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        # The only truly top-level section is the H1
        assert len(doc.sections) >= 1
        assert doc.sections[0].heading == "# Market Sizing Analysis"

    def test_parses_slide_children(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        slide1 = doc.get_section("## Slide 1")
        assert slide1 is not None
        child_headings = [c.heading for c in slide1.children]
        assert "### Text (Verbatim)" in child_headings
        assert "### Analysis" in child_headings

    def test_get_section_exact_match(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        section = doc.get_section("## Slide 1")
        assert section is not None
        assert section.level == 2

    def test_get_section_not_found(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        assert doc.get_section("## Nonexistent") is None

    def test_get_subtree_includes_children(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        subtree = doc.get_subtree("## Slide 1")
        assert subtree is not None
        assert "### Text (Verbatim)" in subtree
        assert "### Analysis" in subtree
        assert "verbatim text from slide 1" in subtree

    def test_version_history_content(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        subtree = doc.get_subtree("## Version History")
        assert subtree is not None
        assert "Initial conversion" in subtree


# ---------------------------------------------------------------------------
# Interaction note parsing
# ---------------------------------------------------------------------------

class TestInteractionNoteParsing:
    """Parse interaction note structure."""

    def test_parses_all_sections(self):
        doc = MarkdownDocument(INTERACTION_NOTE)
        headings = [s.heading for s in doc.all_sections]
        assert "# CTO Sync Meeting" in headings
        assert "## Summary" in headings
        assert "## Key Findings" in headings
        assert "## Entities Mentioned" in headings
        assert "## Quotes / Evidence" in headings
        assert "## Impact on Hypotheses" in headings

    def test_key_findings_children(self):
        doc = MarkdownDocument(INTERACTION_NOTE)
        kf = doc.get_section("## Key Findings")
        assert kf is not None
        child_headings = [c.heading for c in kf.children]
        assert "### Claims" in child_headings
        assert "### Data Points" in child_headings
        assert "### Decisions" in child_headings
        assert "### Open Questions" in child_headings

    def test_entities_mentioned_subtree(self):
        doc = MarkdownDocument(INTERACTION_NOTE)
        subtree = doc.get_subtree("## Entities Mentioned")
        assert subtree is not None
        assert "### People" in subtree
        assert "[[Jane Smith]]" in subtree
        assert "### Systems" in subtree


# ---------------------------------------------------------------------------
# Fenced code block handling
# ---------------------------------------------------------------------------

class TestFencedCodeBlocks:
    """Headings inside fenced code blocks are ignored."""

    def test_heading_inside_fence_ignored(self):
        content = """\
# Real Title

Some text here.

```markdown
## Fake Heading Inside Fence

This is not a real section.
```

## Real Section

Content of real section.
"""
        doc = MarkdownDocument(content)
        headings = [s.heading for s in doc.all_sections]
        assert "## Fake Heading Inside Fence" not in headings
        assert "# Real Title" in headings
        assert "## Real Section" in headings

    def test_heading_after_fence_recognized(self):
        content = """\
# Title

```python
## not a heading
def foo():
    pass
```

## After Fence

Real content.
"""
        doc = MarkdownDocument(content)
        after = doc.get_section("## After Fence")
        assert after is not None
        assert "Real content." in doc._content[after.body_start:after.end]

    def test_multiple_fences(self):
        content = """\
# Title

```
## Fake 1
```

## Real 1

```
## Fake 2
```

## Real 2

Content.
"""
        doc = MarkdownDocument(content)
        headings = [s.heading for s in doc.all_sections]
        assert "## Fake 1" not in headings
        assert "## Fake 2" not in headings
        assert "## Real 1" in headings
        assert "## Real 2" in headings


# ---------------------------------------------------------------------------
# Managed sections
# ---------------------------------------------------------------------------

class TestManagedSections:
    """get_managed_sections returns correct sections."""

    def test_evidence_managed_returns_analysis_subtrees(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        managed = doc.get_managed_sections("evidence")
        assert "## Slide 1 > ### Analysis" in managed
        assert "## Slide 2 > ### Analysis" in managed
        # Text (Verbatim) is NOT managed
        for key in managed:
            assert "Text (Verbatim)" not in key

    def test_evidence_managed_includes_related_if_present(self):
        content = EVIDENCE_NOTE.rstrip() + "\n\n## Related\n\n### Supersedes\n- [[other_note|Other]]\n"
        doc = MarkdownDocument(content)
        managed = doc.get_managed_sections("evidence")
        assert "## Related" in managed

    def test_evidence_managed_no_related_when_absent(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        managed = doc.get_managed_sections("evidence")
        assert "## Related" not in managed

    def test_interaction_managed_returns_entities_and_impact(self):
        doc = MarkdownDocument(INTERACTION_NOTE)
        managed = doc.get_managed_sections("interaction")
        assert "## Entities Mentioned" in managed
        assert "## Impact on Hypotheses" in managed

    def test_interaction_managed_does_not_include_summary(self):
        doc = MarkdownDocument(INTERACTION_NOTE)
        managed = doc.get_managed_sections("interaction")
        assert "## Summary" not in managed
        assert "## Key Findings" not in managed
        assert "## Quotes / Evidence" not in managed

    def test_malformed_headings_return_empty_managed(self):
        content = "# Title\n\nJust some text without proper sections.\n"
        doc = MarkdownDocument(content)
        managed = doc.get_managed_sections("evidence")
        assert managed == {}

    def test_unknown_doc_type_returns_empty(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        managed = doc.get_managed_sections("diagram")
        assert managed == {}


# ---------------------------------------------------------------------------
# Section body replacement
# ---------------------------------------------------------------------------

class TestReplaceSectionBody:
    """replace_section_body does not bleed into neighboring sections."""

    def test_replace_analysis_body(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        analysis = None
        for s in doc.all_sections:
            if s.heading == "### Analysis" and s.start < doc.get_section("## Slide 2").start:
                analysis = s
                break
        assert analysis is not None

        new_body = "\nNew analysis content here.\n\n"
        new_content = doc.replace_section_body(analysis, new_body)

        # New content should contain the replacement
        assert "New analysis content here." in new_content
        # Original analysis content should be gone
        assert "Revenue grew 15% YoY" not in new_content
        # Neighboring sections should be untouched
        assert "verbatim text from slide 1" in new_content
        assert "## Slide 2" in new_content
        assert "Second slide verbatim text" in new_content

    def test_replace_does_not_bleed_forward(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        slide2_analysis = None
        slide2 = doc.get_section("## Slide 2")
        for s in slide2.children:
            if s.heading == "### Analysis":
                slide2_analysis = s
                break
        assert slide2_analysis is not None

        new_body = "\nReplacement.\n\n"
        new_content = doc.replace_section_body(slide2_analysis, new_body)

        # Version History should still be present
        assert "## Version History" in new_content
        assert "Initial conversion" in new_content
        # Slide 1 analysis should be untouched
        assert "Revenue grew 15% YoY" in new_content

    def test_replace_interaction_entities_section(self):
        doc = MarkdownDocument(INTERACTION_NOTE)
        entities = doc.get_section("## Entities Mentioned")
        assert entities is not None

        new_body = "\n### People\n- [[Alice]]\n\n### Departments\n- [[HR]]\n\n### Systems\n- None\n\n### Processes\n- None\n\n"
        new_content = doc.replace_section_body(entities, new_body)

        assert "[[Alice]]" in new_content
        assert "[[HR]]" in new_content
        # Summary should be untouched
        assert "Q2 roadmap priorities" in new_content
        # Quotes should be untouched
        assert "We need to stabilize before we grow" in new_content


# ---------------------------------------------------------------------------
# Insert and remove
# ---------------------------------------------------------------------------

class TestInsertBeforeSection:
    """insert_before_section works correctly."""

    def test_insert_before_version_history(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        related_section = "## Related\n\n### Supersedes\n- [[other|Other Note]]\n\n"
        new_content = doc.insert_before_section("## Version History", related_section)

        # Related should appear before Version History
        related_pos = new_content.index("## Related")
        version_pos = new_content.index("## Version History")
        assert related_pos < version_pos

    def test_insert_before_nonexistent_returns_unchanged(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        result = doc.insert_before_section("## Nonexistent", "extra content")
        assert result == EVIDENCE_NOTE


class TestRemoveSection:
    """remove_section works correctly."""

    def test_remove_related_section(self):
        content_with_related = EVIDENCE_NOTE.rstrip() + "\n\n## Related\n\n### Supersedes\n- [[other|Other]]\n\n## Version History\n\nNew history.\n"
        doc = MarkdownDocument(content_with_related)
        assert doc.get_section("## Related") is not None

        new_content = doc.remove_section("## Related")
        doc2 = MarkdownDocument(new_content)
        assert doc2.get_section("## Related") is None
        # Version History should still be there
        assert doc2.get_section("## Version History") is not None

    def test_remove_nonexistent_returns_unchanged(self):
        doc = MarkdownDocument(EVIDENCE_NOTE)
        result = doc.remove_section("## Nonexistent")
        assert result == EVIDENCE_NOTE

    def test_remove_section_at_end(self):
        content = "# Title\n\n## Section A\n\nContent A.\n\n## Section B\n\nContent B.\n"
        doc = MarkdownDocument(content)
        new_content = doc.remove_section("## Section B")
        assert "Content B" not in new_content
        assert "Content A" in new_content


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases for section parser."""

    def test_empty_content(self):
        doc = MarkdownDocument("")
        assert doc.sections == []
        assert doc.all_sections == []
        assert doc.get_section("## Anything") is None

    def test_no_headings(self):
        content = "Just plain text\nwith no headings.\n"
        doc = MarkdownDocument(content)
        assert doc.sections == []

    def test_single_heading(self):
        content = "# Only Title\n\nSome content.\n"
        doc = MarkdownDocument(content)
        assert len(doc.sections) == 1
        assert doc.sections[0].heading == "# Only Title"

    def test_level_hierarchy(self):
        content = """\
# H1

## H2a

### H3

## H2b

Content.
"""
        doc = MarkdownDocument(content)
        h1 = doc.get_section("# H1")
        assert h1 is not None
        h2a = doc.get_section("## H2a")
        assert h2a is not None
        assert len(h2a.children) == 1
        assert h2a.children[0].heading == "### H3"

    def test_heading_at_end_of_file(self):
        content = "# Title\n\n## Last Section\n"
        doc = MarkdownDocument(content)
        last = doc.get_section("## Last Section")
        assert last is not None
        assert last.end == len(content)

    def test_frontmatter_not_parsed_as_heading(self):
        content = "---\nid: test\n---\n\n# Title\n\nContent.\n"
        doc = MarkdownDocument(content)
        # Frontmatter delimiters (---) are not headings
        headings = [s.heading for s in doc.all_sections]
        assert "# Title" in headings
        assert len(headings) == 1
