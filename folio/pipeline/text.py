"""Stage 3: Text extraction. Extract verbatim text per slide using MarkItDown."""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


class TextExtractionError(Exception):
    """Raised when text extraction fails."""


_EXTRACTION_VERSION = "0.1.0"
# TODO(Track B): Wire into cache invalidation before v1.0


@dataclass(frozen=True)
class SlideText:
    """Structured text extracted from a single slide."""
    slide_num: int
    full_text: str
    elements: list[dict] = field(default_factory=list)
    is_empty: bool = False
    # Each element: {"type": "title"|"body"|"note"|"table", "text": "..."}


@dataclass
class ReconciliationResult:
    """Result of reconciling text count with authoritative image count."""
    slide_texts: dict[int, SlideText]
    was_reconciled: bool
    action: str  # "none" | "padded" | "truncated"
    gaps_filled: int  # count of empty entries inserted for missing keys within range
    original_text_count: int
    image_count: int
    alignment_confidence: float  # min(text, image) / max(text, image); 1.0 = exact


def _detect_elements(text: str) -> list[dict]:
    """Detect element types from extracted slide text.

    Heuristic:
    - First H1/H2 markdown line → title
    - Everything else → body
    - Speaker notes (prefixed with "Notes:" or similar) → note
    """
    elements = []
    lines = text.split("\n")
    title_found = False
    body_lines = []
    note_lines = []
    in_notes = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_notes:
                note_lines.append("")
            else:
                body_lines.append("")
            continue

        # Detect speaker notes section
        if re.match(r"^(?:Notes?|Speaker\s+Notes?)\s*:", stripped, re.IGNORECASE):
            in_notes = True
            remainder = re.sub(r"^(?:Notes?|Speaker\s+Notes?)\s*:\s*", "", stripped, flags=re.IGNORECASE)
            if remainder:
                note_lines.append(remainder)
            continue

        if in_notes:
            note_lines.append(stripped)
            continue

        # Detect title (first H1/H2 line)
        if not title_found and re.match(r"^#{1,2}\s+", stripped):
            title_text = re.sub(r"^#{1,2}\s+", "", stripped)
            elements.append({"type": "title", "text": title_text})
            title_found = True
            continue

        # Detect title from bold-only first line
        if not title_found and re.match(r"^\*\*[^*]+\*\*$", stripped):
            title_text = stripped.strip("*")
            elements.append({"type": "title", "text": title_text})
            title_found = True
            continue

        body_lines.append(stripped)

    # Consolidate body
    body_text = "\n".join(body_lines).strip()
    if body_text:
        elements.append({"type": "body", "text": body_text})

    # Consolidate notes
    note_text = "\n".join(note_lines).strip()
    if note_text:
        elements.append({"type": "note", "text": note_text})

    # Detect tables: lines with consistent pipe (|) or tab delimiters
    if body_text and _looks_like_table(body_text):
        for elem in elements:
            if elem["type"] == "body":
                elem["type"] = "table"
                break

    return elements


def _looks_like_table(text: str) -> bool:
    """Heuristic: text looks like a table if 3+ lines have consistent pipe delimiters."""
    if not text:
        return False
    lines = [l for l in text.split("\n") if l.strip()]
    if not lines:
        return False
    pipe_lines = [l for l in lines if l.count("|") >= 2]
    return len(pipe_lines) >= 3 and len(pipe_lines) / len(lines) > 0.5


def extract(source_path: Path) -> dict[int, str]:
    """Extract text from PPTX/PDF with per-slide boundaries.

    Backward-compatible wrapper that returns plain strings.

    Args:
        source_path: Path to the original source file (PPTX preferred).

    Returns:
        Dict mapping slide number (1-indexed) to plain text string.
        Empty dict if extraction fails completely (logged as warning).
    """
    return {num: st.full_text for num, st in extract_structured(source_path).items()}


