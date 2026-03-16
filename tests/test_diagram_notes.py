"""Tests for standalone diagram note emission, freeze detection, and hydration."""

import yaml
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from folio.output.diagram_notes import (
    DiagramNoteRef,
    FrozenDiagramPayload,
    build_note_basename,
    discover_frozen_notes,
    emit_diagram_notes,
    _build_note_frontmatter,
    _build_note_body,
    _hydrate_graph_from_tables,
    _parse_table_rows,
    _split_table_cells,
    _extract_section,
)
from folio.pipeline.analysis import (
    DiagramAnalysis,
    DiagramEdge,
    DiagramGraph,
    DiagramGroup,
    DiagramNode,
)


def _make_graph():
    """Create a simple test graph."""
    return DiagramGraph(
        nodes=[
            DiagramNode(id="n1", label="API Gateway", kind="service", technology="Kong", group_id="g1"),
            DiagramNode(id="n2", label="Order DB", kind="database", technology="PostgreSQL", group_id="g1"),
            DiagramNode(id="n3", label="Auth Service", kind="service", technology="Keycloak"),
        ],
        edges=[
            DiagramEdge(id="e1", source_id="n1", target_id="n2", label="queries", direction="forward"),
            DiagramEdge(id="e2", source_id="n1", target_id="n3", label="validates", direction="forward"),
        ],
        groups=[
            DiagramGroup(id="g1", name="Backend", contains=["n1", "n2"]),
        ],
    )


def _make_analysis(**overrides):
    """Create a test DiagramAnalysis with rendered fields."""
    defaults = dict(
        diagram_type="architecture",
        graph=_make_graph(),
        mermaid="graph TD\n  A-->B",
        description="System architecture overview.",
        component_table="| Component | Type | Technology | Group | Source | Confidence |\n|---|---|---|---|---|---|\n| API Gateway | service | Kong | Backend | vision | 0.95 |\n| Order DB | database | PostgreSQL | Backend | vision | 0.90 |\n| Auth Service | service | Keycloak | — | vision | 0.85 |",
        connection_table="| From | To | Label | Direction | Confidence |\n|---|---|---|---|---|\n| API Gateway | Order DB | queries | → | 0.9 |\n| API Gateway | Auth Service | validates | → | 0.85 |",
        diagram_confidence=0.93,
        confidence_reasoning="Clear architecture diagram with standard components.",
        review_required=False,
        review_questions=[],
        abstained=False,
        _extraction_metadata={"extraction_provider": "anthropic", "extraction_model": "claude"},
    )
    defaults.update(overrides)
    return DiagramAnalysis(**defaults)


class TestBuildNoteBasename:
    """Test stable filename generation."""

    def test_standard_basename(self):
        result = build_note_basename("20260314", "system-design-review", 7)
        assert result == "20260314-system-design-review-diagram-p007"

    def test_zero_padded(self):
        result = build_note_basename("20260314", "deck", 1)
        assert result == "20260314-deck-diagram-p001"

    def test_triple_digit(self):
        result = build_note_basename("20260314", "deck", 100)
        assert result == "20260314-deck-diagram-p100"


