"""Tests for frontmatter generation: v2 schema completeness."""

from pathlib import Path

import pytest
import yaml
from unittest.mock import patch, MagicMock

from folio.converter import _detect_source_type
from folio.output.frontmatter import (
    _collect_unique,
    _generate_tags,
    generate,
)
from folio.pipeline.analysis import SlideAnalysis
from folio.tracking.versions import ChangeSet, VersionInfo


def _make_version_info(**overrides):
    defaults = dict(
        version=1,
        timestamp="2026-01-01T00:00:00Z",
        source_hash="abc123def456",
        source_path="deck.pptx",
        note=None,
        slide_count=1,
        changes=ChangeSet(added=[1]),
    )
    defaults.update(overrides)
    return VersionInfo(**defaults)


def _parse_frontmatter(fm_str: str) -> dict:
    content = fm_str.split("---", 2)[1].strip()
    return yaml.safe_load(content)


def _generate_simple(**overrides):
    defaults = dict(
        title="Test Deck",
        deck_id="test_id",
        source_relative_path="deck.pptx",
        source_hash="abc123def456",
        source_type="deck",
        version_info=_make_version_info(),
        analyses={1: SlideAnalysis(slide_type="title")},
    )
    defaults.update(overrides)
    return generate(**defaults)


# --- G1: Source type detection ---


class TestSourceTypeDetection:
    def test_pptx_returns_deck(self):
        assert _detect_source_type(Path("slides.pptx")) == "deck"

    def test_pdf_returns_pdf(self):
        assert _detect_source_type(Path("report.pdf")) == "pdf"

    def test_ppt_returns_deck(self):
        assert _detect_source_type(Path("old_slides.ppt")) == "deck"

    def test_unknown_extension_returns_pdf(self):
        assert _detect_source_type(Path("document.docx")) == "pdf"

    def test_source_type_in_frontmatter_deck(self):
        fm = _parse_frontmatter(_generate_simple(source_type="deck"))
        assert fm["source_type"] == "deck"

    def test_source_type_in_frontmatter_pdf(self):
        fm = _parse_frontmatter(_generate_simple(source_type="pdf"))
        assert fm["source_type"] == "pdf"


# --- G2: Subtype configurability ---


class TestSubtypeConfigurability:
    def test_default_subtype_is_research(self):
        fm = _parse_frontmatter(_generate_simple())
        assert fm["subtype"] == "research"

    def test_explicit_subtype_data_extract(self):
        fm = _parse_frontmatter(_generate_simple(subtype="data_extract"))
        assert fm["subtype"] == "data_extract"

    def test_explicit_subtype_benchmark(self):
        fm = _parse_frontmatter(_generate_simple(subtype="benchmark"))
        assert fm["subtype"] == "benchmark"


# --- G3: Industry field ---


class TestIndustryField:
    def test_absent_when_not_provided(self):
        fm = _parse_frontmatter(_generate_simple())
        assert "industry" not in fm

    def test_single_industry(self):
        fm = _parse_frontmatter(_generate_simple(industry=["retail"]))
        assert fm["industry"] == ["retail"]

    def test_multiple_industries_sorted(self):
        fm = _parse_frontmatter(_generate_simple(industry=["ecommerce", "retail"]))
        assert fm["industry"] == ["ecommerce", "retail"]


# --- G4: Tag override ---


class TestTagOverride:
    def test_auto_tags_preserved_without_extra(self):
        analyses = {
            1: SlideAnalysis(slide_type="data", framework="tam-sam-som"),
        }
        fm = _parse_frontmatter(_generate_simple(analyses=analyses))
        assert "tam-sam-som" in fm["tags"]

    def test_manual_tags_merged(self):
        fm = _parse_frontmatter(_generate_simple(extra_tags=["market-sizing"]))
        assert "market-sizing" in fm["tags"]

    def test_duplicate_tags_deduplicated(self):
        analyses = {
            1: SlideAnalysis(slide_type="data", framework="tam-sam-som"),
        }
        fm = _parse_frontmatter(_generate_simple(
            analyses=analyses,
            extra_tags=["tam-sam-som", "custom"],
        ))
        assert fm["tags"].count("tam-sam-som") == 1
        assert "custom" in fm["tags"]