def extract_structured(source_path: Path) -> dict[int, "SlideText"]:
    """Extract text from PPTX/PDF with per-slide boundaries.

    Args:
        source_path: Path to the original source file (PPTX preferred).

    Returns:
        Dict mapping slide number (1-indexed) to SlideText.
        Empty dict if extraction fails completely (logged as warning).
    """
    source_path = Path(source_path)
    suffix = source_path.suffix.lower()

    try:
        if suffix in (".pptx", ".ppt"):
            return _extract_pptx(source_path)
        elif suffix == ".pdf":
            return _extract_pdf(source_path)
        else:
            logger.warning("Text extraction not supported for %s", suffix)
            return {}
    except TextExtractionError as e:
        logger.warning("Text extraction failed (L2 fallback): %s", e)
        return {}


def _extract_pptx(source_path: Path) -> dict[int, "SlideText"]:
    """Extract text from PPTX using MarkItDown.

    Raises TextExtractionError on unexpected failures (L1). The caller
    (extract_structured) catches these at L2 and falls back to {}.
    """
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
    except TextExtractionError:
        raise
    except Exception as e:
        raise TextExtractionError(
            f"MarkItDown extraction failed for {source_path.name}: {e}"
        ) from e

    raw_slides = _parse_slide_boundaries(raw_text)

    if not raw_slides:
        # Fallback: treat entire text as slide 1
        logger.warning(
            "No slide boundaries detected in %s. Treating as single block.",
            source_path.name,
        )
        if raw_text.strip():
            text = raw_text.strip()
            return {1: SlideText(
                slide_num=1,
                full_text=text,
                elements=_detect_elements(text),
            )}
        return {}

    slides = {}
    for slide_num, text in raw_slides.items():
        slides[slide_num] = SlideText(
            slide_num=slide_num,
            full_text=text,
            elements=_detect_elements(text),
        )

    logger.info("Extracted text for %d slides from %s", len(slides), source_path.name)
    return slides


def _extract_pdf(pdf_path: Path) -> dict[int, "SlideText"]:
    """Extract per-page structured text from PDF using pdfplumber.

    Returns dict of SlideText keyed by 1-based page number. Empty pages are
    omitted from the result (legitimate gaps, not errors).

    Raises TextExtractionError on unexpected failures (L1). The caller
    (extract_structured) catches these at L2 and falls back to {}.
    """
    try:
        import pdfplumber
    except ImportError:
        raise TextExtractionError(
            "pdfplumber is required for PDF text extraction. "
            "Install with: pip install pdfplumber"
        )

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            slides = {}
            for i, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text = page_text.strip()
                    slides[i] = SlideText(
                        slide_num=i,
                        full_text=text,
                        elements=_detect_elements(text),
                    )
            return slides
    except TextExtractionError:
        raise
    except Exception as e:
        raise TextExtractionError(
            f"PDF text extraction failed for {pdf_path.name}: {e}"
        ) from e


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

    # Pattern 2.5: Horizontal rules (--- or ===) as slide separators
    # Some MarkItDown versions use these between slides
    # Strip leading YAML frontmatter block before HR splitting
    text_for_hr = raw_text
    if text_for_hr.startswith("---"):
        frontmatter_end = text_for_hr.find("---", 3)
        if frontmatter_end != -1:
            text_for_hr = text_for_hr[frontmatter_end + 3:]
    hr_pattern = re.compile(r"^-{3,}$|^={3,}$", re.MULTILINE)
    hr_matches = list(hr_pattern.finditer(text_for_hr))
    if len(hr_matches) >= 2:
        # Guard: require minimum content between HRs to avoid false positives
        has_content_between = False
        for j in range(len(hr_matches) - 1):
            between = text_for_hr[hr_matches[j].end():hr_matches[j + 1].start()].strip()
            if len(between) > 10:
                has_content_between = True
                break
        if has_content_between:
            return _split_by_hr(text_for_hr, hr_matches)

    # Pattern 3: Numbered sections starting from 1 with sequential numbering
    section_pattern = re.compile(r"^(\d+)\s*$", re.MULTILINE)
    section_matches = list(section_pattern.finditer(raw_text))
    if len(section_matches) >= 2:
        # Validate sequential numbering from 1
        numbers = [int(m.group(1)) for m in section_matches]
        if numbers[0] == 1 and numbers == list(range(1, len(numbers) + 1)):
            return _split_by_matches(raw_text, section_matches)

    return {}