class TestFullNoteEmission:
    """Test 1: Full standalone note emission for a normal rendered diagram."""

    def test_emits_note_with_all_sections(self, tmp_path):
        analysis = _make_analysis()
        analyses = {7: analysis}
        page_profiles = {7: MagicMock(classification="diagram")}

        refs = emit_diagram_notes(
            deck_dir=tmp_path,
            deck_slug="system_design_review",
            deck_title="System Design Review",
            created_date="20260314",
            analyses=analyses,
            page_profiles=page_profiles,
        )

        assert 7 in refs
        ref = refs[7]
        assert ref.basename == "20260314-system_design_review-diagram-p007"
        assert ref.has_diagram_section is True
        assert ref.has_components_section is True

        # Verify file was written
        note_path = ref.path
        assert note_path.exists()
        content = note_path.read_text()

        # Parse frontmatter
        fm_text = content.split("---", 2)[1]
        fm = yaml.safe_load(fm_text)
        assert fm["type"] == "diagram"
        assert fm["diagram_type"] == "architecture"
        assert fm["source_deck"] == "[[system_design_review]]"
        assert fm["source_page"] == 7
        assert fm["folio_freeze"] is False
        assert "diagram" in fm["tags"]
        assert "architecture" in fm["tags"]
        assert "source" not in fm  # Must NOT have deck fields
        assert "source_hash" not in fm
        assert "source_type" not in fm

        # Verify body sections
        assert "## Diagram" in content
        assert "```mermaid" in content
        assert "## Components" in content
        assert "## Connections" in content
        assert "## Summary" in content
        assert "## Extraction Notes" in content
        assert "![[slides/slide-007.png]]" in content

    def test_title_format(self, tmp_path):
        analysis = _make_analysis(diagram_type="data-flow")
        analyses = {3: analysis}
        page_profiles = {3: MagicMock(classification="diagram")}

        refs = emit_diagram_notes(
            tmp_path, "my_deck", "My Deck", "20260315",
            analyses, page_profiles,
        )
        content = refs[3].path.read_text()
        fm = yaml.safe_load(content.split("---", 2)[1])
        assert fm["title"] == "My Deck — Data Flow (Page 3)"


class TestAbstainedNoteGraphNone:
    """Test 2: Abstained note with graph=None."""

    def test_graphless_abstained_omits_sections(self, tmp_path):
        analysis = _make_analysis(
            abstained=True,
            graph=None,
            mermaid=None,
            description=None,
            component_table=None,
            connection_table=None,
            diagram_confidence=0.2,
            confidence_reasoning="Too complex to extract reliably.",
        )
        analyses = {5: analysis}
        page_profiles = {5: MagicMock(classification="diagram")}

        refs = emit_diagram_notes(
            tmp_path, "deck", "Test Deck", "20260314",
            analyses, page_profiles,
        )
        content = refs[5].path.read_text()

        # Should NOT have diagram sections
        assert "## Diagram" not in content
        assert "## Components" not in content
        assert "## Connections" not in content
        assert "## Summary" not in content

        # Should have abstention explanation
        assert "Too complex to extract reliably." in content
        assert "![[slides/slide-005.png]]" in content

        assert refs[5].has_diagram_section is False
        assert refs[5].has_components_section is False


class TestAbstainedNoteWithGraph:
    """Test 3: Abstained note with graph present (candidate extraction)."""

    def test_abstained_with_graph_has_caveat(self, tmp_path):
        analysis = _make_analysis(abstained=True)
        analyses = {4: analysis}
        page_profiles = {4: MagicMock(classification="diagram")}

        refs = emit_diagram_notes(
            tmp_path, "deck", "Test Deck", "20260314",
            analyses, page_profiles,
        )
        content = refs[4].path.read_text()

        assert "Candidate extraction rendered for reviewer context" in content
        assert "## Diagram" in content
        assert "## Components" in content

        fm = yaml.safe_load(content.split("---", 2)[1])
        assert fm["abstained"] is True


class TestReviewHeavyNote:
    """Test 4: Review-heavy note with uncertainties and review questions."""

    def test_uncertainties_and_questions_rendered(self, tmp_path):
        analysis = _make_analysis(
            review_required=True,
            uncertainties=["Node 'Cache' may be Redis or Memcached"],
            review_questions=["Is the message queue Kafka or RabbitMQ?"],
        )
        analyses = {2: analysis}
        page_profiles = {2: MagicMock(classification="diagram")}

        refs = emit_diagram_notes(
            tmp_path, "deck", "Test Deck", "20260314",
            analyses, page_profiles,
        )
        content = refs[2].path.read_text()

        assert "> Node 'Cache' may be Redis or Memcached" in content
        assert "> Is the message queue Kafka or RabbitMQ?" in content

        fm = yaml.safe_load(content.split("---", 2)[1])
        assert fm["review_required"] is True
        assert "Is the message queue Kafka or RabbitMQ?" in fm["review_questions"]


class TestStableFilename:
    """Test 5: Stable filename from preserved created date."""

    def test_same_created_date_same_basename(self):
        b1 = build_note_basename("20260314", "my-deck", 7)
        b2 = build_note_basename("20260314", "my-deck", 7)
        assert b1 == b2

    def test_different_dates_different_basenames(self):
        b1 = build_note_basename("20260314", "deck", 7)
        b2 = build_note_basename("20260315", "deck", 7)
        assert b1 != b2


