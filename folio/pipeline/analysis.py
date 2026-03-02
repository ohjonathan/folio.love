"""Stage 4: LLM analysis. Generate structured analysis per slide via Claude API."""

import base64
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .text import SlideText

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Analyze this consulting slide and provide:

1. SLIDE TYPE: One of: title, executive-summary, framework, data, narrative, next-steps, appendix

2. FRAMEWORK: If a consulting framework is used, identify it: 2x2-matrix, scr, mece, waterfall, gantt, timeline, process-flow, org-chart, tam-sam-som, porter-five-forces, value-chain, bcg-matrix, or "none"

3. VISUAL DESCRIPTION: Describe what you see that wouldn't be captured by text extraction alone. Include:
   - For matrices: axis labels, quadrant contents, positioning
   - For charts: chart type, axes, key data points
   - For diagrams: structure, flow, relationships
   - For tables: column/row structure if complex

4. KEY DATA: List specific numbers, percentages, dates, or metrics shown

5. MAIN INSIGHT: One sentence summarizing the "so what" of this slide

6. EVIDENCE: For each claim above, cite the exact text from the slide that supports it. For each piece of evidence provide:
   - Claim: What you are claiming (e.g. "Framework detection", "Market sizing")
   - Quote: Exact text from the slide supporting this claim
   - Element: Which part of the slide (title, body, or note)
   - Confidence: high, medium, or low

Format your response exactly as:
Slide Type: [type]
Framework: [framework]
Visual Description: [description]
Key Data: [data points]
Main Insight: [insight]
Evidence:
- Claim: [what this evidence supports]
  Quote: "[exact text from slide]"
  Element: [title|body|note]
  Confidence: [high|medium|low]
- Claim: [next claim]
  Quote: "[exact text]"
  Element: [title|body|note]
  Confidence: [high|medium|low]"""


@dataclass
class SlideAnalysis:
    """Structured analysis of a single slide."""
    slide_type: str = "unknown"
    framework: str = "none"
    visual_description: str = ""
    key_data: str = ""
    main_insight: str = ""
    evidence: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "slide_type": self.slide_type,
            "framework": self.framework,
            "visual_description": self.visual_description,
            "key_data": self.key_data,
            "main_insight": self.main_insight,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SlideAnalysis":
        fields = {k: d.get(k, "") for k in ("slide_type", "framework",
                  "visual_description", "key_data", "main_insight")}
        fields["evidence"] = d.get("evidence", [])
        return cls(**fields)

    @classmethod
    def pending(cls) -> "SlideAnalysis":
        """Return a placeholder for when analysis is unavailable."""
        return cls(
            slide_type="pending",
            framework="pending",
            visual_description="[Analysis pending - API unavailable]",
            key_data="[pending]",
            main_insight="[pending]",
        )


def analyze_slides(
    image_paths: list[Path],
    model: str = "claude-sonnet-4-20250514",
    cache_dir: Optional[Path] = None,
    slide_texts: Optional[dict[int, "SlideText"]] = None,
) -> dict[int, SlideAnalysis]:
    """Analyze slides via Claude API with caching.

    Args:
        image_paths: Ordered list of slide image paths.
        model: Claude model to use.
        cache_dir: Directory for analysis cache. If None, no caching.
        slide_texts: Extracted text per slide for evidence validation.

    Returns:
        Dict mapping slide number (1-indexed) to SlideAnalysis.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning(
            "ANTHROPIC_API_KEY not set. Skipping LLM analysis. "
            "Set the env var to enable framework detection."
        )
        return {i + 1: SlideAnalysis.pending() for i in range(len(image_paths))}

    # Load cache
    cache = _load_cache(cache_dir) if cache_dir else {}

    try:
        from anthropic import Anthropic
        client = Anthropic()
    except ImportError:
        logger.warning("anthropic package not installed. Skipping analysis.")
        return {i + 1: SlideAnalysis.pending() for i in range(len(image_paths))}

    results = {}
    for i, image_path in enumerate(image_paths, 1):
        image_hash = _hash_image(image_path)

        # Check cache
        if image_hash in cache:
            logger.debug("Slide %d: using cached analysis", i)
            results[i] = SlideAnalysis.from_dict(cache[image_hash])
            continue

        # Call API
        logger.info("Analyzing slide %d/%d...", i, len(image_paths))
        slide_text = slide_texts.get(i) if slide_texts else None
        analysis = _analyze_single_slide(client, image_path, model, slide_text=slide_text)
        results[i] = analysis

        # Update cache
        if cache_dir:
            cache[image_hash] = analysis.to_dict()

    # Save cache
    if cache_dir:
        _save_cache(cache_dir, cache)

    return results


