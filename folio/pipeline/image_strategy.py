"""Image strategy: tile preparation and highlight overlay generation.

Exports:
- prepare_images(): produce ImageParts for a page (global ± tiles)
- crop_region(): padded bbox crop from a page image
- highlight_regions(): non-mutating semi-transparent rectangle overlay
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

from ..llm.types import ImagePart

if TYPE_CHECKING:
    from .inspect import PageProfile


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_LONG_EDGE = 1568  # Anthropic / OpenAI recommended max
_TILE_PRODUCING_CLASSES = {"diagram", "mixed", "unsupported_diagram"}
_DEFAULT_PALETTE = [
    "#FF6B6B",  # coral red
    "#4ECDC4",  # teal
    "#FFE66D",  # warm yellow
    "#95E1D3",  # mint
    "#F38181",  # salmon
    "#AA96DA",  # lavender
    "#FCEABB",  # cream
    "#A8D8EA",  # sky blue
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def prepare_images(
    page_image: Image.Image,
    page_profile: "PageProfile",
) -> list[ImagePart]:
    """Produce ImageParts for a page: global image ± quadrant tiles.

    Tile-producing classes (diagram, mixed, unsupported_diagram):
        5 ImageParts — 1 global + 4 quadrant tiles.
    Global-only classes (text, text_light, blank, image_blank):
        1 ImagePart — global only.

    Detail rules:
        - default detail="auto"
        - if tile-producing AND escalation in {"medium", "dense"},
          all parts get detail="high"
    """
    classification = page_profile.classification
    escalation = getattr(page_profile, "escalation_level", "simple")
    produces_tiles = classification in _TILE_PRODUCING_CLASSES
    use_high_detail = (
        produces_tiles and escalation in {"medium", "dense"}
    )
    detail = "high" if use_high_detail else "auto"

    # Global image: resize if long edge > 1568
    global_img = _resize_to_max_edge(page_image, _MAX_LONG_EDGE)
    global_part = ImagePart(
        image_data=_to_png_bytes(global_img),
        role="global",
        media_type="image/png",
        detail=detail,
    )

    if not produces_tiles:
        return [global_part]

    # Quadrant tiles from the FULL rendered image (not resized global)
    w, h = page_image.size
    half_w = w // 2
    half_h = h // 2

    tile_boxes = [
        ("tile_q1", (0, 0, half_w, half_h)),           # top-left
        ("tile_q2", (half_w, 0, w, half_h)),            # top-right
        ("tile_q3", (0, half_h, half_w, h)),            # bottom-left
        ("tile_q4", (half_w, half_h, w, h)),            # bottom-right
    ]

    tile_parts = []
    for role, box in tile_boxes:
        tile_img = page_image.crop(box)
        tile_parts.append(ImagePart(
            image_data=_to_png_bytes(tile_img),
            role=role,
            media_type="image/png",
            detail=detail,
        ))

    return [global_part] + tile_parts


def crop_region(
    page_image: Image.Image,
    bbox: tuple[float, float, float, float],
    padding: float = 0.1,
) -> Image.Image:
    """Crop a region from a page image with padding.

    Args:
        page_image: Source image.
        bbox: (x0, y0, x1, y1) in pixel coordinates.
        padding: Percentage of bbox dimensions to add as padding.
            0.1 = 10% padding on each side.

    Returns:
        A new cropped Image.
    """
    w, h = page_image.size

    # Normalize bbox ordering
    x0 = min(bbox[0], bbox[2])
    y0 = min(bbox[1], bbox[3])
    x1 = max(bbox[0], bbox[2])
    y1 = max(bbox[1], bbox[3])

    # Calculate padding
    bw = x1 - x0
    bh = y1 - y0
    pad_x = bw * padding
    pad_y = bh * padding

    # Apply padding and clamp to image bounds
    crop_x0 = max(0, x0 - pad_x)
    crop_y0 = max(0, y0 - pad_y)
    crop_x1 = min(w, x1 + pad_x)
    crop_y1 = min(h, y1 + pad_y)

    return page_image.crop((int(crop_x0), int(crop_y0), int(crop_x1), int(crop_y1)))


def highlight_regions(
    page_image: Image.Image,
    regions: list[tuple[float, float, float, float]],
    colors: list[str] | None = None,
) -> Image.Image:
    """Draw semi-transparent rectangle highlights over regions.

    Does NOT mutate the input image. Returns a new image with
    thick semi-transparent rectangles drawn over the specified regions.

    Args:
        page_image: Source image (not modified).
        regions: List of (x0, y0, x1, y1) bounding boxes in pixel coordinates.
        colors: Optional list of hex color strings. Cycles through
            a default palette if not provided.
    """
    palette = colors if colors else _DEFAULT_PALETTE
    result = page_image.copy().convert("RGBA")
    overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for i, region in enumerate(regions):
        color_hex = palette[i % len(palette)]
        # Parse hex color
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        fill_color = (r, g, b, 50)     # semi-transparent fill
        outline_color = (r, g, b, 180)  # more opaque outline

        x0 = min(region[0], region[2])
        y0 = min(region[1], region[3])
        x1 = max(region[0], region[2])
        y1 = max(region[1], region[3])

        draw.rectangle([x0, y0, x1, y1], fill=fill_color, outline=outline_color, width=3)

    result = Image.alpha_composite(result, overlay)
    return result.convert("RGB")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resize_to_max_edge(image: Image.Image, max_edge: int) -> Image.Image:
    """Resize image so the long edge is at most max_edge, preserving aspect ratio."""
    w, h = image.size
    long_edge = max(w, h)
    if long_edge <= max_edge:
        return image.copy()

    scale = max_edge / long_edge
    new_w = int(w * scale)
    new_h = int(h * scale)
    return image.resize((new_w, new_h), Image.LANCZOS)


def _to_png_bytes(image: Image.Image) -> bytes:
    """Serialize a PIL Image to PNG bytes."""
    buf = io.BytesIO()
    # Ensure RGB mode for PNG serialization
    if image.mode == "RGBA":
        image = image.convert("RGB")
    image.save(buf, format="PNG")
    return buf.getvalue()