class TestFrontmatterPreservation:
    """Test 6: Preservation of human_overrides, _review_history, folio_freeze on reprocessing."""

    def test_preserves_user_fields_on_reconversion(self, tmp_path):
        # First emission
        analysis = _make_analysis()
        analyses = {7: analysis}
        page_profiles = {7: MagicMock(classification="diagram")}

        refs = emit_diagram_notes(
            tmp_path, "deck", "Test Deck", "20260314",
            analyses, page_profiles,
        )

        # Simulate user editing the note
        note_path = refs[7].path
        content = note_path.read_text()
        fm_text = content.split("---", 2)[1]
        fm = yaml.safe_load(fm_text)
        fm["human_overrides"] = {"n1_label": "Load Balancer"}
        fm["_review_history"] = [{"date": "2026-03-14", "action": "reviewed"}]
        fm["custom_user_field"] = "my notes"
        # NOT setting folio_freeze to true, just modifying fields

        new_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
        body = content.split("---", 2)[2]
        note_path.write_text(f"---\n{new_yaml}---{body}")

        # Re-emit (reconversion)
        refs2 = emit_diagram_notes(
            tmp_path, "deck", "Test Deck", "20260314",
            analyses, page_profiles,
        )
        content2 = refs2[7].path.read_text()
        fm2 = yaml.safe_load(content2.split("---", 2)[1])

        assert fm2["human_overrides"] == {"n1_label": "Load Balancer"}
        assert fm2["_review_history"] == [{"date": "2026-03-14", "action": "reviewed"}]
        assert fm2["custom_user_field"] == "my notes"


class TestFrozenNoteHydration:
    """Test 7: Frozen-note hydration from Components and Connections tables."""

    def _write_frozen_note(self, tmp_path, basename):
        fm = {
            "type": "diagram",
            "diagram_type": "architecture",
            "title": "Test — Architecture (Page 7)",
            "source_deck": "[[deck]]",
            "source_page": 7,
            "extraction_confidence": 0.93,
            "confidence_reasoning": "Clear diagram.",
            "review_required": False,
            "review_questions": [],
            "abstained": False,
            "folio_freeze": True,
            "components": ["API Gateway", "Order DB"],
            "technologies": ["Kong", "PostgreSQL"],
            "tags": ["diagram", "architecture"],
            "human_overrides": {},
            "_review_history": [{"date": "2026-03-14", "action": "Verified"}],
        }
        body = """# Test — Architecture (Page 7)

Extracted from [[deck]], page 7.

## Diagram

```mermaid
graph TD
  A-->B
```

## Components

| Component | Type | Technology | Group | Source | Confidence |
|---|---|---|---|---|---|
| API Gateway | service | Kong | Backend | vision | 0.95 |
| Order DB | database | PostgreSQL | Backend | vision | 0.90 |

## Connections

| From | To | Label | Direction | Confidence |
|---|---|---|---|---|
| API Gateway | Order DB | queries | → | 0.9 |

## Summary

System architecture overview.

## Extraction Notes

> No uncertainties flagged.

---

![[slides/slide-007.png]]"""

        yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
        note_path = tmp_path / f"{basename}.md"
        note_path.write_text(f"---\n{yaml_str}---\n\n{body}\n")
        return note_path

    def test_discovers_frozen_note(self, tmp_path):
        basename = build_note_basename("20260314", "deck", 7)
        self._write_frozen_note(tmp_path, basename)

        page_profiles = {7: MagicMock(classification="diagram")}
        frozen = discover_frozen_notes(tmp_path, "deck", "20260314", page_profiles)

        assert 7 in frozen
        payload = frozen[7]
        assert isinstance(payload.analysis, DiagramAnalysis)
        assert payload.analysis.diagram_type == "architecture"
        assert payload.analysis.diagram_confidence == 0.93
        assert payload.note_ref.has_diagram_section is True

    def test_hydrates_graph_from_tables(self, tmp_path):
        basename = build_note_basename("20260314", "deck", 7)
        self._write_frozen_note(tmp_path, basename)

        page_profiles = {7: MagicMock(classification="diagram")}
        frozen = discover_frozen_notes(tmp_path, "deck", "20260314", page_profiles)

        graph = frozen[7].analysis.graph
        assert graph is not None
        assert len(graph.nodes) == 2
        assert graph.nodes[0].label == "API Gateway"
        assert graph.nodes[0].technology == "Kong"
        assert len(graph.edges) == 1
        assert graph.edges[0].direction == "forward"
        assert len(graph.groups) == 1
        assert graph.groups[0].name == "Backend"

        # S-NEW-1 regression: frozen mermaid code must NOT be silently discarded
        assert frozen[7].analysis.mermaid is not None
        assert "A-->B" in frozen[7].analysis.mermaid

    def test_frozen_note_not_rewritten(self, tmp_path):
        """Frozen notes should not be rewritten by emit_diagram_notes."""
        basename = build_note_basename("20260314", "deck", 7)
        note_path = self._write_frozen_note(tmp_path, basename)
        original_content = note_path.read_text()

        analysis = _make_analysis()
        analyses = {7: analysis}
        page_profiles = {7: MagicMock(classification="diagram")}

        refs = emit_diagram_notes(
            tmp_path, "deck", "Test Deck", "20260314",
            analyses, page_profiles,
        )

        assert 7 in refs
        # File should NOT have been rewritten
        assert note_path.read_text() == original_content