def _analyze_single_slide(
    client, image_path: Path, model: str, max_retries: int = 1,
    slide_text: Optional["SlideText"] = None,
) -> SlideAnalysis:
    """Analyze a single slide image via Claude API."""
    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    media_type = "image/png"

    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": ANALYSIS_PROMPT,
                        },
                    ],
                }],
            )
            raw_text = response.content[0].text
            analysis = _parse_analysis(raw_text)

            # Validate evidence against extracted text
            if slide_text and analysis.evidence:
                _validate_evidence(analysis.evidence, slide_text)

            return analysis

        except Exception as e:
            if attempt < max_retries:
                logger.warning("Slide analysis failed (attempt %d), retrying: %s", attempt + 1, e)
                time.sleep(2 ** attempt)
            else:
                logger.warning("Slide analysis failed after %d attempts: %s", max_retries + 1, e)
                return SlideAnalysis.pending()


def _parse_analysis(raw_text: str) -> SlideAnalysis:
    """Parse structured analysis from LLM response text."""
    analysis = SlideAnalysis()

    patterns = {
        "slide_type": r"Slide Type:\s*(.+?)(?:\n|$)",
        "framework": r"Framework:\s*(.+?)(?:\n|$)",
        "visual_description": r"Visual Description:\s*(.+?)(?=\nKey Data:|\n\n|$)",
        "key_data": r"Key Data:\s*(.+?)(?=\nMain Insight:|\n\n|$)",
        "main_insight": r"Main Insight:\s*(.+?)(?=\nEvidence:|\n\n|$)",
    }

    for field_name, pattern in patterns.items():
        match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Normalize slide_type and framework to lowercase-hyphenated
            if field_name in ("slide_type", "framework"):
                value = value.lower().replace(" ", "-")
            setattr(analysis, field_name, value)

    # Parse evidence blocks
    analysis.evidence = _parse_evidence(raw_text)

    return analysis


def _parse_evidence(raw_text: str) -> list[dict]:
    """Parse evidence blocks from LLM response.

    Expects format:
    Evidence:
    - Claim: ...
      Quote: "..."
      Element: title|body|note
      Confidence: high|medium|low
    """
    evidence_items = []

    # Find the Evidence: section
    evidence_match = re.search(r"Evidence:\s*\n", raw_text, re.IGNORECASE)
    if not evidence_match:
        return []

    evidence_text = raw_text[evidence_match.end():]

    # Split into individual evidence items by "- Claim:" pattern
    item_pattern = re.compile(r"^-\s*Claim:\s*", re.MULTILINE)
    item_starts = list(item_pattern.finditer(evidence_text))

    for idx, match in enumerate(item_starts):
        start = match.start()
        end = item_starts[idx + 1].start() if idx + 1 < len(item_starts) else len(evidence_text)
        item_text = evidence_text[start:end]

        item = _parse_single_evidence(item_text)
        if item:
            evidence_items.append(item)

    return evidence_items


def _parse_single_evidence(item_text: str) -> Optional[dict]:
    """Parse a single evidence item from text block."""
    claim_match = re.search(r"Claim:\s*(.+?)(?:\n|$)", item_text, re.IGNORECASE)
    quote_match = re.search(r'Quote:\s*"?([^"]*?)"?\s*(?:\n|$)', item_text, re.IGNORECASE)
    element_match = re.search(r"Element:\s*(\w+)", item_text, re.IGNORECASE)
    confidence_match = re.search(r"Confidence:\s*(\w+)", item_text, re.IGNORECASE)

    if not claim_match:
        return None

    claim = claim_match.group(1).strip()
    quote = quote_match.group(1).strip() if quote_match else ""
    element_type = element_match.group(1).strip().lower() if element_match else "body"
    confidence = confidence_match.group(1).strip().lower() if confidence_match else "medium"

    # Normalize confidence
    if confidence not in ("high", "medium", "low"):
        confidence = "medium"
    # Normalize element type
    if element_type not in ("title", "body", "note"):
        element_type = "body"

    return {
        "claim": claim,
        "quote": quote,
        "element_type": element_type,
        "confidence": confidence,
        "validated": False,
        "pass": 1,
    }


