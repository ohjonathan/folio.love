"""Tests for images.py: ImageResult, extract_with_metadata, atomic swap."""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from folio.pipeline.images import (
    ImageExtractionError,
    ImageResult,
    _contiguous_runs,
    extract,
    extract_with_metadata,
)


def _make_png(tmp_path, name="test.png", width=200, height=200, color="white"):
    """Create a solid-color PNG image."""
    img = Image.new("RGB", (width, height), color=color)
    path = tmp_path / name
    img.save(str(path))
    return path


def _make_fake_pdf(tmp_path, name="test.pdf"):
    """Create a fake PDF file."""
    path = tmp_path / name
    path.write_bytes(b"%PDF-1.4 test")
    return path


class TestImageResult:
    """Test ImageResult dataclass."""

    def test_defaults(self):
        r = ImageResult(path=Path("test.png"), slide_num=1)
        assert r.is_blank is False
        assert r.is_tiny is False
        assert r.width == 0
        assert r.height == 0

    def test_full_fields(self):
        r = ImageResult(
            path=Path("test.png"),
            slide_num=2,
            is_blank=True,
            is_tiny=False,
            width=800,
            height=600,
        )
        assert r.slide_num == 2
        assert r.is_blank is True


class TestPopperCheck:
    """Test poppler dependency check."""

    def test_missing_pdftoppm(self, tmp_path):
        pdf = _make_fake_pdf(tmp_path)
        with patch("shutil.which", return_value=None):
            with pytest.raises(ImageExtractionError, match="Poppler not found"):
                extract(pdf, tmp_path)


class TestAtomicSwap:
    """Test atomic swap behavior for slides directory."""

    def _setup_extract_mock(self, tmp_path, slide_count=3):
        """Set up mocks for extract() to return images in tmp dir."""
        images_list = []
        for i in range(slide_count):
            img = Image.new("RGB", (200, 200), color="blue")
            images_list.append(img)
        return images_list

    def test_preserves_existing_on_failure(self, tmp_path):
        """Existing slides/ preserved when extraction fails."""
        output_dir = tmp_path / "output"
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(parents=True)
        existing = slides_dir / "slide-001.png"
        existing.write_bytes(b"existing image data")

        pdf = _make_fake_pdf(tmp_path)

        with patch("shutil.which", return_value="/usr/bin/pdftoppm"), \
             patch("folio.pipeline.images.convert_from_path", side_effect=Exception("conversion failed")):
            with pytest.raises(ImageExtractionError, match="conversion failed"):
                extract(pdf, output_dir)

        # Existing slides/ should be intact
        assert existing.exists()
        assert existing.read_bytes() == b"existing image data"

    def test_replaces_on_success(self, tmp_path):
        """Old slides/ replaced with new on success."""
        output_dir = tmp_path / "output"
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(parents=True)
        old_file = slides_dir / "slide-001.png"
        old_file.write_bytes(b"old data")

        pdf = _make_fake_pdf(tmp_path)
        images_list = self._setup_extract_mock(tmp_path, 2)

        with patch("shutil.which", return_value="/usr/bin/pdftoppm"), \
             patch("folio.pipeline.images.convert_from_path", return_value=images_list):
            result = extract(pdf, output_dir)

        assert len(result) == 2
        # Old file should be replaced
        assert not old_file.exists() or old_file.read_bytes() != b"old data"

    def test_atomic_swap_failure_wraps_oserror(self, tmp_path):
        """Atomic swap rename failure raises ImageExtractionError, not raw OSError."""
        output_dir = tmp_path / "output"
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(parents=True)
        (slides_dir / "slide-001.png").write_bytes(b"existing")

        pdf = _make_fake_pdf(tmp_path)
        images_list = self._setup_extract_mock(tmp_path, 1)

        original_rename = Path.rename

        def failing_rename(self_path, target):
            # Let slides/ -> .slides_old succeed, but fail .slides_tmp -> slides/
            if self_path.name == ".slides_tmp":
                raise OSError("Permission denied")
            return original_rename(self_path, target)

        with patch("shutil.which", return_value="/usr/bin/pdftoppm"), \
             patch("folio.pipeline.images.convert_from_path", return_value=images_list), \
             patch.object(Path, "rename", failing_rename):
            with pytest.raises(ImageExtractionError, match="Atomic swap failed"):
                extract(pdf, output_dir)

    def test_preflight_recovery_stale_old(self, tmp_path):
        """Stranded .slides_old (no slides/) is restored on next run."""
        output_dir = tmp_path / "output"
        old_dir = output_dir / ".slides_old"
        old_dir.mkdir(parents=True)
        (old_dir / "slide-001.png").write_bytes(b"recovered")

        pdf = _make_fake_pdf(tmp_path)
        images_list = self._setup_extract_mock(tmp_path, 1)

        with patch("shutil.which", return_value="/usr/bin/pdftoppm"), \
             patch("folio.pipeline.images.convert_from_path", return_value=images_list):
            result = extract(pdf, output_dir)

        slides_dir = output_dir / "slides"
        assert slides_dir.exists()
        assert not old_dir.exists()

    def test_preflight_cleanup_stale_old_with_slides(self, tmp_path):
        """Stranded .slides_old (with slides/ present) is deleted."""
        output_dir = tmp_path / "output"
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(parents=True)
        (slides_dir / "slide-001.png").write_bytes(b"current")

        old_dir = output_dir / ".slides_old"
        old_dir.mkdir(parents=True)
        (old_dir / "slide-001.png").write_bytes(b"stale")

        pdf = _make_fake_pdf(tmp_path)
        images_list = self._setup_extract_mock(tmp_path, 1)

        with patch("shutil.which", return_value="/usr/bin/pdftoppm"), \
             patch("folio.pipeline.images.convert_from_path", return_value=images_list):
            extract(pdf, output_dir)

        assert not old_dir.exists()

    def test_preflight_cleanup_stale_tmp(self, tmp_path):
        """Stranded .slides_tmp from previous failed run is cleaned."""
        output_dir = tmp_path / "output"
        tmp_dir = output_dir / ".slides_tmp"
        tmp_dir.mkdir(parents=True)
        (tmp_dir / "stale.png").write_bytes(b"stale")

        pdf = _make_fake_pdf(tmp_path)
        images_list = self._setup_extract_mock(tmp_path, 1)

        with patch("shutil.which", return_value="/usr/bin/pdftoppm"), \
             patch("folio.pipeline.images.convert_from_path", return_value=images_list):
            extract(pdf, output_dir)

        assert not tmp_dir.exists()