class TestMalformedFrozenNote:
    """Test 8: Malformed frozen-note degradation with warning and partial graph."""

    def test_malformed_tables_partial_recovery(self, tmp_path, caplog):
        """Malformed tables should produce partial graph with warning."""
        import logging

        basename = build_note_basename("20260314", "deck", 3)
        fm = {
            "type": "diagram",
            "diagram_type": "data-flow",
            "title": "Test — Data Flow (Page 3)",
            "source_deck": "[[deck]]",
            "source_page": 3,
            "extraction_confidence": 0.7,
            "confidence_reasoning": "Partial extraction.",
            "review_required": True,
            "review_questions": [],
            "abstained": False,
            "folio_freeze": True,
            "tags": ["diagram"],
            "human_overrides": {},
            "_review_history": [],
        }
        # Malformed component table (missing columns)
        body = """# Test

Extracted from [[deck]], page 3.

## Diagram

```mermaid
graph LR
  X-->Y
```

## Components

| Component | Type |
|---|---|
| Service A | service |

## Connections

## Summary

Partial.

## Extraction Notes

> Partial extraction.

---

![[slides/slide-003.png]]"""

        yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
        note_path = tmp_path / f"{basename}.md"
        note_path.write_text(f"---\n{yaml_str}---\n\n{body}\n")

        page_profiles = {3: MagicMock(classification="diagram")}
        with caplog.at_level(logging.WARNING):
            frozen = discover_frozen_notes(tmp_path, "deck", "20260314", page_profiles)

        assert 3 in frozen
        graph = frozen[3].analysis.graph
        # Should have partially recovered the graph
        assert graph is not None
        assert len(graph.nodes) == 1
        assert graph.nodes[0].label == "Service A"


class TestTableParsing:
    """Unit tests for _parse_table_rows and _hydrate_graph_from_tables."""

    def test_standard_table(self):
        table = (
            "| Component | Type | Technology | Group | Source | Confidence |\n"
            "|---|---|---|---|---|---|\n"
            "| API | service | Kong | Backend | vision | 0.95 |"
        )
        rows = _parse_table_rows(table)
        assert len(rows) == 1
        assert rows[0]["Component"] == "API"
        assert rows[0]["Technology"] == "Kong"

    def test_hydrate_with_direction_symbols(self):
        comp = (
            "| Component | Type | Technology | Group | Source | Confidence |\n"
            "|---|---|---|---|---|---|\n"
            "| A | service | | | vision | 1.0 |\n"
            "| B | database | | | vision | 1.0 |"
        )
        conn = (
            "| From | To | Label | Direction | Confidence |\n"
            "|---|---|---|---|---|\n"
            "| A | B | reads | → | 0.9 |\n"
            "| B | A | notifies | ← | 0.8 |"
        )
        graph = _hydrate_graph_from_tables(comp, conn)
        assert graph is not None
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 2
        assert graph.edges[0].direction == "forward"
        assert graph.edges[1].direction == "reverse"


