"""Stage 1: Format normalization. PPTX -> PDF via LibreOffice or PowerPoint."""

import logging
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


class NormalizationError(Exception):
    """Raised when format normalization fails."""


def to_pdf(
    source_path: Path, output_dir: Path, timeout: int = 60, renderer: str = "auto"
) -> Path:
    """Convert PPTX to PDF using LibreOffice or PowerPoint.

    If source is already PDF, copies it to output_dir unchanged.

    Args:
        source_path: Path to PPTX or PDF file.
        output_dir: Directory for the output PDF.
        timeout: Max seconds for conversion.
        renderer: Renderer preference: "auto", "libreoffice", or "powerpoint".

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

    renderer_name, renderer_path = _select_renderer(renderer)
    effective_timeout = _compute_timeout(source_path, timeout)
    expected_pdf = output_dir / f"{source_path.stem}.pdf"

    if renderer_name == "libreoffice":
        try:
            _convert_with_libreoffice(
                renderer_path, source_path, output_dir, effective_timeout, expected_pdf
            )
        except NormalizationError:
            if renderer != "auto" or not _find_powerpoint():
                raise
            # LO found on disk but failed (e.g. MDM launch-blocked).
            # Fall back to PowerPoint in auto mode.
            logger.warning(
                "LibreOffice found but conversion failed; "
                "falling back to PowerPoint renderer"
            )
            _convert_with_powerpoint(
                source_path, output_dir, effective_timeout, expected_pdf
            )
    elif renderer_name == "powerpoint":
        _convert_with_powerpoint(
            source_path, output_dir, effective_timeout, expected_pdf
        )

    if not expected_pdf.exists():
        raise NormalizationError(
            f"Conversion completed but PDF not found at {expected_pdf}"
        )

    logger.info("Normalized to PDF: %s", expected_pdf)
    return expected_pdf


def _select_renderer(preference: str = "auto") -> tuple[str, str | None]:
    """Select a PPTX-to-PDF renderer based on preference and availability.

    Returns:
        ("libreoffice", "/path/to/soffice") or ("powerpoint", None).

    Raises:
        NormalizationError: If no renderer is available.
    """
    if preference == "libreoffice":
        lo_path = _find_libreoffice()
        if lo_path is None:
            raise NormalizationError(
                "LibreOffice not found. Install with: "
                "brew install --cask libreoffice (macOS) or "
                "apt install libreoffice (Linux)."
            )
        return ("libreoffice", lo_path)

    if preference == "powerpoint":
        if not _find_powerpoint():
            raise NormalizationError(
                "Microsoft PowerPoint not found at "
                "/Applications/Microsoft PowerPoint.app. "
                "PowerPoint renderer is only available on macOS."
            )
        return ("powerpoint", None)

    # auto: prefer LibreOffice (headless, CI-friendly), fall back to PowerPoint
    lo_path = _find_libreoffice()
    if lo_path is not None:
        return ("libreoffice", lo_path)

    if _find_powerpoint():
        logger.info("LibreOffice not found; falling back to PowerPoint renderer")
        return ("powerpoint", None)

    raise NormalizationError(
        "No PPTX renderer available. Options:\n"
        "  1. Install LibreOffice: brew install --cask libreoffice (macOS) "
        "or apt install libreoffice (Linux)\n"
        "  2. Use PowerPoint on macOS (auto-detected if installed)\n"
        "  3. Export to PDF manually and run: folio convert <deck>.pdf"
    )


def _find_powerpoint() -> bool:
    """Check whether Microsoft PowerPoint is installed (macOS only)."""
    if sys.platform != "darwin":
        return False
    return Path("/Applications/Microsoft PowerPoint.app").exists()


def _find_libreoffice() -> str | None:
    """Find LibreOffice binary on the system."""
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


def _convert_with_libreoffice(
    lo_path: str,
    source_path: Path,
    output_dir: Path,
    timeout: int,
    expected_pdf: Path,
) -> None:
    """Convert PPTX to PDF using LibreOffice headless."""
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
        if expected_pdf.exists():
            expected_pdf.unlink()
            logger.debug("Cleaned up partial PDF: %s", expected_pdf)
        raise NormalizationError(
            f"LibreOffice timed out after {timeout}s converting {source_path.name}"
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


def _escape_applescript_string(s: str) -> str:
    """Escape a string for safe embedding in an AppleScript double-quoted literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _build_powerpoint_applescript(
    source_posix: str, output_posix: str, timeout: int
) -> str:
    """Build AppleScript to convert a PPTX to PDF via PowerPoint."""
    safe_source = _escape_applescript_string(source_posix)
    safe_output = _escape_applescript_string(output_posix)
    return (
        'tell application "Microsoft PowerPoint"\n'
        "    launch\n"
        f"    with timeout of {timeout} seconds\n"
        f'        open POSIX file "{safe_source}"\n'
        f'        save active presentation in POSIX file "{safe_output}" as save as PDF\n'
        "        close active presentation saving no\n"
        "    end timeout\n"
        "end tell"
    )


def _convert_with_powerpoint(
    source_path: Path,
    output_dir: Path,
    timeout: int,
    expected_pdf: Path,
) -> None:
    """Convert PPTX to PDF using PowerPoint via AppleScript."""
    script = _build_powerpoint_applescript(
        str(source_path), str(expected_pdf), timeout
    )

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout + 10,
        )
    except subprocess.TimeoutExpired:
        if expected_pdf.exists():
            expected_pdf.unlink()
            logger.debug("Cleaned up partial PDF: %s", expected_pdf)
        # Best-effort: close the specific presentation we opened, not whatever
        # happens to be active (which could be unrelated user work).
        safe_name = _escape_applescript_string(source_path.name)
        try:
            subprocess.run(
                [
                    "osascript", "-e",
                    'tell application "Microsoft PowerPoint" to '
                    f'close presentation "{safe_name}" saving no',
                ],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass
        raise NormalizationError(
            f"PowerPoint timed out after {timeout}s converting {source_path.name}"
        )

    if result.returncode != 0:
        if expected_pdf.exists():
            expected_pdf.unlink()
            logger.debug("Cleaned up partial PDF: %s", expected_pdf)
        raise NormalizationError(
            f"PowerPoint conversion failed: {result.stderr.strip()}"
        )

    if result.stderr.strip():
        logger.warning(
            "PowerPoint stderr (non-fatal): %s", result.stderr.strip()[:500]
        )


def _validate_source(source_path: Path) -> None:
    """Pre-flight validation before conversion."""
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
