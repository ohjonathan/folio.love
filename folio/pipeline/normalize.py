"""Stage 1: Format normalization. PPTX → PDF via LibreOffice headless."""

import logging
import shutil
import subprocess
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


class NormalizationError(Exception):
    """Raised when format normalization fails."""


def to_pdf(source_path: Path, output_dir: Path, timeout: int = 60) -> Path:
    """Convert PPTX to PDF using LibreOffice headless.

    If source is already PDF, copies it to output_dir unchanged.

    Args:
        source_path: Path to PPTX or PDF file.
        output_dir: Directory for the output PDF.
        timeout: Max seconds for LibreOffice conversion.

    Returns:
        Path to the normalized PDF.

    Raises:
        NormalizationError: If conversion fails.
    """
    source_path = Path(source_path).resolve()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _validate_source(source_path)

    suffix = source_path.suffix.lower()

    if suffix == ".pdf":
        dest = output_dir / source_path.name
        shutil.copy2(source_path, dest)
        logger.info("Source is PDF, copied directly: %s", dest)
        return dest

    if suffix not in (".pptx", ".ppt"):
        raise NormalizationError(f"Unsupported format: {suffix}")

    # Check LibreOffice is available
    lo_path = _find_libreoffice()
    if lo_path is None:
        raise NormalizationError(
            "LibreOffice not found. Install with: "
            "brew install --cask libreoffice (macOS) or "
            "apt install libreoffice (Linux). "
            "If LibreOffice is blocked on a managed laptop, export the deck "
            "to PDF in PowerPoint and run folio convert <deck>.pdf instead."
        )

    effective_timeout = _compute_timeout(source_path, timeout)
    expected_pdf = output_dir / f"{source_path.stem}.pdf"

    try:
        result = subprocess.run(
            [
                lo_path,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(output_dir),
                str(source_path),
            ],
            capture_output=True,
            text=True,
            timeout=effective_timeout,
        )
    except subprocess.TimeoutExpired:
        if expected_pdf.exists():
            expected_pdf.unlink()
            logger.debug("Cleaned up partial PDF: %s", expected_pdf)
        raise NormalizationError(
            f"LibreOffice timed out after {effective_timeout}s converting {source_path.name}"
        )

    if result.returncode != 0:
        if expected_pdf.exists():
            expected_pdf.unlink()
            logger.debug("Cleaned up partial PDF: %s", expected_pdf)
        raise NormalizationError(
            f"LibreOffice conversion failed: {result.stderr.strip()}"
        )

    if result.stderr.strip():
        logger.warning(
            "LibreOffice stderr (non-fatal): %s", result.stderr.strip()[:500]
        )

    if not expected_pdf.exists():
        raise NormalizationError(
            f"LibreOffice completed but PDF not found at {expected_pdf}"
        )

    logger.info("Normalized to PDF: %s", expected_pdf)
    return expected_pdf


def _validate_source(source_path: Path) -> None:
    """Pre-flight validation before LibreOffice conversion."""
    # Note: existence check is included for standalone to_pdf() usage.
    # TOCTOU between exists() and stat() is acceptable for single-threaded pipeline.
    # If parallelism is added (Track B), consolidate into a single try/stat() call.
    if not source_path.exists():
        raise NormalizationError(f"Source not found: {source_path}")

    size = source_path.stat().st_size
    if size == 0:
        raise NormalizationError(
            f"Source file is empty (0 bytes): {source_path.name}"
        )
    if size > 500 * 1024 * 1024:
        size_mb = size / (1024 * 1024)
        raise NormalizationError(
            f"Source file too large ({size_mb:.0f} MB, max 500 MB): "
            f"{source_path.name}"
        )

    if source_path.suffix.lower() == ".pptx":
        if not zipfile.is_zipfile(source_path):
            raise NormalizationError(
                f"Invalid PPTX (not a ZIP archive): {source_path.name}"
            )
        try:
            with zipfile.ZipFile(source_path, "r") as zf:
                names = zf.namelist()
                if "EncryptedPackage" in names or "EncryptedInfo" in names:
                    raise NormalizationError(
                        f"Password-protected PPTX: {source_path.name}"
                    )
                if "[Content_Types].xml" not in names:
                    raise NormalizationError(
                        f"Malformed PPTX (missing [Content_Types].xml): "
                        f"{source_path.name}"
                    )
        except zipfile.BadZipFile:
            raise NormalizationError(
                f"Invalid PPTX (corrupt ZIP archive): {source_path.name}"
            )


def _compute_timeout(source_path: Path, base_timeout: int) -> int:
    """Scale timeout: base + 1s per MB, capped at 300s. Minimum 10s."""
    size_mb = source_path.stat().st_size / (1024 * 1024)
    scaled = max(base_timeout, 10) + int(size_mb)
    return min(scaled, 300)


def _find_libreoffice() -> str | None:
    """Find LibreOffice binary on the system."""
    # Common locations
    candidates = [
        "libreoffice",
        "soffice",
        "/usr/bin/libreoffice",
        "/usr/local/bin/libreoffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for candidate in candidates:
        if shutil.which(candidate):
            return candidate
    return None