# --- Round 1 Review Regression Tests ---


class TestC1PipeEscapeRoundTrip:
    """C1 regression: _parse_table_rows must handle escaped pipes."""

    def test_escaped_pipe_in_label(self):
        """A label with escaped pipe must not split into phantom columns."""
        table = (
            "| Component | Type | Technology | Group | Source | Confidence |\n"
            "|---|---|---|---|---|---|\n"
            "| Config \\| Settings | service | Redis | Infra | vision | 0.9 |"
        )
        rows = _parse_table_rows(table)
        assert len(rows) == 1
        assert rows[0]["Component"] == "Config | Settings"
        assert rows[0]["Type"] == "service"
        assert rows[0]["Technology"] == "Redis"

    def test_split_table_cells_unescape(self):
        """_split_table_cells must unescape \\| -> |."""
        cells = _split_table_cells("| foo \\| bar | baz |")
        assert cells == ["foo | bar", "baz"]

    def test_round_trip_escape_parse(self):
        """Value with pipe: escape -> render -> parse must preserve."""
        from folio.output.diagram_rendering import _escape_table_cell
        original = "Config | Settings"
        escaped = _escape_table_cell(original)
        table = f"| Component |\n|---|\n| {escaped} |"
        rows = _parse_table_rows(table)
        assert rows[0]["Component"] == original


class TestC2S1DiagramTypeScopeing:
    """C2+S1: diagram_types scope — graphless abstentions excluded, extracted types included."""

    def test_graphless_abstained_excluded(self):
        """S1 fix: graphless abstained should NOT appear in deck diagram_types."""
        from folio.output.frontmatter import _collect_unique
        analyses = {
            1: DiagramAnalysis(
                diagram_type="unsupported",
                graph=None,
                abstained=True,
                diagram_confidence=0.1,
            ),
        }
        types = _collect_unique(analyses, "diagram_type", exclude={"unknown"})
        assert "unsupported" not in types

    def test_abstained_with_graph_included(self):
        """Abstained-with-graph (candidate) still appears in diagram_types."""
        from folio.output.frontmatter import _collect_unique
        analyses = {
            1: DiagramAnalysis(
                diagram_type="architecture",
                graph=_make_graph(),
                abstained=True,
                diagram_confidence=0.4,
            ),
        }
        types = _collect_unique(analyses, "diagram_type", exclude={"unknown"})
        assert "architecture" in types

    def test_normal_diagram_included(self):
        """Non-abstained diagram should appear in diagram_types."""
        from folio.output.frontmatter import _collect_unique
        analyses = {1: _make_analysis()}
        types = _collect_unique(analyses, "diagram_type", exclude={"unknown"})
        assert "architecture" in types


class TestB1UnsupportedDiagramEmission:
    """B1: unsupported_diagram pages get standalone abstention notes."""

    def test_unsupported_diagram_emits_note(self, tmp_path):
        analysis = DiagramAnalysis(
            diagram_type="unsupported",
            graph=None,
            abstained=True,
            diagram_confidence=0.1,
            confidence_reasoning="Diagram type not supported.",
            review_required=True,
        )
        analyses = {5: analysis}
        page_profiles = {5: MagicMock(classification="unsupported_diagram")}

        refs = emit_diagram_notes(
            tmp_path, "deck", "Test Deck", "20260314", analyses, page_profiles,
        )
        assert 5 in refs
        content = refs[5].path.read_text()
        assert "unsupported" in content
        assert refs[5].has_diagram_section is False

    def test_unsupported_diagram_frozen_discovery(self, tmp_path):
        """Frozen notes for unsupported_diagram pages should be discovered."""
        import yaml
        basename = build_note_basename("20260314", "deck", 5)
        fm = {
            "type": "diagram",
            "diagram_type": "unsupported",
            "title": "Test — Unsupported (Page 5)",
            "source_deck": "[[deck]]",
            "source_page": 5,
            "extraction_confidence": 0.1,
            "confidence_reasoning": "Unsupported.",
            "review_required": True,
            "review_questions": [],
            "abstained": True,
            "folio_freeze": True,
            "tags": ["diagram"],
            "human_overrides": {},
            "_review_history": [],
            "_extraction_metadata": {},
        }
        yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)
        body = "# Test\n\nAbstained — unsupported diagram type.\n\n---\n\n![[slides/slide-005.png]]"
        note_path = tmp_path / f"{basename}.md"
        note_path.write_text(f"---\n{yaml_str}---\n\n{body}\n")

        page_profiles = {5: MagicMock(classification="unsupported_diagram")}
        frozen = discover_frozen_notes(tmp_path, "deck", "20260314", page_profiles)
        assert 5 in frozen
        assert frozen[5].analysis.abstained is True


