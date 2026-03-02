"""Stage 1: Format normalization. PPTX → PDF via LibreOffice headless."""

import logging
import shutil
import subprocess
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
            "apt install libreoffice (Linux)"
        )

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
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise NormalizationError(
            f"LibreOffice timed out after {timeout}s converting {source_path.name}"
        )

    if result.returncode != 0:
        raise NormalizationError(
            f"LibreOffice conversion failed: {result.stderr.strip()}"
        )

    expected_pdf = output_dir / f"{source_path.stem}.pdf"
    if not expected_pdf.exists():
        raise NormalizationError(
            f"LibreOffice completed but PDF not found at {expected_pdf}"
        )

    logger.info("Normalized to PDF: %s", expected_pdf)
    return expected_pdf


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