# --- G5: Field ordering ---


class TestFieldOrdering:
    def test_semantic_group_order(self):
        fm = _parse_frontmatter(_generate_simple(client="acme", engagement="dd_q1"))
        keys = list(fm.keys())
        # Identity block comes first
        assert keys.index("id") < keys.index("type")
        assert keys.index("type") < keys.index("subtype")
        # Lifecycle before source
        assert keys.index("status") < keys.index("source")
        # Source before temporal
        assert keys.index("source_type") < keys.index("created")
        # Temporal before engagement
        assert keys.index("converted") < keys.index("client")


# --- Field completeness ---


class TestFieldCompleteness:
    REQUIRED_FIELDS = [
        "id", "title", "type", "subtype", "status", "authority",
        "curation_level", "source", "source_hash", "source_type",
        "version", "created", "modified", "converted", "slide_count",
    ]

    def test_all_required_fields_present(self):
        fm = _parse_frontmatter(_generate_simple())
        for field in self.REQUIRED_FIELDS:
            assert field in fm, f"Missing required field: {field}"

    def test_correct_types(self):
        fm = _parse_frontmatter(_generate_simple())
        assert isinstance(fm["id"], str)
        assert isinstance(fm["version"], int)
        assert isinstance(fm["slide_count"], int)
        assert isinstance(fm["status"], str)


# --- _collect_unique ---


class TestCollectUnique:
    def test_collects_unique_values(self):
        analyses = {
            1: SlideAnalysis(slide_type="data", framework="tam-sam-som"),
            2: SlideAnalysis(slide_type="data", framework="scr"),
            3: SlideAnalysis(slide_type="title", framework="none"),
        }
        result = _collect_unique(analyses, "framework", exclude={"none"})
        assert result == ["scr", "tam-sam-som"]

    def test_excludes_specified_values(self):
        analyses = {
            1: SlideAnalysis(slide_type="pending"),
            2: SlideAnalysis(slide_type="data"),
        }
        result = _collect_unique(analyses, "slide_type", exclude={"pending"})
        assert result == ["data"]

    def test_empty_analyses(self):
        result = _collect_unique({}, "framework")
        assert result == []


# --- _generate_tags ---


class TestGenerateTags:
    def test_includes_frameworks(self):
        tags = _generate_tags(["tam-sam-som", "scr"], [], "Test Deck")
        assert "tam-sam-som" in tags
        assert "scr" in tags

    def test_extracts_title_words(self):
        tags = _generate_tags([], [], "Market Sizing Analysis")
        assert "market" in tags
        assert "sizing" in tags
        assert "analysis" in tags

    def test_filters_noise_words(self):
        tags = _generate_tags([], [], "The Final Version of the Report")
        assert "the" not in tags
        assert "final" not in tags
        assert "version" not in tags

    def test_filters_short_words(self):
        tags = _generate_tags([], [], "An AI ML Report")
        assert "an" not in tags
        assert "ai" not in tags
        assert "ml" not in tags


# --- S1: Type guards (string → list coercion) ---


class TestTypeGuards:
    def test_industry_string_coerced_to_list(self):
        fm = _parse_frontmatter(_generate_simple(industry="retail"))
        assert fm["industry"] == ["retail"]

    def test_extra_tags_string_coerced_to_list(self):
        fm = _parse_frontmatter(_generate_simple(extra_tags="custom"))
        assert "custom" in fm["tags"]
        # Must not character-explode
        assert "c" not in fm["tags"]


# --- S2: CLI option parsing integration ---


