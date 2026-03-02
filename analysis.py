"""Stage 4: LLM analysis. Generate structured analysis per slide via Claude API."""

import base64
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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

Format your response exactly as:
Slide Type: [type]
Framework: [framework]
Visual Description: [description]
Key Data: [data points]
Main Insight: [insight]"""


@dataclass
class SlideAnalysis:
    """Structured analysis of a single slide."""
    slide_type: str = "unknown"
    framework: str = "none"
    visual_description: str = ""
    key_data: str = ""
    main_insight: str = ""

    def to_dict(self) -> dict:
        return {
            "slide_type": self.slide_type,
            "framework": self.framework,
            "visual_description": self.visual_description,
            "key_data": self.key_data,
            "main_insight": self.main_insight,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SlideAnalysis":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})

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
) -> dict[int, SlideAnalysis]:
    """Analyze slides via Claude API with caching.

    Args:
        image_paths: Ordered list of slide image paths.
        model: Claude model to use.
        cache_dir: Directory for analysis cache. If None, no caching.

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
        analysis = _analyze_single_slide(client, image_path, model)
        results[i] = analysis

        # Update cache
        if cache_dir:
            cache[image_hash] = analysis.to_dict()

    # Save cache
    if cache_dir:
        _save_cache(cache_dir, cache)

    return results


def _analyze_single_slide(
    client, image_path: Path, model: str, max_retries: int = 1
) -> SlideAnalysis:
    """Analyze a single slide image via Claude API."""
    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    media_type = "image/png"

    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
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
            return _parse_analysis(raw_text)

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
        "main_insight": r"Main Insight:\s*(.+?)(?:\n|$)",
    }

    for field_name, pattern in patterns.items():
        match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Normalize slide_type and framework to lowercase-hyphenated
            if field_name in ("slide_type", "framework"):
                value = value.lower().replace(" ", "-")
            setattr(analysis, field_name, value)

    return analysis


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