def _split_by_hr(raw_text: str, hr_matches: list) -> dict[int, str]:
    """Split text into slides using horizontal rules as boundaries."""
    slides = {}
    slide_num = 1

    # Text before first HR
    first_text = raw_text[:hr_matches[0].start()].strip()
    if first_text:
        slides[slide_num] = first_text
        slide_num += 1

    # Text between HRs
    for i, match in enumerate(hr_matches):
        start = match.end()
        end = hr_matches[i + 1].start() if i + 1 < len(hr_matches) else len(raw_text)
        text = raw_text[start:end].strip()
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()
        if text:
            slides[slide_num] = text
            slide_num += 1

    return slides


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


def reconcile_slide_count(
    slide_texts: dict[int, SlideText],
    image_count: int,
) -> ReconciliationResult:
    """Pad or truncate slide text dict to match authoritative image count.

    Image count (from PDF page count) is authoritative. Text extraction
    may produce fewer slides (missed boundaries) or more (false boundaries).

    Keys are NEVER remapped — they preserve page/slide positional identity.
    Gaps within the existing key range are filled with empty SlideText entries.

    Returns:
        ReconciliationResult with reconciled slide_texts and metadata.
        Consumers should check alignment_confidence to assess trust.
    """
    # B2 fix: copy input to avoid mutating caller's dict
    slide_texts = dict(slide_texts)

    if not slide_texts:
        # No text at all — return empty placeholders
        return ReconciliationResult(
            slide_texts={
                i: SlideText(slide_num=i, full_text="", is_empty=True)
                for i in range(1, image_count + 1)
            },
            was_reconciled=True,
            action="padded",
            gaps_filled=0,
            original_text_count=0,
            image_count=image_count,
            alignment_confidence=0.0,
        )

    original_text_count = len(slide_texts)

    # Step 1: Fill gaps within existing key range with empties
    max_existing_key = max(slide_texts.keys())
    gaps_filled = 0
    for i in range(1, max_existing_key + 1):
        if i not in slide_texts:
            slide_texts[i] = SlideText(slide_num=i, full_text="", is_empty=True)
            gaps_filled += 1

    if gaps_filled:
        logger.info(
            "Filled %d gaps in text keys (range 1..%d)",
            gaps_filled, max_existing_key,
        )

    # Step 2: Pad or truncate to match image count
    text_count = len(slide_texts)
    confidence = (
        min(original_text_count, image_count) / max(original_text_count, image_count)
        if image_count > 0 else 0.0
    )

    if text_count == image_count:
        return ReconciliationResult(
            slide_texts=dict(slide_texts),
            was_reconciled=gaps_filled > 0,
            action="none",
            gaps_filled=gaps_filled,
            original_text_count=original_text_count,
            image_count=image_count,
            alignment_confidence=confidence,
        )

    if text_count > image_count:
        logger.warning(
            "Text extraction found %d slides but only %d images. "
            "Truncating text to match image count.",
            text_count, image_count,
        )
        return ReconciliationResult(
            slide_texts={
                k: v for k, v in slide_texts.items() if k <= image_count
            },
            was_reconciled=True,
            action="truncated",
            gaps_filled=gaps_filled,
            original_text_count=original_text_count,
            image_count=image_count,
            alignment_confidence=confidence,
        )

    # text_count < image_count — pad missing slides
    logger.warning(
        "Text extraction found %d slides but %d images. "
        "Padding %d missing slides with empty text.",
        text_count, image_count, image_count - text_count,
    )
    result = dict(slide_texts)
    for i in range(1, image_count + 1):
        if i not in result:
            result[i] = SlideText(slide_num=i, full_text="", is_empty=True)
    return ReconciliationResult(
        slide_texts=result,
        was_reconciled=True,
        action="padded",
        gaps_filled=gaps_filled,
        original_text_count=original_text_count,
        image_count=image_count,
        alignment_confidence=confidence,
    )