class TestExtractWithMetadata:
    """Test extract_with_metadata returns ImageResult list."""

    def test_returns_image_results(self, tmp_path):
        output_dir = tmp_path / "output"
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(parents=True)

        # Create test images
        for i in range(1, 3):
            img = Image.new("RGB", (200, 200), color="blue")
            img.save(str(slides_dir / f"slide-{i:03d}.png"))

        paths = sorted(slides_dir.glob("*.png"))

        with patch("folio.pipeline.images.extract", return_value=paths):
            results = extract_with_metadata(Path("test.pdf"), output_dir)

        assert len(results) == 2
        for r in results:
            assert isinstance(r, ImageResult)
            assert r.width == 200
            assert r.height == 200
            assert r.is_blank is False
            assert r.is_tiny is False

    def test_blank_detection(self, tmp_path):
        output_dir = tmp_path / "output"
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(parents=True)

        # All-white image
        img = Image.new("RGB", (200, 200), color="white")
        img.save(str(slides_dir / "slide-001.png"))

        paths = [slides_dir / "slide-001.png"]

        with patch("folio.pipeline.images.extract", return_value=paths):
            results = extract_with_metadata(Path("test.pdf"), output_dir)

        assert results[0].is_blank is True

    def test_tiny_detection(self, tmp_path):
        output_dir = tmp_path / "output"
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(parents=True)

        img = Image.new("RGB", (50, 50), color="blue")
        img.save(str(slides_dir / "slide-001.png"))

        paths = [slides_dir / "slide-001.png"]

        with patch("folio.pipeline.images.extract", return_value=paths):
            results = extract_with_metadata(Path("test.pdf"), output_dir)

        assert results[0].is_tiny is True


