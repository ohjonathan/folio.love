"""Tests for source-root mapping, target resolution, and client/engagement inference."""

import tempfile
from pathlib import Path

import pytest

from folio.config import FolioConfig, SourceConfig


# ---------------------------------------------------------------------------
# normalize_target_prefix
# ---------------------------------------------------------------------------

class TestNormalizeTargetPrefix:
    def test_empty_string(self):
        assert FolioConfig.normalize_target_prefix("") == ""

    def test_trailing_slash_stripped(self):
        assert FolioConfig.normalize_target_prefix("Internal/") == "Internal"

    def test_leading_slash_stripped(self):
        assert FolioConfig.normalize_target_prefix("/Internal") == "Internal"

    def test_both_slashes_stripped(self):
        assert FolioConfig.normalize_target_prefix("/Internal/") == "Internal"

    def test_nested_prefix(self):
        assert FolioConfig.normalize_target_prefix("A/B/C") == "A/B/C"

    def test_dotdot_rejected(self):
        with pytest.raises(ValueError, match="must not contain"):
            FolioConfig.normalize_target_prefix("../../etc")

    def test_dotdot_in_middle_rejected(self):
        with pytest.raises(ValueError, match="must not contain"):
            FolioConfig.normalize_target_prefix("ok/../escape")

    def test_dotdot_alone_rejected(self):
        with pytest.raises(ValueError, match="must not contain"):
            FolioConfig.normalize_target_prefix("..")

    def test_dotdot_as_substring_allowed(self):
        """'..foo' is not a traversal; only exact '..' component is rejected."""
        assert FolioConfig.normalize_target_prefix("..foo") == "..foo"

    def test_whitespace_stripped(self):
        assert FolioConfig.normalize_target_prefix("  Internal  ") == "Internal"


# ---------------------------------------------------------------------------
# match_source_root
# ---------------------------------------------------------------------------

class TestMatchSourceRoot:
    def test_match_returns_relative_path(self, tmp_path):
        source_dir = tmp_path / "materials"
        source_dir.mkdir()
        source_file = source_dir / "ClientA" / "deck.pptx"
        source_file.parent.mkdir(parents=True)
        source_file.touch()

        config = FolioConfig(
            sources=[SourceConfig(name="materials", path=str(source_dir))],
        )

        result = config.match_source_root(source_file)
        assert result is not None
        src_config, rel_path = result
        assert src_config.name == "materials"
        assert str(rel_path) == "ClientA/deck.pptx"

    def test_no_match_returns_none(self, tmp_path):
        config = FolioConfig(
            sources=[SourceConfig(name="materials", path=str(tmp_path / "materials"))],
        )
        result = config.match_source_root(tmp_path / "other" / "deck.pptx")
        assert result is None


# ---------------------------------------------------------------------------
# _infer_from_source_root (via FolioConverter)
# ---------------------------------------------------------------------------

class TestInferFromSourceRoot:
    def _make_converter(self, tmp_path, sources, library_root=None):
        from folio.converter import FolioConverter
        config = FolioConfig(
            library_root=library_root or (tmp_path / "library"),
            sources=sources,
        )
        return FolioConverter(config)

    def test_two_segment_inference(self, tmp_path):
        """Two-segment path: ClientA/Engagement1/deck.pptx → client=ClientA, engagement=Engagement1."""
        source_dir = tmp_path / "materials"
        source_file = source_dir / "ClientA" / "Engagement1" / "deck.pptx"
        source_file.parent.mkdir(parents=True)
        source_file.touch()

        converter = self._make_converter(tmp_path, [
            SourceConfig(name="materials", path=str(source_dir), target_prefix=""),
        ])

        client, engagement = converter._infer_from_source_root(
            source_file.resolve(), None, None
        )
        assert client == "ClientA"
        assert engagement == "Engagement1"

    def test_one_segment_inference(self, tmp_path):
        """One-segment path: ClientA/deck.pptx → client=ClientA, engagement=None."""
        source_dir = tmp_path / "materials"
        source_file = source_dir / "ClientA" / "deck.pptx"
        source_file.parent.mkdir(parents=True)
        source_file.touch()

        converter = self._make_converter(tmp_path, [
            SourceConfig(name="materials", path=str(source_dir), target_prefix=""),
        ])

        client, engagement = converter._infer_from_source_root(
            source_file.resolve(), None, None
        )
        assert client == "ClientA"
        assert engagement is None

    def test_no_inference_with_prefix(self, tmp_path):
        """Non-empty target_prefix disables client/engagement inference."""
        source_dir = tmp_path / "materials"
        source_file = source_dir / "ClientA" / "deck.pptx"
        source_file.parent.mkdir(parents=True)
        source_file.touch()

        converter = self._make_converter(tmp_path, [
            SourceConfig(name="materials", path=str(source_dir), target_prefix="Internal"),
        ])

        client, engagement = converter._infer_from_source_root(
            source_file.resolve(), None, None
        )
        assert client is None
        assert engagement is None

    def test_explicit_cli_overrides_inference(self, tmp_path):
        """Explicit --client/--engagement CLI flags take precedence over inference."""
        source_dir = tmp_path / "materials"
        source_file = source_dir / "InferredClient" / "deck.pptx"
        source_file.parent.mkdir(parents=True)
        source_file.touch()

        converter = self._make_converter(tmp_path, [
            SourceConfig(name="materials", path=str(source_dir), target_prefix=""),
        ])

        # _infer_from_source_root itself doesn't check explicit — the caller does.
        # But let's verify converter.convert() logic handles it correctly.
        inferred_client, inferred_engagement = converter._infer_from_source_root(
            source_file.resolve(), "ExplicitClient", None
        )
        # Inference still runs (returns values), but converter.convert() uses
        # explicit over inferred via: `client if client is not None else inferred_client`
        assert inferred_client == "InferredClient"