class TestB2FreezeFailClosed:
    """B2: emit_diagram_notes must never overwrite unparseable existing notes."""

    def test_unparseable_note_preserved(self, tmp_path, caplog):
        """Existing note with corrupt frontmatter should be preserved, not overwritten."""
        import logging

        basename = build_note_basename("20260314", "deck", 7)
        note_path = tmp_path / f"{basename}.md"
        # Write a file with corrupt YAML frontmatter
        corrupt_content = "---\nfolio_freeze: true\ninvalid_yaml: [\n---\n\n# Human notes\n"
        note_path.write_text(corrupt_content)

        analysis = _make_analysis()
        analyses = {7: analysis}
        page_profiles = {7: MagicMock(classification="diagram")}

        with caplog.at_level(logging.WARNING):
            refs = emit_diagram_notes(
                tmp_path, "deck", "Test Deck", "20260314", analyses, page_profiles,
            )

        # Page 7 should NOT have a ref (skipped, not overwritten)
        assert 7 not in refs
        # Original file must be preserved
        assert note_path.read_text() == corrupt_content
        assert "preserving file" in caplog.text


class TestB3MalformedFrozenMetadata:
    """B3: malformed frozen-note metadata must degrade, not crash."""

    def test_non_dict_extraction_metadata(self, tmp_path):
        """_extraction_metadata as a string should degrade to empty dict."""
        import yaml
        basename = build_note_basename("20260314", "deck", 7)
        fm = {
            "type": "diagram",
            "diagram_type": "architecture",
            "title": "Test — Architecture (Page 7)",
            "source_deck": "[[deck]]",
            "source_page": 7,
            "extraction_confidence": 0.9,
            "confidence_reasoning": "Clear.",
            "review_required": False,
            "review_questions": [],
            "abstained": False,
            "folio_freeze": True,
            "tags": ["diagram"],
            "human_overrides": {},
            "_review_history": [],
            "_extraction_metadata": "not_a_dict",  # malformed
        }
        body = "# Test\n\n## Diagram\n\n```mermaid\ngraph TD\n  A-->B\n```\n\n---\n\n![[slides/slide-007.png]]"
        yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)
        note_path = tmp_path / f"{basename}.md"
        note_path.write_text(f"---\n{yaml_str}---\n\n{body}\n")

        page_profiles = {7: MagicMock(classification="diagram")}
        frozen = discover_frozen_notes(tmp_path, "deck", "20260314", page_profiles)

        # Should not crash, and _extraction_metadata should be empty dict
        assert 7 in frozen
        assert frozen[7].analysis._extraction_metadata == {}

    def test_non_list_review_questions(self, tmp_path):
        """review_questions as a string should degrade to empty list."""
        import yaml
        basename = build_note_basename("20260314", "deck", 8)
        fm = {
            "type": "diagram",
            "diagram_type": "sequence",
            "title": "Test — Sequence (Page 8)",
            "source_deck": "[[deck]]",
            "source_page": 8,
            "extraction_confidence": 0.8,
            "confidence_reasoning": "OK.",
            "review_required": False,
            "review_questions": "not a list",  # malformed
            "abstained": False,
            "folio_freeze": True,
            "tags": ["diagram"],
            "human_overrides": {},
            "_review_history": [],
            "_extraction_metadata": {},
        }
        body = "# Test\n\n---\n\n![[slides/slide-008.png]]"
        yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)
        note_path = tmp_path / f"{basename}.md"
        note_path.write_text(f"---\n{yaml_str}---\n\n{body}\n")

        page_profiles = {8: MagicMock(classification="diagram")}
        frozen = discover_frozen_notes(tmp_path, "deck", "20260314", page_profiles)

        assert 8 in frozen
        assert frozen[8].analysis.review_questions == []