def _validate_evidence(evidence: list[dict], slide_text: "SlideText") -> None:
    """Validate evidence items against extracted slide text.

    Sets 'validated' to True/False on each evidence dict in place.
    """
    full_text_normalized = _normalize_for_matching(slide_text.full_text)

    for item in evidence:
        quote = item.get("quote", "")
        if not quote:
            item["validated"] = False
            continue

        quote_normalized = _normalize_for_matching(quote)

        # Check 1: substring match
        if quote_normalized in full_text_normalized:
            item["validated"] = True
            continue

        # Check 2: word overlap (80% threshold)
        quote_words = set(quote_normalized.split())
        text_words = set(full_text_normalized.split())
        if quote_words and len(quote_words & text_words) / len(quote_words) >= 0.8:
            item["validated"] = True
            continue

        item["validated"] = False
        logger.debug("Evidence not validated: %s", quote[:50])


def _normalize_for_matching(text: str) -> str:
    """Normalize text for evidence matching: lowercase, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s.,;:$%()-]", "", text)
    return text.strip()


DEPTH_PROMPT = """You previously analyzed this consulting slide. Now look deeper.

Previous analysis found:
- Slide type: {slide_type}
- Framework: {framework}
- Key data: {key_data}
- Main insight: {main_insight}

Now extract additional details:
1. Additional data points not captured in the first pass
2. Relationships between data points
3. Assumptions implied by the slide
4. Caveats or limitations mentioned or implied

For each finding, cite the exact text from the slide.

Format your response exactly as:
Evidence:
- Claim: [what this evidence supports]
  Quote: "[exact text from slide]"
  Element: [title|body|note]
  Confidence: [high|medium|low]"""

DATA_HEAVY_TYPES = {"data", "framework", "executive-summary"}


def _compute_density_score(analysis: SlideAnalysis, text: "SlideText") -> float:
    """Compute a density score for a slide to determine if it needs a second pass.

    Score components:
    - Evidence count * 0.3
    - Word count: >150 → 1.0, >75 → 0.5
    - Framework detected → 1.0
    - Data-heavy slide type → 0.5
    - Comma-delimited data points → min(count * 0.2, 1.0)
    """
    score = 0.0

    # Evidence count
    score += len(analysis.evidence) * 0.3

    # Word count
    word_count = len(text.full_text.split()) if text.full_text else 0
    if word_count > 150:
        score += 1.0
    elif word_count > 75:
        score += 0.5

    # Framework detected
    if analysis.framework not in ("none", "pending", ""):
        score += 1.0

    # Data-heavy slide type
    if analysis.slide_type in DATA_HEAVY_TYPES:
        score += 0.5

    # Comma-delimited data points
    comma_count = text.full_text.count(",") if text.full_text else 0
    score += min(comma_count * 0.2, 1.0)

    return score


def _deduplicate_evidence(existing: list[dict], new_items: list[dict]) -> list[dict]:
    """Deduplicate evidence items across passes.

    If >85% word overlap, keep the higher confidence version.
    """
    confidence_rank = {"high": 3, "medium": 2, "low": 1}
    result = list(existing)

    for new_item in new_items:
        new_words = set(new_item.get("quote", "").lower().split())
        is_duplicate = False

        for i, existing_item in enumerate(result):
            existing_words = set(existing_item.get("quote", "").lower().split())
            if not new_words or not existing_words:
                continue

            overlap = len(new_words & existing_words)
            max_len = max(len(new_words), len(existing_words))
            if max_len > 0 and overlap / max_len >= 0.85:
                # Keep higher confidence
                new_rank = confidence_rank.get(new_item.get("confidence", "medium"), 2)
                old_rank = confidence_rank.get(existing_item.get("confidence", "medium"), 2)
                if new_rank > old_rank:
                    result[i] = new_item
                is_duplicate = True
                break

        if not is_duplicate:
            result.append(new_item)

    return result


def analyze_slides_deep(
    pass1_results: dict[int, SlideAnalysis],
    slide_texts: dict[int, "SlideText"],
    image_paths: list[Path],
    model: str = "claude-sonnet-4-20250514",
    cache_dir: Optional[Path] = None,
    density_threshold: float = 2.0,
) -> dict[int, SlideAnalysis]:
    """Run selective second pass on high-density slides.

    Args:
        pass1_results: Results from first analysis pass.
        slide_texts: Extracted text per slide.
        image_paths: Ordered list of slide image paths.
        model: Claude model to use.
        cache_dir: Directory for analysis cache.
        density_threshold: Minimum density score for second pass.

    Returns:
        Updated analysis results with merged Pass 2 evidence.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return pass1_results

    # Identify high-density slides
    dense_slides = []
    for slide_num, analysis in pass1_results.items():
        text = slide_texts.get(slide_num)
        if text:
            score = _compute_density_score(analysis, text)
            if score >= density_threshold:
                dense_slides.append(slide_num)
                logger.info(
                    "Slide %d: density score %.1f (above %.1f threshold) — queued for Pass 2",
                    slide_num, score, density_threshold,
                )

    if not dense_slides:
        logger.info("No slides above density threshold — skipping Pass 2")
        return pass1_results

    logger.info("Pass 2: analyzing %d high-density slides", len(dense_slides))

    # Load deep cache
    deep_cache = _load_cache_deep(cache_dir) if cache_dir else {}

    try:
        from anthropic import Anthropic
        client = Anthropic()
    except ImportError:
        return pass1_results

    results = dict(pass1_results)  # Copy

    for slide_num in dense_slides:
        if slide_num < 1 or slide_num > len(image_paths):
            continue

        image_path = image_paths[slide_num - 1]
        image_hash = _hash_image(image_path)
        deep_key = f"{image_hash}_deep"

        # Check deep cache
        if deep_key in deep_cache:
            logger.debug("Slide %d: using cached deep analysis", slide_num)
            new_evidence = deep_cache[deep_key]
        else:
            # Build depth prompt with Pass 1 context
            analysis = results[slide_num]
            prompt = DEPTH_PROMPT.format(
                slide_type=analysis.slide_type,
                framework=analysis.framework,
                key_data=analysis.key_data,
                main_insight=analysis.main_insight,
            )

            new_evidence = _run_depth_pass(
                client, image_path, model, prompt,
                slide_text=slide_texts.get(slide_num),
            )

            if cache_dir:
                deep_cache[deep_key] = new_evidence

        # Merge evidence
        if new_evidence:
            # Tag as pass 2
            for ev in new_evidence:
                ev["pass"] = 2

            merged = _deduplicate_evidence(results[slide_num].evidence, new_evidence)
            results[slide_num].evidence = merged

            # Check for differing slide_type/framework
            # (depth pass doesn't return these, so this is a no-op for now)

    # Save deep cache
    if cache_dir:
        _save_cache_deep(cache_dir, deep_cache)

    return results


