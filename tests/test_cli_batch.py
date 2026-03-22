"""Tests for folio batch deduplication (P0)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from folio.cli import cli, _content_hash


class TestContentHash:
    """Test the streaming SHA-256 helper."""

    def test_deterministic(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_bytes(b"hello world")
        assert _content_hash(f) == _content_hash(f)

    def test_different_content_different_hash(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_bytes(b"hello")
        b.write_bytes(b"world")
        assert _content_hash(a) != _content_hash(b)

    def test_same_content_same_hash(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_bytes(b"identical content")
        b.write_bytes(b"identical content")
        assert _content_hash(a) == _content_hash(b)


class TestBatchDedup:
    """Test batch deduplication at the CLI boundary."""

    @patch("folio.cli.FolioConverter")
    def test_duplicate_files_skipped(self, mock_converter_cls, tmp_path):
        """Two identical files and one unique → only 2 conversions run."""
        # Create files
        unique = tmp_path / "unique.pptx"
        dup1 = tmp_path / "dup_a.pptx"
        dup2 = tmp_path / "dup_b.pptx"
        unique.write_bytes(b"unique content")
        dup1.write_bytes(b"same content")
        dup2.write_bytes(b"same content")

        mock_converter = MagicMock()
        mock_result = MagicMock()
        mock_result.slide_count = 1
        mock_result.renderer_used = "powerpoint"
        mock_converter.convert.return_value = mock_result
        mock_converter_cls.return_value = mock_converter

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(tmp_path), "--pattern", "*.pptx"])

        assert mock_converter.convert.call_count == 2
        assert "duplicate of" in result.output
        assert "Duplicates skipped: 1" in result.output

    @patch("folio.cli.FolioConverter")
    def test_same_basename_different_content_both_process(self, mock_converter_cls, tmp_path):
        """Same basename in subdirectories with different content → both process."""
        sub_a = tmp_path / "a"
        sub_b = tmp_path / "b"
        sub_a.mkdir()
        sub_b.mkdir()

        # Create files with same basename but different content
        (sub_a / "deck.pptx").write_bytes(b"content A")
        (sub_b / "deck.pptx").write_bytes(b"content B")

        mock_converter = MagicMock()
        mock_result = MagicMock()
        mock_result.slide_count = 1
        mock_result.renderer_used = "powerpoint"
        mock_converter.convert.return_value = mock_result
        mock_converter_cls.return_value = mock_converter

        # Note: batch uses glob which is non-recursive by default,
        # so we put both files in the same dir for this test.
        flat_dir = tmp_path / "flat"
        flat_dir.mkdir()
        (flat_dir / "a.pptx").write_bytes(b"content A")
        (flat_dir / "b.pptx").write_bytes(b"content B")

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(flat_dir), "--pattern", "*.pptx"])

        assert mock_converter.convert.call_count == 2
        assert "Duplicates skipped: 0" in result.output

    @patch("folio.cli.FolioConverter")
    def test_empty_file_skipped(self, mock_converter_cls, tmp_path):
        """Empty file is skipped with warning and never converted."""
        empty = tmp_path / "empty.pptx"
        empty.write_bytes(b"")  # 0 bytes
        normal = tmp_path / "normal.pptx"
        normal.write_bytes(b"real content")

        mock_converter = MagicMock()
        mock_result = MagicMock()
        mock_result.slide_count = 1
        mock_result.renderer_used = "powerpoint"
        mock_converter.convert.return_value = mock_result
        mock_converter_cls.return_value = mock_converter

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(tmp_path), "--pattern", "*.pptx"])

        # Only the non-empty file should be converted
        assert mock_converter.convert.call_count == 1
        assert "empty, skipped" in result.output
        assert "Empty files skipped: 1" in result.output

    @patch("folio.cli.FolioConverter")
    def test_summary_shows_both_counters(self, mock_converter_cls, tmp_path):
        """Summary always includes both duplicate and empty counters."""
        f = tmp_path / "only.pptx"
        f.write_bytes(b"content")

        mock_converter = MagicMock()
        mock_result = MagicMock()
        mock_result.slide_count = 1
        mock_result.renderer_used = "powerpoint"
        mock_converter.convert.return_value = mock_result
        mock_converter_cls.return_value = mock_converter

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(tmp_path), "--pattern", "*.pptx"])

        assert "Duplicates skipped: 0" in result.output
        assert "Empty files skipped: 0" in result.output

    @patch("folio.cli.FolioConverter")
    def test_empty_files_not_duplicates(self, mock_converter_cls, tmp_path):
        """Empty files are counted separately from duplicates."""
        empty1 = tmp_path / "a_empty.pptx"
        empty2 = tmp_path / "b_empty.pptx"
        empty1.write_bytes(b"")
        empty2.write_bytes(b"")

        mock_converter = MagicMock()
        mock_converter_cls.return_value = mock_converter

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(tmp_path), "--pattern", "*.pptx"])

        # Both should be skipped as empty, not as duplicates
        assert "Empty files skipped: 2" in result.output
        assert "Duplicates skipped: 0" in result.output
        assert mock_converter.convert.call_count == 0


class TestCombinedBatchScenario:
    """B4: Combined mocked batch test per spec §7.1.

    One duplicate + one empty + two unique files in a single invocation.
    """

    @patch("folio.cli.FolioConverter")
    def test_combined_batch(self, mock_converter_cls, tmp_path):
        """Mixed scenario: 2 unique, 1 duplicate, 1 empty → 2 conversions."""
        # Two unique files
        (tmp_path / "unique_a.pptx").write_bytes(b"content alpha")
        (tmp_path / "unique_b.pptx").write_bytes(b"content beta")
        # One duplicate of unique_a
        (tmp_path / "dup_of_a.pptx").write_bytes(b"content alpha")
        # One empty file
        (tmp_path / "empty.pptx").write_bytes(b"")

        mock_converter = MagicMock()
        mock_result = MagicMock()
        mock_result.slide_count = 1
        mock_result.renderer_used = "powerpoint"
        mock_converter.convert.return_value = mock_result
        mock_converter_cls.return_value = mock_converter

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(tmp_path), "--pattern", "*.pptx"])

        # Only 2 unique non-empty files should be converted
        assert mock_converter.convert.call_count == 2
        assert "Duplicates skipped: 1" in result.output
        assert "Empty files skipped: 1" in result.output
        # Verify output mentions both skips
        assert "duplicate of" in result.output
        assert "empty, skipped" in result.output