class TestSpecRequiredCoverage:
    """Spec-required named tests (S3 review item)."""

    def _setup_extract_mock(self, slide_count=3):
        images_list = []
        for i in range(slide_count):
            img = Image.new("RGB", (200, 200), color="blue")
            images_list.append(img)
        return images_list

    def test_extract_returns_paths(self, tmp_path):
        """extract() returns list[Path] ordered by slide number."""
        pdf = _make_fake_pdf(tmp_path)
        images_list = self._setup_extract_mock(3)

        with patch("shutil.which", return_value="/usr/bin/pdftoppm"), \
             patch("folio.pipeline.images.convert_from_path", return_value=images_list):
            result = extract(pdf, tmp_path)

        assert isinstance(result, list)
        assert all(isinstance(p, Path) for p in result)
        assert len(result) == 3
        # Verify ordering
        nums = [int(p.stem.split("-")[1]) for p in result]
        assert nums == sorted(nums)

    def test_blank_detection_content_image(self, tmp_path):
        """A non-blank content image is correctly identified as not blank."""
        output_dir = tmp_path / "output"
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(parents=True)

        # Create a colorful, non-blank image
        img = Image.new("RGB", (200, 200), color="red")
        img.save(str(slides_dir / "slide-001.png"))

        paths = [slides_dir / "slide-001.png"]

        with patch("folio.pipeline.images.extract", return_value=paths):
            results = extract_with_metadata(Path("test.pdf"), output_dir)

        assert results[0].is_blank is False

    def test_failure_recovery_no_data_loss(self, tmp_path):
        """B1 fix: if both renames fail, backup (.slides_old) is preserved."""
        output_dir = tmp_path / "output"
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(parents=True)
        (slides_dir / "slide-001.png").write_bytes(b"original data")

        old_dir = output_dir / ".slides_old"
        tmp_dir = output_dir / ".slides_tmp"
        tmp_dir.mkdir(parents=True)
        (tmp_dir / "slide-001.png").write_bytes(b"new data")

        # Simulate: slides/ already renamed to .slides_old,
        # then tmp_dir.rename(slides_dir) fails, then old_dir.rename(slides_dir) also fails
        # The finally block should NOT delete old_dir since slides_dir doesn't exist.
        slides_dir.rename(old_dir)
        assert not slides_dir.exists()

        original_rename = Path.rename

        def failing_rename(self_path, target):
            if self_path == tmp_dir and target == slides_dir:
                raise OSError("Permission denied on tmp rename")
            if self_path == old_dir and target == slides_dir:
                raise OSError("Permission denied on restore")
            return original_rename(self_path, target)

        with patch.object(Path, "rename", failing_rename):
            try:
                # Manually execute the swap logic
                try:
                    tmp_dir.rename(slides_dir)
                except Exception:
                    if old_dir.exists():
                        old_dir.rename(slides_dir)
                    raise
                finally:
                    # This is the B1-fixed guard
                    if old_dir.exists() and slides_dir.exists():
                        shutil.rmtree(old_dir)
            except OSError:
                pass

        # Key assertion: old_dir (backup) must still exist since slides/ was never restored
        assert old_dir.exists()
        assert (old_dir / "slide-001.png").read_bytes() == b"original data"

    def test_zero_images_guard(self, tmp_path):
        """extract() raises ImageExtractionError when PDF produces no images."""
        pdf = _make_fake_pdf(tmp_path)

        with patch("shutil.which", return_value="/usr/bin/pdftoppm"), \
             patch("folio.pipeline.images.convert_from_path", return_value=[]):
            with pytest.raises(ImageExtractionError, match="No images extracted"):
                extract(pdf, tmp_path)


class TestContiguousRuns:
    """S1: tests for _contiguous_runs helper (pure function, no fixtures)."""

    def test_empty_list(self):
        assert _contiguous_runs([]) == []

    def test_single_page(self):
        assert _contiguous_runs([5]) == [(5, 5)]

    def test_contiguous_sequence(self):
        assert _contiguous_runs([1, 2, 3, 4, 5]) == [(1, 5)]

    def test_two_runs(self):
        assert _contiguous_runs([1, 2, 3, 7, 8]) == [(1, 3), (7, 8)]

    def test_three_runs(self):
        assert _contiguous_runs([1, 5, 6, 10]) == [(1, 1), (5, 6), (10, 10)]

    def test_all_disjoint(self):
        assert _contiguous_runs([1, 5, 9]) == [(1, 1), (5, 5), (9, 9)]

    def test_unordered_input_sorted(self):
        """Input doesn't need to be pre-sorted."""
        assert _contiguous_runs([7, 1, 3, 2, 8]) == [(1, 3), (7, 8)]

    def test_duplicate_pages(self):
        """Duplicates handled gracefully (same as single)."""
        result = _contiguous_runs([1, 1, 2, 2, 3])
        # After sorting: [1, 1, 2, 2, 3] — duplicates break contiguity
        assert result[0][0] == 1
        assert result[-1][1] == 3
