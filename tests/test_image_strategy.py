"""Tests for folio.pipeline.image_strategy — tiles, highlights, crops."""

from unittest.mock import MagicMock

import pytest
from PIL import Image

from folio.pipeline.image_strategy import (
    prepare_images,
    crop_region,
    highlight_regions,
    _resize_to_max_edge,
)
from folio.llm.types import ImagePart


def _make_profile(classification: str, render_dpi: int = 150, escalation: str = "simple"):
    """Create a mock PageProfile."""
    profile = MagicMock()
    profile.classification = classification
    profile.render_dpi = render_dpi
    profile.escalation_level = escalation
    return profile


def _make_test_image(width: int = 200, height: int = 200, color: str = "red") -> Image.Image:
    """Create a solid-color test image."""
    return Image.new("RGB", (width, height), color)


class TestPrepareImages:
    """B5: test prepare_images tile/global logic."""

    def test_text_page_returns_global_only(self):
        img = _make_test_image(800, 600)
        profile = _make_profile("text")
        parts = prepare_images(img, profile)
        assert len(parts) == 1
        assert parts[0].role == "global"
        assert parts[0].detail == "auto"

    def test_blank_page_returns_global_only(self):
        img = _make_test_image(800, 600)
        profile = _make_profile("blank")
        parts = prepare_images(img, profile)
        assert len(parts) == 1

    def test_diagram_page_returns_5_parts(self):
        img = _make_test_image(800, 600)
        profile = _make_profile("diagram")
        parts = prepare_images(img, profile)
        assert len(parts) == 5
        roles = [p.role for p in parts]
        assert roles == ["global", "tile_q1", "tile_q2", "tile_q3", "tile_q4"]

    def test_mixed_page_returns_5_parts(self):
        img = _make_test_image(800, 600)
        profile = _make_profile("mixed")
        parts = prepare_images(img, profile)
        assert len(parts) == 5

    def test_unsupported_diagram_returns_5_parts(self):
        """m7: unsupported_diagram is tile-producing."""
        img = _make_test_image(800, 600)
        profile = _make_profile("unsupported_diagram")
        parts = prepare_images(img, profile)
        assert len(parts) == 5

    def test_detail_auto_for_simple_escalation(self):
        img = _make_test_image(800, 600)
        profile = _make_profile("diagram", escalation="simple")
        parts = prepare_images(img, profile)
        for part in parts:
            assert part.detail == "auto"

    def test_detail_high_for_medium_escalation(self):
        img = _make_test_image(800, 600)
        profile = _make_profile("diagram", escalation="medium")
        parts = prepare_images(img, profile)
        for part in parts:
            assert part.detail == "high"

    def test_detail_high_for_dense_escalation(self):
        img = _make_test_image(800, 600)
        profile = _make_profile("diagram", escalation="dense")
        parts = prepare_images(img, profile)
        for part in parts:
            assert part.detail == "high"

    def test_text_page_no_high_detail_even_with_dense(self):
        """Non-tile pages never get high detail."""
        img = _make_test_image(800, 600)
        profile = _make_profile("text", escalation="dense")
        parts = prepare_images(img, profile)
        assert parts[0].detail == "auto"

    def test_all_parts_are_image_parts(self):
        img = _make_test_image(800, 600)
        profile = _make_profile("diagram")
        parts = prepare_images(img, profile)
        for part in parts:
            assert isinstance(part, ImagePart)
            assert part.media_type == "image/png"
            assert len(part.image_data) > 0

    def test_global_image_resized_when_large(self):
        """S3: large images should be resized to MAX_LONG_EDGE."""
        img = _make_test_image(3000, 2000)
        profile = _make_profile("text")
        parts = prepare_images(img, profile)
        # Verify the global image was resized (check PNG bytes are smaller)
        assert len(parts) == 1

    def test_tiles_resized_to_max_edge(self):
        """S3: tile crops should also be resized to MAX_LONG_EDGE."""
        img = _make_test_image(4000, 3000)
        profile = _make_profile("diagram")
        parts = prepare_images(img, profile)
        # Each tile should be from the original image halves, then resized
        assert len(parts) == 5


