"""Stage 3: Text extraction. Extract verbatim text per slide using MarkItDown."""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class TextExtractionError(Exception):
    """Raised when text extraction fails."""


def extract(source_path: Path) -> dict[int, str]:
    """Extract text from PPTX/PDF with per-slide boundaries.

    Args:
        source_path: Path to the original source file (PPTX preferred).

    Returns:
        Dict mapping slide number (1-indexed) to extracted text.
        Empty dict if extraction fails completely (logged as warning).
    """
    source_path = Path(source_path)
    suffix = source_path.suffix.lower()

    if suffix in (".pptx", ".ppt"):
        return _extract_pptx(source_path)
    elif suffix == ".pdf":
        return _extract_pdf(source_path)
    else:
        logger.warning("Text extraction not supported for %s", suffix)
        return {}


def _extract_pptx(source_path: Path) -> dict[int, str]:
    """Extract text from PPTX using MarkItDown."""
    try:
        from markitdown import MarkItDown
    except ImportError:
        raise TextExtractionError(
            "markitdown not installed. Run: pip install markitdown"
        )

    try:
        md = MarkItDown()
        result = md.convert(str(source_path))
        raw_text = result.text_content
    except Exception as e:
        logger.warning("MarkItDown extraction failed for %s: %s", source_path.name, e)
        return {}

    slides = _parse_slide_boundaries(raw_text)

    if not slides:
        # Fallback: treat entire text as slide 1
        logger.warning(
            "No slide boundaries detected in %s. Treating as single block.",
            source_path.name,
        )
        if raw_text.strip():
            return {1: raw_text.strip()}
        return {}

    logger.info("Extracted text for %d slides from %s", len(slides), source_path.name)
    return slides


def _extract_pdf(source_path: Path) -> dict[int, str]:
    """Extract text from PDF. Less reliable slide boundaries than PPTX."""
    try:
        import pdfplumber
    except ImportError:
        logger.warning(
            "pdfplumber not installed. PDF text extraction unavailable. "
            "Run: pip install pdfplumber"
        )
        return {}

    try:
        slides = {}
        with pdfplumber.open(str(source_path)) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    slides[i] = text.strip()
        logger.info("Extracted text for %d pages from %s", len(slides), source_path.name)
        return slides
    except Exception as e:
        logger.warning("PDF text extraction failed for %s: %s", source_path.name, e)
        return {}


def _parse_slide_boundaries(raw_text: str) -> dict[int, str]:
    """Parse MarkItDown output into per-slide text blocks.

    MarkItDown typically marks slide boundaries with HTML comments
    like <!-- Slide X --> or with markdown headers like ## Slide X.
    This parser handles both patterns.
    """
    slides = {}

    # Pattern 1: HTML comments (<!-- Slide number: N --> or <!-- Slide N -->)
    comment_pattern = re.compile(
        r"<!--\s*Slide\s*(?:number:\s*)?(\d+)\s*-->", re.IGNORECASE
    )
    # Pattern 2: Markdown headers (## Slide N or # Slide N)
    header_pattern = re.compile(r"^#{1,3}\s+Slide\s+(\d+)", re.IGNORECASE | re.MULTILINE)

    # Try comment-based splitting first
    comment_matches = list(comment_pattern.finditer(raw_text))
    if comment_matches:
        return _split_by_matches(raw_text, comment_matches)

    # Try header-based splitting
    header_matches = list(header_pattern.finditer(raw_text))
    if header_matches:
        return _split_by_matches(raw_text, header_matches)

    # Pattern 3: Numbered sections that look like slide content
    # MarkItDown sometimes uses "1\n\nContent..." format
    section_pattern = re.compile(r"^(\d+)\s*$", re.MULTILINE)
    section_matches = list(section_pattern.finditer(raw_text))
    if len(section_matches) >= 2:
        return _split_by_matches(raw_text, section_matches)

    return {}


def _split_by_matches(raw_text: str, matches: list) -> dict[int, str]:
    """Split text into slides based on regex matches."""
    slides = {}
    for i, match in enumerate(matches):
        slide_num = int(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        text = raw_text[start:end].strip()
        # Clean up any remaining HTML comments
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()
        if text:
            slides[slide_num] = text
    return slides
