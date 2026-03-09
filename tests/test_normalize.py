"""Tests for normalize.py: input validation, timeout scaling, cleanup, renderer selection."""

import subprocess
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from folio.pipeline.normalize import (
    NormalizationError,
    NormalizationResult,
    _build_powerpoint_export_applescript,
    _compute_timeout,
    _convert_with_powerpoint,
    _escape_applescript_string,
    _find_powerpoint,
    _select_renderer,
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
             patch("folio.pipeline.normalize._find_powerpoint", return_value=False), \
             patch("folio.pipeline.normalize._validate_source"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("soffice", 60)):
            with pytest.raises(NormalizationError, match="timed out"):
                to_pdf(source, output, renderer="libreoffice")

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
             patch("folio.pipeline.normalize._find_powerpoint", return_value=False), \
             patch("folio.pipeline.normalize._validate_source"), \
             patch("subprocess.run", return_value=mock_result):
            import logging
            with caplog.at_level(logging.WARNING):
                to_pdf(source, output, renderer="libreoffice")

        assert "font substitution" in caplog.text


class TestLibreOfficeFallbackMessage:
    """Test actionable fallback guidance when no renderer is available."""

    def test_missing_all_renderers_mentions_options(self, sample_pptx, tmp_path):
        output = tmp_path / "output"
        output.mkdir()

        with patch("folio.pipeline.normalize._find_libreoffice", return_value=None), \
             patch("folio.pipeline.normalize._find_powerpoint", return_value=False):
            with pytest.raises(NormalizationError) as exc_info:
                to_pdf(sample_pptx, output)

        message = str(exc_info.value)
        assert "LibreOffice" in message
        assert "PowerPoint" in message
        assert "PDF" in message


class TestFindPowerPoint:
    """Test PowerPoint discovery."""

    def test_found_on_darwin(self):
        with patch("folio.pipeline.normalize.sys") as mock_sys, \
             patch("folio.pipeline.normalize.Path") as mock_path_cls:
            mock_sys.platform = "darwin"
            mock_path_cls.return_value.exists.return_value = True
            assert _find_powerpoint() is True

    def test_not_found_on_darwin(self):
        with patch("folio.pipeline.normalize.sys") as mock_sys, \
             patch("folio.pipeline.normalize.Path") as mock_path_cls:
            mock_sys.platform = "darwin"
            mock_path_cls.return_value.exists.return_value = False
            assert _find_powerpoint() is False

    def test_always_false_on_linux(self):
        with patch("folio.pipeline.normalize.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert _find_powerpoint() is False


class TestRendererSelection:
    """Test _select_renderer fallback chain."""

    def test_auto_prefers_libreoffice(self):
        with patch("folio.pipeline.normalize._find_libreoffice", return_value="soffice"):
            name, path = _select_renderer("auto")
        assert name == "libreoffice"
        assert path == "soffice"

    def test_auto_falls_back_to_powerpoint_on_darwin(self):
        with patch("folio.pipeline.normalize._find_libreoffice", return_value=None), \
             patch("folio.pipeline.normalize._find_powerpoint", return_value=True):
            name, path = _select_renderer("auto")
        assert name == "powerpoint"
        assert path is None

    def test_auto_raises_on_linux_when_lo_missing(self):
        with patch("folio.pipeline.normalize._find_libreoffice", return_value=None), \
             patch("folio.pipeline.normalize._find_powerpoint", return_value=False):
            with pytest.raises(NormalizationError, match="No PPTX renderer"):
                _select_renderer("auto")

    def test_explicit_powerpoint_works_when_found(self):
        with patch("folio.pipeline.normalize._find_powerpoint", return_value=True):
            name, path = _select_renderer("powerpoint")
        assert name == "powerpoint"

    def test_explicit_powerpoint_raises_when_not_found(self):
        with patch("folio.pipeline.normalize._find_powerpoint", return_value=False):
            with pytest.raises(NormalizationError, match="PowerPoint not found"):
                _select_renderer("powerpoint")

    def test_explicit_libreoffice_works_when_found(self):
        with patch("folio.pipeline.normalize._find_libreoffice", return_value="/usr/bin/soffice"):
            name, path = _select_renderer("libreoffice")
        assert name == "libreoffice"
        assert path == "/usr/bin/soffice"

    def test_explicit_libreoffice_raises_when_not_found(self):
        with patch("folio.pipeline.normalize._find_libreoffice", return_value=None):
            with pytest.raises(NormalizationError, match="LibreOffice not found"):
                _select_renderer("libreoffice")


class TestBuildAppleScript:
    """Test AppleScript generation (export-only, no open POSIX file)."""

    def test_contains_output_path(self):
        script = _build_powerpoint_export_applescript("/tmp/out.pdf", 60, "in.pptx")
        assert 'POSIX file "/tmp/out.pdf"' in script
        # No open POSIX file — opening is via Launch Services
        assert 'open POSIX file' not in script

    def test_contains_timeout(self):
        script = _build_powerpoint_export_applescript("/b.pdf", 120, "a.pptx")
        assert "with timeout of 120 seconds" in script

    def test_uses_named_presentation_not_active(self):
        """A2: save/close must target the specific presentation, not active."""
        script = _build_powerpoint_export_applescript(
            "/tmp/deck.pdf", 60, "deck.pptx"
        )
        assert 'save presentation "deck.pptx"' in script
        assert 'close presentation "deck.pptx"' in script
        assert "active presentation" not in script

    def test_handles_spaces_in_paths(self):
        script = _build_powerpoint_export_applescript(
            "/tmp/output dir/deck file.pdf",
            60,
            "deck file.pptx",
        )
        assert "output dir/deck file.pdf" in script

    def test_escapes_double_quotes_in_paths(self):
        script = _build_powerpoint_export_applescript(
            '/tmp/deck "final".pdf',
            60,
            'deck "final".pptx',
        )
        assert r'deck \"final\".pdf' in script
        # Must NOT contain unescaped quotes that break the literal
        assert 'deck "final"' not in script

    def test_escapes_backslashes_in_paths(self):
        script = _build_powerpoint_export_applescript(
            "/tmp/path\\with\\backslash.pdf",
            60,
            "path\\with\\backslash.pptx",
        )
        assert "path\\\\with\\\\backslash" in script


class TestEscapeAppleScriptString:
    """Test AppleScript string escaping."""

    def test_no_special_chars(self):
        assert _escape_applescript_string("hello") == "hello"

    def test_double_quotes(self):
        assert _escape_applescript_string('say "hi"') == r'say \"hi\"'

    def test_backslashes(self):
        assert _escape_applescript_string("a\\b") == "a\\\\b"

    def test_both(self):
        assert _escape_applescript_string('"\\') == r'\"\\'

    def test_carriage_return(self):
        assert _escape_applescript_string("a\rb") == "a\\rb"

    def test_newline(self):
        assert _escape_applescript_string("a\nb") == "a\\nb"

    def test_tab(self):
        assert _escape_applescript_string("a\tb") == "a\\tb"

    def test_null_byte_stripped(self):
        assert _escape_applescript_string("a\0b") == "ab"


class TestPowerPointConversion:
    """Test PowerPoint conversion via AppleScript."""

    def test_successful_conversion(self, tmp_path):
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        expected_pdf = output / "test.pdf"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        def create_pdf(*args, **kwargs):
            expected_pdf.write_text("pdf content")
            return mock_result

        with patch("subprocess.run", side_effect=create_pdf), \
             patch("folio.pipeline.normalize._wait_for_presentation"):
            _convert_with_powerpoint(source, 60, expected_pdf)

        assert expected_pdf.exists()

    def test_timeout_cleanup(self, tmp_path):
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        expected_pdf = output / "test.pdf"
        expected_pdf.write_text("partial")

        call_count = 0

        def mock_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: open -a succeeds
                return MagicMock(returncode=0)
            if call_count == 2:
                # Second call: export AppleScript times out
                raise subprocess.TimeoutExpired("osascript", 70)
            # Third call is the best-effort cleanup
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=mock_run), \
             patch("folio.pipeline.normalize._wait_for_presentation"):
            with pytest.raises(NormalizationError, match="PowerPoint timed out"):
                _convert_with_powerpoint(source, 60, expected_pdf)

        assert not expected_pdf.exists()

    def test_nonzero_exit_cleanup(self, tmp_path):
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        expected_pdf = output / "test.pdf"
        expected_pdf.write_text("partial")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "AppleScript error: something broke"

        with patch("subprocess.run", return_value=mock_result), \
             patch("folio.pipeline.normalize._wait_for_presentation"):
            with pytest.raises(NormalizationError, match="something broke"):
                _convert_with_powerpoint(source, 60, expected_pdf)

        assert not expected_pdf.exists()

    def test_pdf_not_created(self, tmp_path):
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        expected_pdf = output / "test.pdf"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result), \
             patch("folio.pipeline.normalize._wait_for_presentation"):
            # _convert_with_powerpoint itself doesn't check PDF existence;
            # the caller (to_pdf) does. But stderr is logged on success.
            _convert_with_powerpoint(source, 60, expected_pdf)

        # PDF was never created by our mock
        assert not expected_pdf.exists()

    def test_best_effort_cleanup_targets_specific_presentation(self, tmp_path):
        """Cleanup must close the specific presentation by name, not active presentation."""
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        expected_pdf = output / "test.pdf"

        calls = []

        def mock_run(cmd, **kwargs):
            calls.append(cmd)
            if len(calls) == 1:
                # First call: open -a succeeds
                return MagicMock(returncode=0)
            if len(calls) == 2:
                # Second call: export AppleScript times out
                raise subprocess.TimeoutExpired("osascript", 70)
            # Third call: best-effort cleanup
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=mock_run), \
             patch("folio.pipeline.normalize._wait_for_presentation"):
            with pytest.raises(NormalizationError):
                _convert_with_powerpoint(source, 60, expected_pdf)

        # Calls: open -a (1), export osascript timeout (2), cleanup (3)
        assert len(calls) >= 3
        # Find the cleanup call (the last osascript call with close)
        cleanup_calls = [c for c in calls if isinstance(c, list) and len(c) >= 3
                         and c[0] == "osascript" and "close presentation" in str(c)]
        assert len(cleanup_calls) >= 1
        cleanup_script = cleanup_calls[0][2]
        # Must target the specific file, not blindly close active presentation
        assert 'close presentation "test.pptx"' in cleanup_script
        assert "active presentation" not in cleanup_script


