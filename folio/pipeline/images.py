"""Stage 2: Image extraction. PDF → PNG images, one per page."""

import logging
from pathlib import Path

from PIL import Image
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)


class ImageExtractionError(Exception):
    """Raised when image extraction fails."""


def extract(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 150,
    fmt: str = "png",
) -> list[Path]:
    """Extract one image per page from a PDF.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save slide images (slides/ subdirectory).
        dpi: Resolution for extraction. Default 150 (readable, reasonable size).
        fmt: Image format. Default 'png' (lossless).

    Returns:
        List of paths to extracted images, ordered by page number.

    Raises:
        ImageExtractionError: If extraction fails or produces no images.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    slides_dir = output_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    try:
        images = convert_from_path(pdf_path, dpi=dpi, fmt=fmt)
    except Exception as e:
        raise ImageExtractionError(f"pdf2image failed: {e}") from e

    if not images:
        raise ImageExtractionError(f"No images extracted from {pdf_path.name}")

    image_paths = []
    for i, image in enumerate(images, 1):
        filename = f"slide-{i:03d}.{fmt}"
        image_path = slides_dir / filename
        image.save(str(image_path))

        # Validate: non-zero size, reasonable dimensions
        _validate_image(image_path, image, slide_num=i)

        image_paths.append(image_path)

    logger.info(
        "Extracted %d images from %s at %d DPI",
        len(image_paths), pdf_path.name, dpi,
    )
    return image_paths


def _validate_image(image_path: Path, image: Image.Image, slide_num: int):
    """Warn on suspicious images (blank, tiny, etc.)."""
    # Check file size
    size_bytes = image_path.stat().st_size
    if size_bytes == 0:
        logger.warning("Slide %d: image file is empty (0 bytes)", slide_num)
        return

    # Check dimensions
    width, height = image.size
    if width < 100 or height < 100:
        logger.warning(
            "Slide %d: unusually small (%dx%d)", slide_num, width, height
        )

    # Check for mostly-blank (>95% white pixels)
    if _is_mostly_blank(image, threshold=0.95):
        logger.warning("Slide %d: appears mostly blank", slide_num)


def _is_mostly_blank(image: Image.Image, threshold: float = 0.95) -> bool:
    """Check if an image is mostly white/blank."""
    try:
        grayscale = image.convert("L")
        pixels = list(grayscale.getdata())
        white_count = sum(1 for p in pixels if p > 240)
        return (white_count / len(pixels)) > threshold
    except Exception:
        return False
