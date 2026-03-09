"""Stage 1: Format normalization. PPTX -> PDF via LibreOffice or PowerPoint."""

import logging
import re
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Fixed staging directory for PowerPoint PDF export.  PowerPoint's macOS App
# Sandbox triggers a "Grant File Access" dialog per *directory*.  Using a single
# fixed location means at most one dialog for the entire batch session.
# ~/Documents/ is typically sandbox-exempt for Office apps.
_PPT_STAGING = Path.home() / "Documents" / ".folio_pdf_staging"


class NormalizationError(Exception):
    """Raised when format normalization fails.

    Attributes:
        renderer_used: The renderer that was active when the error occurred.
            Set by ``to_pdf()`` before the error propagates to callers.
    """
    renderer_used: str = "unknown"


@dataclass
class NormalizationResult:
    """Result of a normalization operation."""
    pdf_path: Path
    renderer_used: str  # "libreoffice", "powerpoint", "pdf-copy"


def to_pdf(
    source_path: Path,
    output_dir: Path,
    *,
    pptx_output_dir: Path | None = None,
    timeout: int = 60,
    renderer: str = "auto",
) -> Path:
    """Convert PPTX to PDF using LibreOffice or PowerPoint.

    If source is already PDF, copies it to output_dir unchanged.

    Args:
        source_path: Path to PPTX or PDF file.
        output_dir: Directory for the output PDF.
        pptx_output_dir: Optional override staging dir for PowerPoint renderer.
            Defaults to ~/Documents/.folio_pdf_staging/ to avoid per-file
            macOS sandbox dialogs.  The PDF is moved to output_dir after
            export.  LibreOffice and PDF-copy paths are unaffected.
        timeout: Max seconds for conversion.
        renderer: Renderer preference: "auto", "libreoffice", or "powerpoint".

    Returns:
        NormalizationResult with pdf_path and renderer_used.

    Raises:
        NormalizationError: If conversion fails.
    """
    source_path = Path(source_path).resolve()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if pptx_output_dir is not None:
        pptx_output_dir = Path(pptx_output_dir)

    _validate_source(source_path)

    suffix = source_path.suffix.lower()

    if suffix == ".pdf":
        dest = output_dir / source_path.name
        shutil.copy2(source_path, dest)
        logger.info("Source is PDF, copied directly: %s", dest)
        _warn_portrait_pdf(dest)
        return NormalizationResult(pdf_path=dest, renderer_used="pdf-copy")

    if suffix not in (".pptx", ".ppt"):
        raise NormalizationError(f"Unsupported format: {suffix}")

    renderer_name, renderer_path = _select_renderer(renderer)
    effective_timeout = _compute_timeout(source_path, timeout)

    ppt_dir = pptx_output_dir if pptx_output_dir is not None else _PPT_STAGING
    ppt_dir.mkdir(parents=True, exist_ok=True)
    lo_pdf = output_dir / f"{source_path.stem}.pdf"
    ppt_pdf = ppt_dir / f"{source_path.stem}.pdf"

    # Track which path and renderer were actually used.
    actual_pdf: Path
    actual_renderer: str

    if renderer_name == "libreoffice":
        actual_pdf = lo_pdf
        actual_renderer = "libreoffice"
        try:
            _convert_with_libreoffice(
                renderer_path, source_path, output_dir, effective_timeout, lo_pdf
            )
        except NormalizationError as lo_err:
            if renderer != "auto" or not _find_powerpoint():
                lo_err.renderer_used = "libreoffice"
                raise
            # LO found on disk but failed (e.g. MDM launch-blocked).
            # Fall back to PowerPoint in auto mode.
            logger.warning(
                "LibreOffice found but conversion failed; "
                "falling back to PowerPoint renderer"
            )
            actual_pdf = ppt_pdf
            actual_renderer = "powerpoint"
            try:
                _convert_with_powerpoint(
                    source_path, effective_timeout, ppt_pdf
                )
            except NormalizationError as ppt_err:
                ppt_err.renderer_used = "powerpoint"
                raise
    elif renderer_name == "powerpoint":
        actual_pdf = ppt_pdf
        actual_renderer = "powerpoint"
        try:
            _convert_with_powerpoint(
                source_path, effective_timeout, ppt_pdf
            )
        except NormalizationError as ppt_err:
            ppt_err.renderer_used = "powerpoint"
            raise
    else:
        # Defensive fallback: _select_renderer() currently only returns
        # "libreoffice" or "powerpoint", so this branch is unreachable.
        # Kept as a safety net for future renderer additions.
        actual_pdf = lo_pdf
        actual_renderer = "libreoffice"

    if not actual_pdf.exists():
        raise NormalizationError(
            f"Conversion completed but PDF not found at {actual_pdf}"
        )

    # PowerPoint writes the PDF to a staging directory to avoid sandbox
    # dialogs.  Move it into the output directory for downstream stages.
    if actual_renderer == "powerpoint" and actual_pdf.parent != output_dir:
        dest = output_dir / actual_pdf.name
        shutil.move(str(actual_pdf), str(dest))
        actual_pdf = dest
        logger.debug("Moved PowerPoint PDF to output dir: %s", dest)

    logger.info("Normalized to PDF via %s: %s", actual_renderer, actual_pdf)
    return NormalizationResult(pdf_path=actual_pdf, renderer_used=actual_renderer)


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
    """Escape a string for safe embedding in an AppleScript double-quoted literal.

    Handles backslashes, double quotes, and control characters that AppleScript
    interprets inside quoted strings.
    """
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\r", "\\r")
    s = s.replace("\n", "\\n")
    s = s.replace("\t", "\\t")
    s = s.replace("\0", "")
    return s