class TestToPdfRendererDispatch:
    """Test to_pdf dispatches to the correct renderer."""

    def test_dispatches_to_libreoffice(self, tmp_path):
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        expected_pdf = output / "test.pdf"
        expected_pdf.write_text("pdf")

        mock_result = MagicMock(returncode=0, stderr="")

        with patch("folio.pipeline.normalize._validate_source"), \
             patch("folio.pipeline.normalize._select_renderer", return_value=("libreoffice", "soffice")), \
             patch("subprocess.run", return_value=mock_result):
            result = to_pdf(source, output, renderer="libreoffice")

        assert result.pdf_path == expected_pdf

    def test_auto_falls_back_to_powerpoint_when_lo_launch_blocked(self, tmp_path):
        """P2: LO on disk but MDM-blocked — auto mode should fall back to PowerPoint.
        PDF is staged then moved to output_dir."""
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        staging = tmp_path / "staging"
        staging.mkdir()

        def mock_subprocess(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if cmd and cmd[0] == "soffice":
                result = MagicMock()
                result.returncode = 1
                result.stderr = "Operation not permitted"
                return result
            return MagicMock(returncode=0, stderr="")

        with patch("folio.pipeline.normalize._validate_source"), \
             patch("folio.pipeline.normalize._find_libreoffice", return_value="soffice"), \
             patch("folio.pipeline.normalize._find_powerpoint", return_value=True), \
             patch("subprocess.run", side_effect=mock_subprocess), \
             patch("folio.pipeline.normalize._convert_with_powerpoint",
                   side_effect=lambda s, t, p: p.write_text("pdf") or None):
            result = to_pdf(source, output, pptx_output_dir=staging, renderer="auto")

        assert result.pdf_path == output / "test.pdf"
        assert result.renderer_used == "powerpoint"

    def test_explicit_libreoffice_does_not_fall_back(self, tmp_path):
        """Explicit libreoffice renderer should NOT fall back to PowerPoint."""
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()

        mock_result = MagicMock(returncode=1, stderr="Operation not permitted")

        with patch("folio.pipeline.normalize._validate_source"), \
             patch("folio.pipeline.normalize._select_renderer", return_value=("libreoffice", "soffice")), \
             patch("folio.pipeline.normalize._find_powerpoint", return_value=True), \
             patch("subprocess.run", return_value=mock_result):
            with pytest.raises(NormalizationError, match="LibreOffice conversion failed"):
                to_pdf(source, output, renderer="libreoffice")

    def test_dispatches_to_powerpoint(self, tmp_path):
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        expected_pdf = output / "test.pdf"

        mock_result = MagicMock(returncode=0, stderr="")

        def create_pdf(source, timeout, expected):
            expected.write_text("pdf")

        with patch("folio.pipeline.normalize._validate_source"), \
             patch("folio.pipeline.normalize._select_renderer", return_value=("powerpoint", None)), \
             patch("folio.pipeline.normalize._convert_with_powerpoint", side_effect=create_pdf):
            result = to_pdf(source, output, renderer="powerpoint")

        assert result.pdf_path == expected_pdf
        assert result.renderer_used == "powerpoint"


class TestPptxOutputDir:
    """Test pptx_output_dir staging seam for PowerPoint renderer.

    PowerPoint writes the PDF to pptx_output_dir (or a default staging dir),
    then the PDF is moved to output_dir for downstream stages.
    """

    def test_powerpoint_stages_then_moves_to_output_dir(self, tmp_path):
        """PowerPoint writes to pptx_output_dir but result lands in output_dir."""
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        staging = tmp_path / "staging"
        staging.mkdir()

        def create_pdf(source, timeout, expected):
            expected.write_text("pdf")

        with patch("folio.pipeline.normalize._validate_source"), \
             patch("folio.pipeline.normalize._select_renderer", return_value=("powerpoint", None)), \
             patch("folio.pipeline.normalize._convert_with_powerpoint", side_effect=create_pdf):
            result = to_pdf(source, output, pptx_output_dir=staging, renderer="powerpoint")

        assert result.pdf_path == output / "test.pdf"
        assert result.pdf_path.parent == output

    def test_libreoffice_ignores_pptx_output_dir(self, tmp_path):
        """LibreOffice should still write to output_dir, not pptx_output_dir."""
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        deck_dir = tmp_path / "deck"
        deck_dir.mkdir()
        expected_pdf = output / "test.pdf"
        expected_pdf.write_text("pdf")

        mock_result = MagicMock(returncode=0, stderr="")

        with patch("folio.pipeline.normalize._validate_source"), \
             patch("folio.pipeline.normalize._select_renderer", return_value=("libreoffice", "soffice")), \
             patch("subprocess.run", return_value=mock_result):
            result = to_pdf(source, output, pptx_output_dir=deck_dir, renderer="libreoffice")

        assert result.pdf_path == expected_pdf
        assert result.pdf_path.parent == output
        assert result.renderer_used == "libreoffice"

    def test_pdf_copy_ignores_pptx_output_dir(self, tmp_path):
        """PDF direct copy should always go to output_dir."""
        source = tmp_path / "test.pdf"
        source.write_bytes(b"%PDF-1.4 content here")
        output = tmp_path / "output"
        output.mkdir()
        deck_dir = tmp_path / "deck"
        deck_dir.mkdir()

        with patch("folio.pipeline.normalize._validate_source"):
            result = to_pdf(source, output, pptx_output_dir=deck_dir)

        assert result.pdf_path.parent == output
        assert result.pdf_path.name == "test.pdf"
        assert result.renderer_used == "pdf-copy"

    def test_auto_fallback_stages_then_moves(self, tmp_path):
        """In auto mode, if LO fails and falls back to PowerPoint,
        the PDF is staged in pptx_output_dir then moved to output_dir."""
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        staging = tmp_path / "staging"
        staging.mkdir()

        def mock_subprocess(cmd, **kwargs):
            if isinstance(cmd, list) and cmd[0] != "osascript":
                return MagicMock(returncode=1, stderr="Operation not permitted")
            return MagicMock(returncode=0, stderr="")

        def create_ppt_pdf(source, timeout, expected):
            expected.write_text("pdf")

        with patch("folio.pipeline.normalize._validate_source"), \
             patch("folio.pipeline.normalize._find_libreoffice", return_value="soffice"), \
             patch("folio.pipeline.normalize._find_powerpoint", return_value=True), \
             patch("subprocess.run", side_effect=mock_subprocess), \
             patch("folio.pipeline.normalize._convert_with_powerpoint", side_effect=create_ppt_pdf):
            result = to_pdf(source, output, pptx_output_dir=staging, renderer="auto")

        assert result.pdf_path == output / "test.pdf"
        assert result.pdf_path.parent == output
        assert result.renderer_used == "powerpoint"

    def test_pptx_output_dir_defaults_to_output_dir(self, tmp_path):
        """When pptx_output_dir is None, PowerPoint uses output_dir."""
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        expected_pdf = output / "test.pdf"

        def create_pdf(source, timeout, expected):
            expected.write_text("pdf")

        with patch("folio.pipeline.normalize._validate_source"), \
             patch("folio.pipeline.normalize._select_renderer", return_value=("powerpoint", None)), \
             patch("folio.pipeline.normalize._convert_with_powerpoint", side_effect=create_pdf):
            result = to_pdf(source, output, renderer="powerpoint")

        assert result.pdf_path == expected_pdf
        assert result.pdf_path.parent == output


class TestPortraitPdfWarning:
    """Test portrait-PDF warning for likely notes-page exports."""

    def test_portrait_pdf_warns(self, tmp_path, caplog):
        """Portrait PDF (height > width) should produce a warning."""
        source = tmp_path / "portrait.pdf"
        # Craft a minimal PDF-like content with a portrait MediaBox
        source.write_bytes(b"%PDF-1.4\n/MediaBox [0 0 612 1008]\n")
        output = tmp_path / "output"
        output.mkdir()

        import logging
        with patch("folio.pipeline.normalize._validate_source"), \
             caplog.at_level(logging.WARNING):
            to_pdf(source, output)

        assert "Portrait PDF detected" in caplog.text

    def test_landscape_pdf_no_warning(self, tmp_path, caplog):
        """Landscape PDF should not produce a portrait warning."""
        source = tmp_path / "landscape.pdf"
        source.write_bytes(b"%PDF-1.4\n/MediaBox [0 0 1008 612]\n")
        output = tmp_path / "output"
        output.mkdir()

        import logging
        with patch("folio.pipeline.normalize._validate_source"), \
             caplog.at_level(logging.WARNING):
            to_pdf(source, output)

        assert "Portrait PDF" not in caplog.text

    def test_portrait_pdf_not_rejected(self, tmp_path):
        """Portrait PDF should be accepted (warning only, no rejection)."""
        source = tmp_path / "portrait.pdf"
        source.write_bytes(b"%PDF-1.4\n/MediaBox [0 0 612 1008]\n")
        output = tmp_path / "output"
        output.mkdir()

        with patch("folio.pipeline.normalize._validate_source"):
            result = to_pdf(source, output)

        assert result.pdf_path.exists()


class TestPowerPointMitigationHint:
    """Test that PowerPoint failures include a mitigation hint."""

    def test_failure_includes_manual_pdf_hint(self, tmp_path):
        """PowerPoint conversion failures should suggest manual PDF export."""
        source = tmp_path / "test.pptx"
        source.write_bytes(b"x" * 100)
        output = tmp_path / "output"
        output.mkdir()
        expected_pdf = output / "test.pdf"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "AppleScript error -9074"

        with patch("subprocess.run", return_value=mock_result), \
             patch("folio.pipeline.normalize._wait_for_presentation"):
            with pytest.raises(NormalizationError) as exc_info:
                _convert_with_powerpoint(source, 60, expected_pdf)

        msg = str(exc_info.value)
        assert "folio convert" in msg
        assert ".pdf" in msg

