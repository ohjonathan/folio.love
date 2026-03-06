"""Stage 2: Image extraction. PDF → PNG images, one per page."""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)


class ImageExtractionError(Exception):
    """Raised when image extraction fails."""


@dataclass
class ImageResult:
    """Result of extracting a single slide image."""
    path: Path
    slide_num: int
    is_blank: bool = False
    is_tiny: bool = False
    width: int = 0
    height: int = 0


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
    tmp_dir = output_dir / ".slides_tmp"
    old_dir = output_dir / ".slides_old"

    if not shutil.which("pdftoppm"):
        raise ImageExtractionError(
            "Poppler not found (pdftoppm). Install with: "
            "brew install poppler (macOS) or apt install poppler-utils (Linux)"
        )

    # Preflight: recover from interrupted previous runs
    if old_dir.exists():
        if not slides_dir.exists():
            # Crashed after slides/ → .slides_old but before .slides_tmp → slides/
            old_dir.rename(slides_dir)
            logger.warning("Recovered slides/ from interrupted swap: %s", old_dir)
        else:
            # Stale leftover — slides/ is intact
            shutil.rmtree(old_dir)
            logger.debug("Cleaned up stale .slides_old: %s", old_dir)

    try:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)  # clean leftover from previous failed run
        tmp_dir.mkdir(parents=True)
        images = convert_from_path(pdf_path, dpi=dpi, fmt=fmt)

        if not images:
            raise ImageExtractionError(f"No images extracted from {pdf_path.name}")

        image_paths = []
        for i, image in enumerate(images, 1):
            filename = f"slide-{i:03d}.{fmt}"
            image_path = tmp_dir / filename
            image.save(str(image_path))

            # Validate: non-zero size, reasonable dimensions
            _validate_image(image_path, image, slide_num=i)

            image_paths.append(image_path)

    except Exception as e:
        # Failure: delete only tmp_dir, existing slides/ untouched
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
            logger.debug("Cleaned up temp slides dir: %s", tmp_dir)
        if isinstance(e, ImageExtractionError):
            raise
        raise ImageExtractionError(f"pdf2image failed: {e}") from e

    # Success: atomic swap
    if slides_dir.exists():
        slides_dir.rename(old_dir)
    try:
        tmp_dir.rename(slides_dir)
    except Exception:
        # Restore old slides on rename failure
        if old_dir.exists():
            old_dir.rename(slides_dir)
        raise
    finally:
        # Only delete backup when slides/ has been successfully restored or replaced.
        # If both renames failed, old_dir is the only remaining copy.
        if old_dir.exists() and slides_dir.exists():
            shutil.rmtree(old_dir)

    # Rewrite paths to final location
    image_paths = sorted(slides_dir.glob(f"*.{fmt}"))

    logger.info(
        "Extracted %d images from %s at %d DPI",
        len(image_paths), pdf_path.name, dpi,
    )
    return image_paths


def extract_with_metadata(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 150,
    fmt: str = "png",
) -> list[ImageResult]:
    """Extract slide images with blank/tiny/dimension metadata.

    Wraps extract() and annotates each result. Use this when the caller
    needs image quality metadata (e.g., converter blank-slide detection).
    """
    paths = extract(pdf_path, output_dir, dpi=dpi, fmt=fmt)
    results = []
    for i, path in enumerate(paths, 1):
        with Image.open(path) as img:
            width, height = img.size
            is_blank = _is_mostly_blank(img, threshold=0.95)
            is_tiny = width < 100 or height < 100

        # S5 fix: suppress duplicate warnings already emitted by _validate_image in extract()
        results.append(ImageResult(
            path=path,
            slide_num=i,
            is_blank=is_blank,
            is_tiny=is_tiny,
            width=width,
            height=height,
        ))
    return results


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