class TestCLIOptionParsing:
    """Test that CLI options are correctly parsed and forwarded to converter."""

    @patch("folio.cli.FolioConverter")
    def test_industry_comma_split(self, MockConverter):
        from click.testing import CliRunner
        from folio.cli import cli

        mock_instance = MagicMock()
        MockConverter.return_value = mock_instance
        mock_instance.convert.return_value = MagicMock(
            slide_count=1, output_path="out.md", version=1,
            deck_id="test", changes=MagicMock(has_changes=False),
            cache_stats=None,
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("deck.pptx").touch()
            result = runner.invoke(cli, ["convert", "deck.pptx", "--industry", "retail,ecommerce"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_instance.convert.call_args[1]
        assert sorted(call_kwargs["industry"]) == ["ecommerce", "retail"]

    @patch("folio.cli.FolioConverter")
    def test_tags_comma_split(self, MockConverter):
        from click.testing import CliRunner
        from folio.cli import cli

        mock_instance = MagicMock()
        MockConverter.return_value = mock_instance
        mock_instance.convert.return_value = MagicMock(
            slide_count=1, output_path="out.md", version=1,
            deck_id="test", changes=MagicMock(has_changes=False),
            cache_stats=None,
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("deck.pptx").touch()
            result = runner.invoke(cli, ["convert", "deck.pptx", "--tags", "market-sizing,custom"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_instance.convert.call_args[1]
        assert sorted(call_kwargs["extra_tags"]) == ["custom", "market-sizing"]

    @patch("folio.cli.FolioConverter")
    def test_subtype_choice(self, MockConverter):
        from click.testing import CliRunner
        from folio.cli import cli

        mock_instance = MagicMock()
        MockConverter.return_value = mock_instance
        mock_instance.convert.return_value = MagicMock(
            slide_count=1, output_path="out.md", version=1,
            deck_id="test", changes=MagicMock(has_changes=False),
            cache_stats=None,
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("deck.pptx").touch()
            result = runner.invoke(cli, ["convert", "deck.pptx", "--subtype", "data_extract"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_instance.convert.call_args[1]
        assert call_kwargs["subtype"] == "data_extract"


# --- M3: YAML special-character round-trip ---


class TestYAMLRoundTrip:
    def test_title_with_special_characters(self):
        fm = _parse_frontmatter(_generate_simple(title="Strategy: Q1 'Report'"))
        assert fm["title"] == "Strategy: Q1 'Report'"


# --- B1: Reconversion preservation safety ---


class TestPreservationSafety:
    """Regression tests for reconversion edge cases (Blocking 1)."""

    def test_null_id_falls_back_to_deck_id(self):
        fm = _parse_frontmatter(_generate_simple(
            existing_frontmatter={"id": None, "created": "2026-01-01T00:00:00Z"},
        ))
        assert fm["id"] == "test_id"  # Falls back to deck_id, not null

    def test_null_created_falls_back_to_now(self):
        fm = _parse_frontmatter(_generate_simple(
            existing_frontmatter={"id": "preserved_id", "created": None},
        ))
        assert fm["created"] is not None
        assert isinstance(fm["created"], str)

    def test_non_dict_existing_frontmatter_ignored(self):
        # Non-dict payload (e.g. a bare string) must not crash
        fm = _parse_frontmatter(_generate_simple(
            existing_frontmatter="not a dict",
        ))
        assert fm["id"] == "test_id"  # Falls back to deck_id

    def test_empty_string_id_falls_back(self):
        fm = _parse_frontmatter(_generate_simple(
            existing_frontmatter={"id": "", "created": "2026-01-01T00:00:00Z"},
        ))
        assert fm["id"] == "test_id"  # Empty string rejected

    def test_valid_preservation(self):
        fm = _parse_frontmatter(_generate_simple(
            existing_frontmatter={"id": "original_id", "created": "2025-06-01T00:00:00Z"},
        ))
        assert fm["id"] == "original_id"
        assert fm["created"] == "2025-06-01T00:00:00Z"


class TestFrontmatterFenceParsing:
    """Regression tests for _read_existing_frontmatter fence detection."""

    def test_triple_dash_in_scalar_does_not_truncate(self, tmp_path):
        from folio.converter import _read_existing_frontmatter

        md = tmp_path / "test.md"
        md.write_text(
            "---\n"
            "id: evidence_board_update\n"
            "source: ../Board --- Update.pptx\n"
            "created: '2026-01-01T00:00:00Z'\n"
            "---\n"
            "# Content\n"
        )
        result = _read_existing_frontmatter(md)
        assert result is not None
        assert result["id"] == "evidence_board_update"
        assert result["source"] == "../Board --- Update.pptx"

    def test_no_frontmatter_returns_none(self, tmp_path):
        from folio.converter import _read_existing_frontmatter

        md = tmp_path / "test.md"
        md.write_text("# Just a heading\nNo frontmatter here.\n")
        assert _read_existing_frontmatter(md) is None

    def test_missing_file_returns_none(self, tmp_path):
        from folio.converter import _read_existing_frontmatter

        assert _read_existing_frontmatter(tmp_path / "nonexistent.md") is None

    def test_non_dict_yaml_returns_none(self, tmp_path):
        from folio.converter import _read_existing_frontmatter

        md = tmp_path / "test.md"
        md.write_text("---\n- just\n- a\n- list\n---\n")
        assert _read_existing_frontmatter(md) is None


# --- SF1: Batch CLI forwarding ---


class TestBatchCLIForwarding:
    """Test that batch command forwards --subtype, --industry, --tags."""

    @patch("folio.cli.FolioConverter")
    def test_batch_forwards_new_options(self, MockConverter):
        from click.testing import CliRunner
        from folio.cli import cli

        mock_instance = MagicMock()
        MockConverter.return_value = mock_instance
        mock_instance.convert.return_value = MagicMock(
            slide_count=1, output_path="out.md", version=1,
            deck_id="test", changes=MagicMock(has_changes=False),
            cache_stats=None,
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("deck.pptx").write_bytes(b"fake")
            result = runner.invoke(cli, [
                "batch", ".",
                "--subtype", "data_extract",
                "--industry", "retail,ecommerce",
                "--tags", "custom-tag",
            ])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_instance.convert.call_args[1]
        assert call_kwargs["subtype"] == "data_extract"
        assert sorted(call_kwargs["industry"]) == ["ecommerce", "retail"]
        assert call_kwargs["extra_tags"] == ["custom-tag"]


# --- B2: source_type: report deferral acceptance ---


class TestSourceTypeReportDeferral:
    """Explicit acceptance test: report is a deferred ontology value.

    Per spec Section 7 and Ontology Section 12.4, ``source_type: report``
    requires semantic classification and cannot be auto-detected from
    file extension. It is deferred to a future ``--source-type`` CLI
    override or subtype-based inference.
    """

    def test_generate_accepts_report_as_passthrough(self):
        """Proves that generate() can emit report if explicitly provided."""
        fm = _parse_frontmatter(_generate_simple(source_type="report"))
        assert fm["source_type"] == "report"

    def test_detect_does_not_emit_report(self):
        """Auto-detection never produces report — by design."""
        assert _detect_source_type(Path("report.pdf")) != "report"
        assert _detect_source_type(Path("report.pptx")) != "report"
        assert _detect_source_type(Path("report.docx")) != "report"


# --- FR-700: Review fields ---


class TestReviewFields:
    """Test review_status, review_flags, extraction_confidence in frontmatter."""

    def test_default_clean_status(self):
        fm = _parse_frontmatter(_generate_simple())
        assert fm["review_status"] == "clean"
        assert fm["review_flags"] == []

    def test_flagged_with_flags(self):
        fm = _parse_frontmatter(_generate_simple(
            review_status="flagged",
            review_flags=["low_confidence_slide_1", "unvalidated_claim_slide_1"],
        ))
        assert fm["review_status"] == "flagged"
        assert "low_confidence_slide_1" in fm["review_flags"]
        assert "unvalidated_claim_slide_1" in fm["review_flags"]

    def test_extraction_confidence_present(self):
        fm = _parse_frontmatter(_generate_simple(extraction_confidence=0.85))
        assert fm["extraction_confidence"] == 0.85

    def test_extraction_confidence_null_when_none(self):
        fm = _parse_frontmatter(_generate_simple())
        assert fm["extraction_confidence"] is None

    def test_review_status_ordering(self):
        """review_status, review_flags, extraction_confidence must appear after curation_level."""
        fm = _parse_frontmatter(_generate_simple(
            review_status="clean",
            review_flags=[],
            extraction_confidence=0.85,
        ))
        keys = list(fm.keys())
        assert keys.index("curation_level") < keys.index("review_status")
        assert keys.index("review_status") < keys.index("review_flags")
        assert keys.index("review_flags") < keys.index("extraction_confidence")
        assert keys.index("extraction_confidence") < keys.index("source")

    def test_required_fields_include_review(self):
        fm = _parse_frontmatter(_generate_simple())
        assert "review_status" in fm
        assert "review_flags" in fm

    def test_zero_claim_grounding_summary_always_emitted(self):
        fm = _parse_frontmatter(_generate_simple(
            analyses={1: SlideAnalysis.pending()},
        ))
        assert "grounding_summary" in fm
        assert fm["grounding_summary"]["total_claims"] == 0
        assert fm["grounding_summary"]["high_confidence"] == 0
        assert fm["grounding_summary"]["medium_confidence"] == 0
        assert fm["grounding_summary"]["low_confidence"] == 0
        assert fm["grounding_summary"]["validated"] == 0
        assert fm["grounding_summary"]["unvalidated"] == 0


# --- PR 6: Diagram-aware frontmatter ---


class TestDiagramFrontmatter:
    """Tests for diagram_types, diagram_components in deck frontmatter."""

    def test_diagram_types_populated(self):
        from folio.pipeline.analysis import DiagramAnalysis, DiagramGraph, DiagramNode
        analyses = {
            1: SlideAnalysis(slide_type="title"),
            2: DiagramAnalysis(
                diagram_type="architecture",
                graph=DiagramGraph(nodes=[DiagramNode(id="n1", label="API")]),
                diagram_confidence=0.9,
            ),
        }
        fm = _parse_frontmatter(_generate_simple(analyses=analyses))
        assert "diagram_types" in fm
        assert "architecture" in fm["diagram_types"]

    def test_diagram_components_populated(self):
        from folio.pipeline.analysis import DiagramAnalysis, DiagramGraph, DiagramNode
        analyses = {
            1: DiagramAnalysis(
                diagram_type="architecture",
                graph=DiagramGraph(nodes=[
                    DiagramNode(id="n1", label="API Gateway"),
                    DiagramNode(id="n2", label="Database"),
                ]),
                diagram_confidence=0.9,
            ),
        }
        fm = _parse_frontmatter(_generate_simple(analyses=analyses))
        assert "diagram_components" in fm
        assert "API Gateway" in fm["diagram_components"]
        assert "Database" in fm["diagram_components"]

    def test_diagram_collect_unique_ignores_non_diagram(self):
        from folio.output.frontmatter import _collect_unique
        from folio.pipeline.analysis import DiagramAnalysis, DiagramGraph, DiagramNode
        analyses = {
            1: SlideAnalysis(slide_type="data"),
            2: DiagramAnalysis(
                diagram_type="data-flow",
                graph=DiagramGraph(nodes=[DiagramNode(id="n1", label="Svc", technology="Go")]),
                diagram_confidence=0.8,
            ),
        }
        types = _collect_unique(analyses, "diagram_type", exclude={"unknown"})
        assert types == ["data-flow"]
        techs = _collect_unique(analyses, "diagram_technology")
        assert techs == ["Go"]
        comps = _collect_unique(analyses, "diagram_component")
        assert comps == ["Svc"]

    def test_diagram_generate_tags(self):
        from folio.output.frontmatter import _generate_tags
        tags = _generate_tags(
            ["tam-sam-som"], [], "Market Report",
            diagram_types=["architecture"],
            diagram_technologies=["PostgreSQL"],
        )
        assert "diagram" in tags
        assert "architecture" in tags
        assert "postgresql" in tags
        assert "tam-sam-som" in tags

