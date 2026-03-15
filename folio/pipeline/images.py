"""Stage 2: Image extraction. PDF → PNG images, one per page.

Supports both single-DPI (legacy) and per-page DPI rendering
driven by PR 1 PageProfile.render_dpi.
"""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image
from pdf2image import convert_from_path

if TYPE_CHECKING:
    from .inspect import PageProfile

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
    render_dpi: int = 0


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
    try:
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
    except ImageExtractionError:
        raise
    except Exception as e:
        raise ImageExtractionError(f"Atomic swap failed: {e}") from e

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
    page_profiles: "dict[int, PageProfile] | None" = None,
) -> list[ImageResult]:
    """Extract slide images with blank/tiny/dimension metadata.

    When page_profiles is provided, renders each page individually at
    its PageProfile.render_dpi. Otherwise falls back to the single-DPI
    code path.

    Wraps extract() and annotates each result. Use this when the caller
    needs image quality metadata (e.g., converter blank-slide detection).
    """
    if page_profiles is not None:
        return _extract_per_page_dpi(pdf_path, output_dir, dpi, fmt, page_profiles)

    # Legacy single-DPI path
    paths = extract(pdf_path, output_dir, dpi=dpi, fmt=fmt)
    results = []
    for i, path in enumerate(paths, 1):
        with Image.open(path) as img:
            width, height = img.size
            is_blank = _is_mostly_blank(img, threshold=0.95)
            is_tiny = width < 100 or height < 100

        results.append(ImageResult(
            path=path,
            slide_num=i,
            is_blank=is_blank,
            is_tiny=is_tiny,
            width=width,
            height=height,
            render_dpi=dpi,
        ))
    return results


def _extract_per_page_dpi(
    pdf_path: Path,
    output_dir: Path,
    default_dpi: int,
    fmt: str,
    page_profiles: "dict[int, PageProfile]",
) -> list[ImageResult]:
    """Per-page DPI rendering: each page at its own DPI from PageProfile.render_dpi.

    Uses convert_from_path(first_page=n, last_page=n) for individual pages.
    Preserves atomic swap semantics and slide-001.png naming.
    """
    output_dir = Path(output_dir)
    slides_dir = output_dir / "slides"
    tmp_dir = output_dir / ".slides_tmp"
    old_dir = output_dir / ".slides_old"

    if not shutil.which("pdftoppm"):
        raise ImageExtractionError(
            "Poppler not found (pdftoppm). Install with: "
            "brew install poppler (macOS) or apt install poppler-utils (Linux)"
        )

    # Preflight recovery
    if old_dir.exists():
        if not slides_dir.exists():
            old_dir.rename(slides_dir)
            logger.warning("Recovered slides/ from interrupted swap: %s", old_dir)
        else:
            shutil.rmtree(old_dir)

    # Determine total page count using a fast single-page probe
    try:
        probe = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=72, fmt=fmt)
    except Exception as e:
        raise ImageExtractionError(f"Cannot probe PDF page count: {e}") from e

    # Get total page count from pdf2image
    from pdf2image.pdf2image import pdfinfo_from_path
    try:
        info = pdfinfo_from_path(str(pdf_path))
        total_pages = info.get("Pages", 0)
    except Exception:
        # Fallback: render all at low DPI to count
        all_images = convert_from_path(pdf_path, dpi=72, fmt=fmt)
        total_pages = len(all_images)

    if total_pages == 0:
        raise ImageExtractionError(f"No pages found in {pdf_path.name}")

    try:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)

        dpi_summary: dict[int, int] = {}
        results = []

        for page_num in range(1, total_pages + 1):
            # Determine DPI for this page
            profile = page_profiles.get(page_num)
            page_dpi = (profile.render_dpi if profile and profile.render_dpi else default_dpi)
            dpi_summary[page_dpi] = dpi_summary.get(page_dpi, 0) + 1

            # Render single page
            page_images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                dpi=page_dpi,
                fmt=fmt,
            )

            if len(page_images) != 1:
                raise ImageExtractionError(
                    f"Expected 1 image for page {page_num}, got {len(page_images)}"
                )

            image = page_images[0]
            filename = f"slide-{page_num:03d}.{fmt}"
            image_path = tmp_dir / filename
            image.save(str(image_path))

            # Validate
            _validate_image(image_path, image, slide_num=page_num)

            width, height = image.size
            is_blank = _is_mostly_blank(image, threshold=0.95)
            is_tiny = width < 100 or height < 100

            results.append(ImageResult(
                path=image_path,
                slide_num=page_num,
                is_blank=is_blank,
                is_tiny=is_tiny,
                width=width,
                height=height,
                render_dpi=page_dpi,
            ))

    except Exception as e:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        if isinstance(e, ImageExtractionError):
            raise
        raise ImageExtractionError(f"Per-page rendering failed: {e}") from e

    # Atomic swap
    try:
        if slides_dir.exists():
            slides_dir.rename(old_dir)
        try:
            tmp_dir.rename(slides_dir)
        except Exception:
            if old_dir.exists():
                old_dir.rename(slides_dir)
            raise
        finally:
            if old_dir.exists() and slides_dir.exists():
                shutil.rmtree(old_dir)
    except ImageExtractionError:
        raise
    except Exception as e:
        raise ImageExtractionError(f"Atomic swap failed: {e}") from e

    # Rewrite paths to final location
    for result in results:
        result.path = slides_dir / result.path.name

    # Log DPI summary
    for page_dpi, count in sorted(dpi_summary.items()):
        logger.info("  %d pages rendered at %d DPI", count, page_dpi)

    logger.info(
        "Extracted %d images from %s (per-page DPI)",
        len(results), pdf_path.name,
    )
    return results


def _validate_image(image_path: Path, image: Image.Image, slide_num: int) -> dict:
    """Validate image and return metadata. Warns on suspicious images."""
    size_bytes = image_path.stat().st_size
    width, height = image.size
    is_blank = False
    is_tiny = False

    if size_bytes == 0:
        logger.warning("Slide %d: image file is empty (0 bytes)", slide_num)
        return {"is_blank": False, "is_tiny": False, "width": 0, "height": 0}

    if width < 100 or height < 100:
        logger.warning("Slide %d: unusually small (%dx%d)", slide_num, width, height)
        is_tiny = True

    if _is_mostly_blank(image, threshold=0.95):
        logger.warning("Slide %d: appears mostly blank", slide_num)
        is_blank = True

    return {"is_blank": is_blank, "is_tiny": is_tiny, "width": width, "height": height}


def _is_mostly_blank(image: Image.Image, threshold: float = 0.95) -> bool:
    """Check if an image is mostly white/blank using histogram."""
    try:
        grayscale = image.convert("L")
        hist = grayscale.histogram()
        total = sum(hist)
        if total == 0:
            return False
        white_count = sum(hist[241:])  # pixels with value > 240
        return (white_count / total) > threshold
    except Exception:
        return False
