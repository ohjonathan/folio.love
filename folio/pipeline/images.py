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


# Stage 1: DPI backoff ladder for oversized pages
_DPI_LADDER = [300, 240, 200, 150, 120, 96]


def _estimate_page_pixels(
    crop_box: tuple[float, float, float, float],
    dpi: int,
) -> int:
    """Estimate rendered pixel count from PDF crop_box geometry and DPI.

    crop_box is in PDF points (1/72 inch). Converts to pixel dimensions
    at the given DPI and returns width * height.
    """
    width_pts = abs(crop_box[2] - crop_box[0])
    height_pts = abs(crop_box[3] - crop_box[1])
    scale = dpi / 72.0
    width_px = int(width_pts * scale)
    height_px = int(height_pts * scale)
    return width_px * height_px


def _find_safe_dpi(
    crop_box: tuple[float, float, float, float],
    intended_dpi: int,
    max_image_pixels: int | None = None,
) -> int:
    """Find the highest DPI from the ladder that fits under the pixel limit.

    Walks the ladder [300, 240, 200, 150, 120, 96] and returns the highest
    value ≤ intended_dpi whose estimated pixel count is under the limit.
    Uses Pillow's MAX_IMAGE_PIXELS as the default warning threshold.

    Raises ImageExtractionError if no DPI on the ladder fits.
    """
    limit = max_image_pixels if max_image_pixels is not None else Image.MAX_IMAGE_PIXELS
    if limit is None:  # Pillow safety check disabled
        return intended_dpi

    for candidate_dpi in _DPI_LADDER:
        if candidate_dpi > intended_dpi:
            continue
        pixels = _estimate_page_pixels(crop_box, candidate_dpi)
        if pixels <= limit:
            return candidate_dpi

    # Nothing on the ladder fits
    raise ImageExtractionError(
        f"Page too large for rendering: even at 96 DPI, estimated "
        f"{_estimate_page_pixels(crop_box, 96):,} pixels exceeds limit "
        f"{limit:,}. crop_box={crop_box}"
    )


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
    max_image_pixels: int | None = None,
) -> list[ImageResult]:
    """Extract slide images with blank/tiny/dimension metadata.

    When page_profiles is provided, renders each page individually at
    its PageProfile.render_dpi. Otherwise falls back to the single-DPI
    code path.

    Wraps extract() and annotates each result. Use this when the caller
    needs image quality metadata (e.g., converter blank-slide detection).
    """
    if page_profiles is not None:
        return _extract_per_page_dpi(
            pdf_path, output_dir, dpi, fmt, page_profiles, max_image_pixels,
        )

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
    max_image_pixels: int | None = None,
) -> list[ImageResult]:
    """Per-page DPI rendering: pages batched by DPI value.

    Groups pages sharing the same render_dpi into single
    convert_from_path calls, minimizing subprocess launches.
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

    # Derive page count from page_profiles when available (inspect_pages guarantees
    # one profile per page). Only fall back to pdfinfo when profiles are empty.
    if page_profiles:
        total_pages = max(page_profiles)
    else:
        from pdf2image.pdf2image import pdfinfo_from_path
        try:
            info = pdfinfo_from_path(str(pdf_path))
            total_pages = info.get("Pages", 0)
        except Exception:
            # Last resort: render all at minimum DPI
            all_images = convert_from_path(pdf_path, dpi=72, fmt=fmt)
            total_pages = len(all_images)
            del all_images  # Free immediately

    if total_pages == 0:
        raise ImageExtractionError(f"No pages found in {pdf_path.name}")

    # Group pages by DPI for batch rendering
    dpi_to_pages: dict[int, list[int]] = {}
    for page_num in range(1, total_pages + 1):
        profile = page_profiles.get(page_num)
        page_dpi = (profile.render_dpi if profile and profile.render_dpi else default_dpi)

        # Stage 1: DPI backoff for oversized pages
        if profile and profile.crop_box:
            safe_dpi = _find_safe_dpi(
                profile.crop_box, page_dpi, max_image_pixels,
            )
            if safe_dpi != page_dpi:
                est_pixels = _estimate_page_pixels(profile.crop_box, page_dpi)
                safe_pixels = _estimate_page_pixels(profile.crop_box, safe_dpi)
                logger.warning(
                    "Page %d: intended DPI %d would produce %s pixels "
                    "(limit %s); backing off to %d DPI (%s pixels)",
                    page_num, page_dpi, f"{est_pixels:,}",
                    f"{max_image_pixels or Image.MAX_IMAGE_PIXELS:,}",
                    safe_dpi, f"{safe_pixels:,}",
                )
                page_dpi = safe_dpi

        dpi_to_pages.setdefault(page_dpi, []).append(page_num)

    try:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)

        # Render batches: save-and-release per batch to limit memory
        results = []

        for batch_dpi, page_nums in sorted(dpi_to_pages.items()):
            # Find contiguous runs to minimize subprocess calls
            for run_start, run_end in _contiguous_runs(page_nums):
                batch = convert_from_path(
                    pdf_path,
                    first_page=run_start,
                    last_page=run_end,
                    dpi=batch_dpi,
                    fmt=fmt,
                )
                expected = run_end - run_start + 1
                if len(batch) != expected:
                    raise ImageExtractionError(
                        f"Expected {expected} images for pages {run_start}-{run_end}, "
                        f"got {len(batch)}"
                    )
                # Save each image immediately and release PIL object
                for i, img in enumerate(batch):
                    page_num = run_start + i
                    profile = page_profiles.get(page_num)
                    page_dpi_val = (profile.render_dpi if profile and profile.render_dpi else default_dpi)

                    filename = f"slide-{page_num:03d}.{fmt}"
                    image_path = tmp_dir / filename
                    img.save(str(image_path))

                    _validate_image(image_path, img, slide_num=page_num)

                    width, height = img.size
                    is_blank = _is_mostly_blank(img, threshold=0.95)
                    is_tiny = width < 100 or height < 100

                    results.append(ImageResult(
                        path=image_path,
                        slide_num=page_num,
                        is_blank=is_blank,
                        is_tiny=is_tiny,
                        width=width,
                        height=height,
                        render_dpi=page_dpi_val,
                    ))
                    img.close()  # Release PIL memory

                del batch  # Free batch list

            logger.info("  Rendered %d pages at %d DPI", len(page_nums), batch_dpi)

        # Sort results by page number (batches may be interleaved)
        results.sort(key=lambda r: r.slide_num)

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

    logger.info(
        "Extracted %d images from %s (per-page DPI, %d batches)",
        len(results), pdf_path.name, len(dpi_to_pages),
    )
    return results


def _contiguous_runs(pages: list[int]) -> list[tuple[int, int]]:
    """Group sorted page numbers into contiguous (start, end) runs.

    Example: [1, 2, 3, 7, 8] → [(1, 3), (7, 8)]
    """
    if not pages:
        return []
    sorted_pages = sorted(pages)
    runs = []
    start = sorted_pages[0]
    prev = start
    for p in sorted_pages[1:]:
        if p == prev + 1:
            prev = p
        else:
            runs.append((start, prev))
            start = p
            prev = p
    runs.append((start, prev))
    return runs


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

