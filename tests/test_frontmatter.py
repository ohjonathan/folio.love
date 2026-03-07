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