class TestM5CodeBlockHeadingImmunity:
    """M5 regression: headings inside code blocks ignored by _extract_section."""

    def test_heading_inside_mermaid_ignored(self):
        content = (
            "## Diagram\n\n"
            "```mermaid\n"
            "graph TD\n"
            "  subgraph \"## Components\"\n"
            "    A-->B\n"
            "  end\n"
            "```\n\n"
            "## Components\n\n"
            "| Component | Type |\n"
            "|---|---|\n"
            "| API | service |\n\n"
            "---\n"
        )
        section = _extract_section(content, "Components")
        assert section is not None
        assert "| API | service |" in section
        assert "subgraph" not in section


class TestSNEW1SectionWithCodeBlock:
    """S-NEW-1 regression: _extract_section on section containing a code block."""

    def test_diagram_section_preserves_mermaid(self):
        """The ## Diagram section contains mermaid; extraction must include it."""
        content = (
            "## Diagram\n\n"
            "```mermaid\n"
            "graph TD\n"
            "  A-->B\n"
            "```\n\n"
            "## Components\n\n"
            "| Component | Type |\n"
            "|---|---|\n"
            "| API | service |\n\n"
            "---\n"
        )
        section = _extract_section(content, "Diagram")
        assert section is not None
        assert "```mermaid" in section
        assert "A-->B" in section
        # Must NOT include content from the Components section
        assert "| API |" not in section

    def test_components_section_after_mermaid(self):
        """Components section extracted correctly when preceded by mermaid."""
        content = (
            "## Diagram\n\n"
            "```mermaid\n"
            "graph TD\n"
            "  A-->B\n"
            "```\n\n"
            "## Components\n\n"
            "| Component | Type |\n"
            "|---|---|\n"
            "| Gateway | service |\n\n"
            "## Summary\n\n"
            "A summary.\n"
        )
        section = _extract_section(content, "Components")
        assert section is not None
        assert "| Gateway | service |" in section
        assert "A summary" not in section


class TestM4NonDiagramAnalysisSkip:
    """m4: non-DiagramAnalysis instances in analyses are silently skipped."""

    def test_regular_slide_analysis_skipped(self, tmp_path):
        from folio.pipeline.analysis import SlideAnalysis
        # A regular SlideAnalysis should be ignored by emit_diagram_notes
        regular = SlideAnalysis()
        analyses = {1: regular, 2: _make_analysis()}
        page_profiles = {
            1: MagicMock(classification="diagram"),
            2: MagicMock(classification="diagram"),
        }
        refs = emit_diagram_notes(
            tmp_path, "deck", "Test", "20260314", analyses, page_profiles,
        )
        # Page 1 (regular SlideAnalysis) should be skipped
        assert 1 not in refs
        # Page 2 (DiagramAnalysis) should be emitted
        assert 2 in refs


class TestM7GenericTechFiltering:
    """m7: generic technology terms filtered from tags."""

    def test_generic_terms_excluded(self):
        analysis = _make_analysis(
            graph=DiagramGraph(
                nodes=[
                    DiagramNode(id="n1", label="App", kind="service", technology="Service"),
                    DiagramNode(id="n2", label="DB", kind="database", technology="PostgreSQL"),
                ],
                edges=[], groups=[],
            ),
        )
        fm = _build_note_frontmatter(analysis, "deck", "Test", 1)
        # "service" is generic and should be filtered; "postgresql" should remain
        assert "postgresql" in fm["tags"]
        assert "service" not in fm["tags"]

    def test_m2_tags_from_title_documented(self):
        """m2: tags from deck_title is intentional (not diagram content)."""
        analysis = _make_analysis()
        fm = _build_note_frontmatter(analysis, "deck", "System Design Review", 1)
        # Title words should appear in tags (by design)
        assert "system" in fm["tags"]
        assert "design" in fm["tags"]
        assert "review" in fm["tags"]
        # Noise words should NOT
        assert "the" not in fm["tags"]