def _run_depth_pass(
    client, image_path: Path, model: str, prompt: str,
    slide_text: Optional["SlideText"] = None,
    max_retries: int = 1,
) -> list[dict]:
    """Run a depth pass on a single slide, returning new evidence items."""
    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    media_type = "image/png"

    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }],
            )
            raw_text = response.content[0].text
            evidence = _parse_evidence(raw_text)

            # Validate against source text
            if slide_text and evidence:
                _validate_evidence(evidence, slide_text)

            return evidence

        except Exception as e:
            if attempt < max_retries:
                logger.warning("Depth pass failed (attempt %d), retrying: %s", attempt + 1, e)
                time.sleep(2 ** attempt)
            else:
                logger.warning("Depth pass failed after %d attempts: %s", max_retries + 1, e)
                return []


def _load_cache_deep(cache_dir: Path) -> dict:
    """Load deep analysis cache from disk."""
    cache_file = cache_dir / ".analysis_cache_deep.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache_deep(cache_dir: Path, cache: dict):
    """Save deep analysis cache to disk."""
    cache_file = cache_dir / ".analysis_cache_deep.json"
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = cache_file.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(cache, indent=2))
    tmp_file.rename(cache_file)


def _hash_image(image_path: Path) -> str:
    """Compute SHA256 hash of an image file."""
    sha256 = hashlib.sha256()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]


def _load_cache(cache_dir: Path) -> dict:
    """Load analysis cache from disk."""
    cache_file = cache_dir / ".analysis_cache.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache_dir: Path, cache: dict):
    """Save analysis cache to disk."""
    cache_file = cache_dir / ".analysis_cache.json"
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Atomic write
    tmp_file = cache_file.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(cache, indent=2))
    tmp_file.rename(cache_file)