def _build_powerpoint_export_applescript(
    output_posix: str, timeout: int, source_name: str
) -> str:
    """Build AppleScript to save an already-open presentation as PDF.

    The file is opened via Launch Services (`open -a`), not AppleScript's
    `open POSIX file`, which avoids the -9074 errors observed with 17
    specific PPTX files.

    Uses the presentation name for save/close to avoid races with other
    open presentations.
    """
    safe_output = _escape_applescript_string(output_posix)
    safe_name = _escape_applescript_string(source_name)
    return (
        'tell application "Microsoft PowerPoint"\n'
        f"    with timeout of {timeout} seconds\n"
        f'        save presentation "{safe_name}" in POSIX file "{safe_output}" as save as PDF\n'
        f'        close presentation "{safe_name}" saving no\n'
        "    end timeout\n"
        "end tell"
    )


def _wait_for_presentation(source_name: str, timeout: int) -> None:
    """Wait for PowerPoint to register a presentation opened via Launch Services.

    Polls up to `timeout` seconds for the presentation name to appear in
    PowerPoint's presentation list.
    """
    safe_name = _escape_applescript_string(source_name)
    check_script = (
        'tell application "Microsoft PowerPoint"\n'
        f'    return name of presentation "{safe_name}"\n'
        'end tell'
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = subprocess.run(
                ["osascript", "-e", check_script],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and source_name in result.stdout:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise NormalizationError(
        f"PowerPoint did not open {source_name} within {timeout}s"
    )


def _convert_with_powerpoint(
    source_path: Path,
    timeout: int,
    expected_pdf: Path,
) -> None:
    """Convert PPTX to PDF using PowerPoint.

    Two-step approach:
      1. Open the file via Launch Services (``open -a``), which avoids the
         AppleScript ``open POSIX file`` interface that triggers -9074 on
         certain PPTX files.
      2. Export to PDF + close via AppleScript (save/close still work fine
         on all tested files).
    """
    # Step 1: Open via Launch Services.
    try:
        subprocess.run(
            ["open", "-a", "Microsoft PowerPoint", str(source_path)],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise NormalizationError(
            f"Launch Services timed out opening {source_path.name}"
        )

    # Wait for PowerPoint to register the presentation.
    try:
        _wait_for_presentation(source_path.name, timeout)
    except NormalizationError:
        # Best-effort cleanup if the file never appeared.
        _best_effort_close(source_path.name)
        raise

    # Step 2: Export via AppleScript (no `open POSIX file`).
    script = _build_powerpoint_export_applescript(
        str(expected_pdf), timeout, source_path.name
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
        _best_effort_close(source_path.name)
        raise NormalizationError(
            f"PowerPoint timed out after {timeout}s converting {source_path.name}"
        )

    if result.returncode != 0:
        if expected_pdf.exists():
            expected_pdf.unlink()
            logger.debug("Cleaned up partial PDF: %s", expected_pdf)
        stderr = result.stderr.strip()
        hint = (
            "\n\nIf this file consistently fails, export it to PDF manually "
            "(File → Export → PDF, slides only) and run: folio convert <deck>.pdf"
        )
        _best_effort_close(source_path.name)
        raise NormalizationError(
            f"PowerPoint conversion failed: {stderr}{hint}"
        )

    if result.stderr.strip():
        logger.warning(
            "PowerPoint stderr (non-fatal): %s", result.stderr.strip()[:500]
        )


def _best_effort_close(source_name: str) -> None:
    """Best-effort close of a specific presentation."""
    safe_name = _escape_applescript_string(source_name)
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


def _warn_portrait_pdf(pdf_path: Path) -> None:
    """Warn if the PDF appears to be portrait (likely notes-page export).

    Uses a lightweight heuristic: reads the first /MediaBox in the first
    8 KB of the file to check width vs height.  This does NOT reject the PDF.

    Limitation: For compressed or encrypted PDFs the /MediaBox may not
    appear in the first 8 KB, resulting in a false negative.  This is
    acceptable under the L3 (non-critical heuristic) policy.
    """
    try:
        with open(pdf_path, "rb") as f:
            raw = f.read(8192)  # first 8 KB is enough for page 1
        text_chunk = raw.decode("latin-1", errors="replace")
        match = re.search(r"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", text_chunk)
        if match:
            x0, y0, x1, y1 = (float(v) for v in match.groups())
            width = x1 - x0
            height = y1 - y0
            if width > 0 and height > width:
                logger.warning(
                    "Portrait PDF detected (%s): this may be a notes-page export. "
                    "For best results, re-export as slides only (landscape).",
                    pdf_path.name,
                )
    except Exception:
        pass  # Non-critical heuristic; never block on failure