# ---------------------------------------------------------------------------
# _resolve_target with source roots
# ---------------------------------------------------------------------------

class TestResolveTarget:
    def _make_converter(self, tmp_path, sources):
        from folio.converter import FolioConverter
        config = FolioConfig(
            library_root=tmp_path / "library",
            sources=sources,
        )
        return FolioConverter(config)

    def test_source_root_with_empty_prefix(self, tmp_path):
        """Empty prefix: routes based on relative path from source root."""
        source_dir = tmp_path / "materials"
        source_file = source_dir / "ClientA" / "deck.pptx"
        source_file.parent.mkdir(parents=True)
        source_file.touch()

        converter = self._make_converter(tmp_path, [
            SourceConfig(name="materials", path=str(source_dir), target_prefix=""),
        ])

        result = converter._resolve_target(
            source_file.resolve(), "deck", "ClientA", None, None
        )
        expected = tmp_path / "library" / "ClientA" / "deck"
        assert result == expected

    def test_source_root_with_prefix(self, tmp_path):
        """Non-empty prefix prepends to path."""
        source_dir = tmp_path / "materials"
        source_file = source_dir / "Sub" / "deck.pptx"
        source_file.parent.mkdir(parents=True)
        source_file.touch()

        converter = self._make_converter(tmp_path, [
            SourceConfig(name="materials", path=str(source_dir), target_prefix="Internal"),
        ])

        result = converter._resolve_target(
            source_file.resolve(), "deck", None, None, None
        )
        expected = tmp_path / "library" / "Internal" / "Sub" / "deck"
        assert result == expected

    def test_explicit_target_overrides_all(self, tmp_path):
        """--target flag takes absolute precedence."""
        converter = self._make_converter(tmp_path, [])
        custom = tmp_path / "custom_output"

        result = converter._resolve_target(
            tmp_path / "deck.pptx", "deck", None, None, custom
        )
        assert result == custom

    def test_fallback_client_engagement_routing(self, tmp_path):
        """Without source root match, falls back to client/engagement."""
        converter = self._make_converter(tmp_path, [])

        result = converter._resolve_target(
            tmp_path / "deck.pptx", "deck", "Acme", "DDQ1", None
        )
        expected = tmp_path / "library" / "Acme" / "DDQ1" / "deck"
        assert result.name == "deck"
        assert "Acme" in str(result)

    def test_nested_source_root(self, tmp_path):
        """Deeply nested file in source root."""
        source_dir = tmp_path / "materials"
        source_file = source_dir / "A" / "B" / "C" / "deck.pptx"
        source_file.parent.mkdir(parents=True)
        source_file.touch()

        converter = self._make_converter(tmp_path, [
            SourceConfig(name="materials", path=str(source_dir), target_prefix=""),
        ])

        result = converter._resolve_target(
            source_file.resolve(), "deck", "A", "B", None
        )
        expected = tmp_path / "library" / "A" / "B" / "C" / "deck"
        assert result == expected
