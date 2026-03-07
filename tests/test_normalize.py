"""Tests for normalize.py: input validation, timeout scaling, cleanup."""

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from folio.pipeline.normalize import (
    NormalizationError,
    _compute_timeout,
    _validate_source,
    to_pdf,
)


class TestValidateSource:
    """Test _validate_source pre-flight checks."""

    def test_empty_file(self, empty_file):
        with pytest.raises(NormalizationError, match="empty.*0 bytes"):
            _validate_source(empty_file)

    def test_too_large(self, tmp_path):
        path = tmp_path / "huge.pptx"
        path.write_bytes(b"x")
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value = MagicMock(st_size=600 * 1024 * 1024)
            with pytest.raises(NormalizationError, match="too large"):
                _validate_source(path)

    def test_not_zip(self, non_zip_pptx):
        with pytest.raises(NormalizationError, match="not a ZIP"):
            _validate_source(non_zip_pptx)

    def test_password_protected(self, tmp_path):
        path = tmp_path / "encrypted.pptx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("EncryptedPackage", "encrypted data")
            zf.writestr("EncryptedInfo", "encryption info")
        with pytest.raises(NormalizationError, match="Password-protected"):
            _validate_source(path)

    def test_malformed_ooxml(self, tmp_path):
        path = tmp_path / "bad.pptx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("random.xml", "not ooxml")
        with pytest.raises(NormalizationError, match="missing.*Content_Types"):
            _validate_source(path)

    def test_valid_pptx(self, sample_pptx):
        # Should not raise
        _validate_source(sample_pptx)

    def test_pdf_skips_zip_checks(self, tmp_path):
        """PDF files skip ZIP validation."""
        path = tmp_path / "test.pdf"
        path.write_bytes(b"%PDF-1.4 content")
        _validate_source(path)

    def test_nonexistent_file(self, tmp_path):
        path = tmp_path / "nope.pptx"
        with pytest.raises(NormalizationError, match="Source not found"):
            _validate_source(path)


class TestComputeTimeout:
    """Test timeout scaling logic."""

    def test_small_file(self, tmp_path):
        path = tmp_path / "small.pptx"
        path.write_bytes(b"x" * (1024 * 1024))  # 1 MB
        result = _compute_timeout(path, 60)
        assert result == 61

    def test_large_file(self, tmp_path):
        path = tmp_path / "large.pptx"
        path.write_bytes(b"x")
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value = MagicMock(st_size=250 * 1024 * 1024)
            result = _compute_timeout(path, 60)
        assert result == 300  # capped

    def test_zero_file(self, tmp_path):
        path = tmp_path / "zero.pptx"
        path.touch()
        result = _compute_timeout(path, 60)
        assert result == 60

    def test_negative_base(self, tmp_path):
        """M7: negative base_timeout floors to 10."""
        path = tmp_path / "test.pptx"
        path.write_bytes(b"x" * (1024 * 1024))  # 1 MB
        result = _compute_timeout(path, -5)
        assert result == 11  # max(-5, 10) + 1 = 11

    def test_zero_base(self, tmp_path):
        """M7: zero base_timeout floors to 10."""
        path = tmp_path / "test.pptx"
        path.write_bytes(b"x" * (1024 * 1024))  # 1 MB
        result = _compute_timeout(path, 0)
        assert result == 11  # max(0, 10) + 1 = 11


class TestCleanup:
    """Test cleanup on failure."""

    def test_cleanup_on_timeout(self, tmp_path):
        """Partial PDF should be removed after timeout."""
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()

        expected_pdf = output / "test.pdf"
        expected_pdf.write_text("partial")

        with patch("folio.pipeline.normalize._find_libreoffice", return_value="soffice"), \
             patch("folio.pipeline.normalize._validate_source"), \
             patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("soffice", 60)):
            with pytest.raises(NormalizationError, match="timed out"):
                to_pdf(source, output)

        assert not expected_pdf.exists()

    def test_stderr_logged_on_success(self, tmp_path, caplog):
        """Non-empty stderr produces warning log."""
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()

        expected_pdf = output / "test.pdf"
        expected_pdf.write_text("valid pdf")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = "Warning: font substitution"

        with patch("folio.pipeline.normalize._find_libreoffice", return_value="soffice"), \
             patch("folio.pipeline.normalize._validate_source"), \
             patch("subprocess.run", return_value=mock_result):
            import logging
            with caplog.at_level(logging.WARNING):
                to_pdf(source, output)

        assert "font substitution" in caplog.text


class TestLibreOfficeFallbackMessage:
    """Test actionable fallback guidance when LibreOffice is unavailable."""

    def test_missing_libreoffice_mentions_pdf_workaround(self, sample_pptx, tmp_path):
        output = tmp_path / "output"
        output.mkdir()

        with patch("folio.pipeline.normalize._find_libreoffice", return_value=None):
            with pytest.raises(NormalizationError) as exc_info:
                to_pdf(sample_pptx, output)

        message = str(exc_info.value)
        assert "LibreOffice not found" in message
        assert "PowerPoint" in message
        assert "folio convert <deck>.pdf" in message