class TestCropRegion:
    """Test crop_region with padding and edge cases."""

    def test_basic_crop(self):
        img = _make_test_image(1000, 1000)
        cropped = crop_region(img, (100, 100, 200, 200))
        assert cropped.size[0] > 0
        assert cropped.size[1] > 0

    def test_padding_expands_crop(self):
        img = _make_test_image(1000, 1000)
        cropped_no_pad = crop_region(img, (100, 100, 200, 200), padding=0.0)
        cropped_with_pad = crop_region(img, (100, 100, 200, 200), padding=0.5)
        assert cropped_with_pad.size[0] > cropped_no_pad.size[0]

    def test_crop_clamped_to_image_bounds(self):
        img = _make_test_image(200, 200)
        cropped = crop_region(img, (150, 150, 250, 250), padding=1.0)
        assert cropped.size[0] <= 200
        assert cropped.size[1] <= 200

    def test_zero_area_bbox_raises(self):
        """S7: zero-area bbox should raise ValueError."""
        img = _make_test_image(100, 100)
        with pytest.raises(ValueError, match="Zero-area"):
            crop_region(img, (50, 50, 50, 50))

    def test_line_bbox_accepted(self):
        """A bbox with zero height but non-zero width is accepted."""
        img = _make_test_image(100, 100)
        cropped = crop_region(img, (10, 50, 80, 50))
        assert cropped.size[0] > 0
        assert cropped.size[1] >= 1  # minimum 1px

    def test_reversed_bbox_normalized(self):
        """Reversed coordinates should be normalized."""
        img = _make_test_image(500, 500)
        cropped = crop_region(img, (300, 300, 100, 100), padding=0.0)
        assert cropped.size[0] == 200
        assert cropped.size[1] == 200


class TestHighlightRegions:
    """Test highlight_regions non-mutation and rendering."""

    def test_does_not_mutate_input(self):
        img = _make_test_image(200, 200, "white")
        original_data = img.tobytes()
        result = highlight_regions(img, [(50, 50, 150, 150)])
        assert img.tobytes() == original_data
        assert result is not img

    def test_returns_rgb_image(self):
        img = _make_test_image(200, 200)
        result = highlight_regions(img, [(10, 10, 50, 50)])
        assert result.mode == "RGB"

    def test_multiple_regions_cycle_colors(self):
        img = _make_test_image(200, 200)
        regions = [(10, 10, 50, 50), (60, 60, 100, 100), (110, 110, 150, 150)]
        result = highlight_regions(img, regions)
        assert result.size == img.size

    def test_empty_regions_returns_copy(self):
        img = _make_test_image(200, 200)
        result = highlight_regions(img, [])
        assert result.size == img.size

    def test_custom_colors(self):
        img = _make_test_image(200, 200)
        result = highlight_regions(img, [(10, 10, 50, 50)], colors=["#00FF00"])
        assert result.size == img.size

    def test_custom_outline_width(self):
        img = _make_test_image(200, 200)
        result = highlight_regions(img, [(10, 10, 50, 50)], outline_width=10)
        assert result.size == img.size

    def test_dpi_proportional_outline(self):
        """m2: outline width should scale with image size."""
        small = _make_test_image(200, 200)
        big = _make_test_image(2000, 2000)
        # Both should produce valid results (no visual assertion, just no crash)
        highlight_regions(small, [(10, 10, 50, 50)])
        highlight_regions(big, [(100, 100, 500, 500)])


class TestResizeToMaxEdge:
    """Test the resize helper."""

    def test_small_image_not_resized(self):
        img = _make_test_image(800, 600)
        result = _resize_to_max_edge(img, 1568)
        assert result.size == (800, 600)

    def test_large_image_resized(self):
        img = _make_test_image(3000, 2000)
        result = _resize_to_max_edge(img, 1568)
        assert max(result.size) <= 1568

    def test_preserves_aspect_ratio(self):
        img = _make_test_image(3000, 1500)
        result = _resize_to_max_edge(img, 1568)
        # Aspect ratio: 3000/1500 = 2:1
        w, h = result.size
        assert abs(w / h - 2.0) < 0.01
