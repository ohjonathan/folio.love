"""Main conversion orchestrator. Ties the pipeline stages together."""

import logging
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml as yaml_lib

from .config import FolioConfig
from .pipeline import normalize, images, text, analysis
from .tracking import sources, versions
from .output import frontmatter, markdown

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of a single file conversion."""
    output_path: Path
    slide_count: int
    version: int
    changes: versions.ChangeSet
    deck_id: str
    cache_stats: Optional["analysis.CacheStats"] = None


class FolioConverter:
    """Orchestrates the full conversion pipeline."""

    def __init__(self, config: Optional[FolioConfig] = None):
        self.config = config or FolioConfig.load()

    def convert(
        self,
        source_path: Path,
        note: Optional[str] = None,
        client: Optional[str] = None,
        engagement: Optional[str] = None,
        target: Optional[Path] = None,
        passes: Optional[int] = None,
        no_cache: bool = False,
        subtype: str = "research",
        industry: Optional[list[str]] = None,
        extra_tags: Optional[list[str]] = None,
    ) -> ConversionResult:
        """Convert a single PPTX/PDF to Folio markdown.

        Args:
            source_path: Path to the source file.
            note: Optional version note.
            client: Client name (for frontmatter and ID).
            engagement: Engagement identifier (for frontmatter and ID).
            target: Override target directory in library.
            subtype: Evidence subtype (default "research").
            industry: Industry tags (optional).
            extra_tags: Manual tags to merge with auto-generated.

        Returns:
            ConversionResult with output path and metadata.

        Raises:
            Various pipeline errors if conversion fails.
        """
        source_path = Path(source_path).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        deck_name = _sanitize_name(source_path.stem)
        logger.info("Converting: %s", source_path.name)

        # Determine output location
        deck_dir = self._resolve_target(
            source_path, deck_name, client, engagement, target
        )
        deck_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = deck_dir / f"{deck_name}.md"

        # Generate ID
        deck_id = _generate_id(
            client=client,
            engagement=engagement,
            deck_name=deck_name,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Stage 1: Normalize to PDF
            logger.info("  Normalizing to PDF...")
            pdf_path = normalize.to_pdf(
                source_path, tmpdir,
                timeout=self.config.conversion.libreoffice_timeout,
            )

            # Stage 2: Extract images
            logger.info("  Extracting images...")
            image_results = images.extract_with_metadata(
                pdf_path, deck_dir,
                dpi=self.config.conversion.image_dpi,
            )
            image_paths = [r.path for r in image_results]
            slide_count = len(image_results)

            blank_slides = {r.slide_num for r in image_results if r.is_blank}
            if blank_slides:
                logger.info("Blank slides detected: %s", sorted(blank_slides))

            # Stage 3: Extract text
            logger.info("  Extracting text...")
            slide_texts = text.extract_structured(source_path)

            reconciliation = text.reconcile_slide_count(slide_texts, slide_count)
            slide_texts = reconciliation.slide_texts

            # Blank override MUST occur before Pass 2 density scoring
            # to prevent hallucinated evidence accumulation on blank slides.

            # Stage 4: LLM analysis
            logger.info("  Running LLM analysis...")
            slide_analyses, pass1_stats = analysis.analyze_slides(
                image_paths,
                model=self.config.llm.model,
                cache_dir=deck_dir,
                slide_texts=slide_texts,
                force_miss=no_cache,
            )

            # Override blank slides with pending() (API call ran but result is unreliable)
            for slide_num in blank_slides:
                if slide_num in slide_analyses:
                    slide_analyses[slide_num] = analysis.SlideAnalysis.pending()

            # Stage 4b: Optional depth pass
            effective_passes = passes if passes is not None else self.config.conversion.default_passes
            if effective_passes >= 2:
                logger.info("  Running depth pass (Pass 2)...")
                slide_analyses, pass2_stats = analysis.analyze_slides_deep(
                    pass1_results=slide_analyses,
                    slide_texts=slide_texts,
                    image_paths=image_paths,
                    model=self.config.llm.model,
                    cache_dir=deck_dir,
                    density_threshold=self.config.conversion.density_threshold,
                    skip_slides=blank_slides,
                    force_miss=no_cache,
                )
                combined_stats = pass1_stats.merge(pass2_stats)
            else:
                combined_stats = pass1_stats

        # Compute source tracking
        source_info = sources.compute_source_info(source_path, markdown_path)

        # Compute version (includes change detection)
        version_info = versions.compute_version(
            deck_dir=deck_dir,
            source_hash=source_info.file_hash,
            source_path=source_info.relative_path,
            slide_count=slide_count,
            new_texts=slide_texts,
            note=note,
        )

        # Load full version history for the document
        history_path = deck_dir / "version_history.json"
        version_history = versions.load_version_history(history_path)

        # Read existing frontmatter for reconversion preservation
        existing_fm = _read_existing_frontmatter(markdown_path)

        # Build reconciliation metadata for frontmatter
        reconciliation_meta = None
        if reconciliation.was_reconciled:
            reconciliation_meta = {
                "text_reconciled": True,
                "text_reconciliation": reconciliation.action,
                "text_alignment_confidence": round(reconciliation.alignment_confidence, 2),
                "text_alignment_status": _alignment_status(reconciliation.alignment_confidence),
            }

        # Generate frontmatter
        fm = frontmatter.generate(
            title=_title_from_name(deck_name),
            deck_id=deck_id,
            source_relative_path=source_info.relative_path,
            source_hash=source_info.file_hash,
            source_type=_detect_source_type(source_path),
            version_info=version_info,
            analyses=slide_analyses,
            subtype=subtype,
            client=client,
            engagement=engagement,
            industry=industry,
            extra_tags=extra_tags,
            existing_frontmatter=existing_fm,
            reconciliation_metadata=reconciliation_meta,
        )

        # Assemble markdown
        md_content = markdown.assemble(
            title=_title_from_name(deck_name),
            frontmatter=fm,
            source_display_path=source_info.relative_path,
            version_info=version_info,
            slide_texts=slide_texts,
            slide_analyses=slide_analyses,
            slide_count=slide_count,
            version_history=version_history,
        )

        # Write output (atomic)
        tmp_md = markdown_path.with_suffix(".md.tmp")
        tmp_md.write_text(md_content)
        tmp_md.rename(markdown_path)

        logger.info(
            "  ✓ Converted: %s (v%d, %d slides)",
            markdown_path.name, version_info.version, slide_count,
        )

        return ConversionResult(
            output_path=markdown_path,
            slide_count=slide_count,
            version=version_info.version,
            changes=version_info.changes,
            deck_id=deck_id,
            cache_stats=combined_stats,
        )

    def _resolve_target(
        self,
        source_path: Path,
        deck_name: str,
        client: Optional[str],
        engagement: Optional[str],
        target: Optional[Path],
    ) -> Path:
        """Determine the output directory for a conversion."""
        if target:
            return Path(target)

        library_root = self.config.library_root.resolve()

        if client and engagement:
            engagement_short = _sanitize_name(engagement)
            return library_root / client / engagement_short / deck_name
        elif client:
            return library_root / client / deck_name
        else:
            return library_root / deck_name


def _alignment_status(confidence: float) -> str:
    """Map alignment confidence to a status string."""
    if confidence >= 0.7:
        return "accepted"
    elif confidence >= 0.3:
        return "degraded"
    return "untrusted"


def _detect_source_type(source_path: Path) -> str:
    """Detect source type from file extension."""
    ext = source_path.suffix.lower()
    if ext in (".pptx", ".ppt"):
        return "deck"
    return "pdf"


def _sanitize_name(name: str) -> str:
    """Sanitize a name for use in file paths and IDs."""
    # Replace spaces and special chars with underscores
    name = re.sub(r"[^\w\-.]", "_", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    return name.strip("_").lower()


def _title_from_name(deck_name: str) -> str:
    """Convert a sanitized deck name to a human-readable title."""
    return deck_name.replace("_", " ").replace("-", " ").title()


def _generate_id(
    client: Optional[str] = None,
    engagement: Optional[str] = None,
    deck_name: str = "",
) -> str:
    """Generate a date-based ID following Folio convention.

    Pattern: {client}_{engagement-short}_{type}_{date}_{descriptor}
    """
    date_str = datetime.now().strftime("%Y%m%d")
    parts = []

    if client:
        parts.append(_sanitize_name(client))
    if engagement:
        parts.append(_sanitize_name(engagement))

    parts.append("evidence")
    parts.append(date_str)
    parts.append(_sanitize_name(deck_name))

    return "_".join(parts)


def _read_existing_frontmatter(markdown_path: Path) -> Optional[dict]:
    """Read existing YAML frontmatter from a markdown file, if it exists.

    Returns the parsed YAML dict, or None if the file doesn't exist
    or doesn't have valid frontmatter.
    """
    if not markdown_path.exists():
        return None
    try:
        content = markdown_path.read_text()
        if not content.startswith("---"):
            return None
        end = content.index("---", 3)
        return yaml_lib.safe_load(content[3:end])
    except (ValueError, yaml_lib.YAMLError, OSError):
        return None
