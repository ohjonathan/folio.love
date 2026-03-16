"""Main conversion orchestrator. Ties the pipeline stages together."""

import logging
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml as yaml_lib

from .config import FolioConfig
from .pipeline import normalize, images, text, analysis, inspect
from .tracking import sources, versions
from .tracking import registry
from .output import frontmatter, markdown

logger = logging.getLogger(__name__)

# Shared constant for PPTX/PPT extensions — used by cli.py too.
PPTX_EXTENSIONS = frozenset({".pptx", ".ppt"})


@dataclass
class ConversionResult:
    """Result of a single file conversion."""
    output_path: Path
    slide_count: int
    version: int
    changes: versions.ChangeSet
    deck_id: str
    renderer_used: str = "unknown"
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
        llm_profile: Optional[str] = None,
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

        # Infer client/engagement from source-root mapping if not explicit
        inferred_client, inferred_engagement = self._infer_from_source_root(
            source_path, client, engagement
        )
        effective_client = client if client is not None else inferred_client
        effective_engagement = engagement if engagement is not None else inferred_engagement

        # Determine output location
        deck_dir = self._resolve_target(
            source_path, deck_name, effective_client, effective_engagement, target
        )
        deck_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = deck_dir / f"{deck_name}.md"

        # Read existing frontmatter early for ID stability on reconversion (B1)
        existing_fm = _read_existing_frontmatter(markdown_path)

        # Use existing ID on reconversion to prevent registry drift (B1)
        if isinstance(existing_fm, dict) and existing_fm.get("id"):
            deck_id = existing_fm["id"]
        else:
            deck_id = _generate_id(
                client=effective_client,
                engagement=effective_engagement,
                deck_name=deck_name,
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Stage 1: Normalize to PDF
            logger.info("  Normalizing to PDF...")
            norm_result = normalize.to_pdf(
                source_path, tmpdir,
                timeout=self.config.conversion.libreoffice_timeout,
                renderer=self.config.conversion.pptx_renderer,
            )
            pdf_path = norm_result.pdf_path
            renderer_used = norm_result.renderer_used
            logger.info("  Renderer used: %s", renderer_used)

            # Stage 1½: Deterministic page inspection
            logger.info("  Inspecting pages...")
            page_profiles = inspect.inspect_pages(pdf_path)

            # Stage 2: Extract images
            logger.info("  Extracting images...")
            try:
                image_results = images.extract_with_metadata(
                    pdf_path, deck_dir,
                    dpi=self.config.conversion.image_dpi,
                    page_profiles=page_profiles,
                )
            finally:
                # Clean up intermediate PowerPoint PDF written into deck_dir.
                # Runs whether image extraction succeeds or fails.
                # Only when: source is PPTX/PPT and the PDF landed in deck_dir.
                # NOTE: Since PR #12, PowerPoint writes to a staging dir and
                # normalize.to_pdf() moves the PDF to tmpdir, so this condition
                # is normally false for PPTX.  Kept as a safety net for callers
                # that override pptx_output_dir to deck_dir.
                if (
                    source_path.suffix.lower() in PPTX_EXTENSIONS
                    and pdf_path.resolve().parent == deck_dir.resolve()
                    and pdf_path.exists()
                ):
                    pdf_path.unlink()
                    logger.debug(
                        "Cleaned up intermediate PowerPoint PDF: %s", pdf_path.name
                    )
            image_paths = [r.path for r in image_results]
            slide_count = len(image_results)

            # Blank detection: combine inspection + histogram.
            # Structurally blank (no text, no vectors, no images):
            structural_blanks = {
                p for p, prof in page_profiles.items()
                if prof.classification == "blank"
            }
            # image_blank pages need histogram confirmation (BLK-2 fix):
            # A raster-only page is only blank if the histogram also says so.
            histogram_blanks = {r.slide_num for r in image_results if r.is_blank}
            image_blanks_confirmed = {
                p for p, prof in page_profiles.items()
                if prof.classification == "image_blank" and p in histogram_blanks
            }
            blank_slides = structural_blanks | image_blanks_confirmed
            if blank_slides:
                logger.info("Blank slides: %s", sorted(blank_slides))

            # PR 3: Derive diagram-like slide sets from classifications
            _DIAGRAM_CLASSIFICATIONS = {"diagram", "mixed", "unsupported_diagram"}
            diagram_like_slides = {
                p for p, prof in page_profiles.items()
                if prof.classification in _DIAGRAM_CLASSIFICATIONS
            }
            # Currently empty — unsupported_diagram classification deferred to PR 4
            unsupported_diagram_slides = {
                p for p, prof in page_profiles.items()
                if prof.classification == "unsupported_diagram"
            }
            diagram_or_mixed_slides = {
                p for p, prof in page_profiles.items()
                if prof.classification in {"diagram", "mixed"}
            }
            if diagram_like_slides:
                logger.info("Diagram-like slides: %s", sorted(diagram_like_slides))

            # PR 6: Frozen-note detection
            # Derive created_date for stable note naming
            created_date = datetime.now(timezone.utc).strftime("%Y%m%d")
            if isinstance(existing_fm, dict):
                prev_created = existing_fm.get("created", "")
                if isinstance(prev_created, str) and len(prev_created) >= 10:
                    created_date = prev_created[:10].replace("-", "")

            from .output.diagram_notes import discover_frozen_notes, emit_diagram_notes
            frozen_payloads = discover_frozen_notes(
                deck_dir, deck_name, created_date, page_profiles,
            )
            frozen_diagram_slides = {
                p for p, payload in frozen_payloads.items()
                if page_profiles.get(p) and page_profiles[p].classification == "diagram"
            }
            frozen_mixed_slides = {
                p for p, payload in frozen_payloads.items()
                if page_profiles.get(p) and page_profiles[p].classification == "mixed"
            }
            all_frozen_diagram_slides = frozen_diagram_slides | frozen_mixed_slides
            if all_frozen_diagram_slides:
                logger.info("Frozen diagram slides: %s", sorted(all_frozen_diagram_slides))

            # Stage 3: Extract text
            logger.info("  Extracting text...")
            slide_texts = text.extract_structured(source_path)

            # Sparse-text warning BEFORE reconciliation (which may pad empty
            # SlideText entries, artificially lowering the average).
            if slide_count > 0:
                total_chars = sum(
                    len(st.full_text or "") for st in slide_texts.values()
                )
                avg_chars = total_chars / slide_count
                if avg_chars < 10:
                    is_pdf_source = source_path.suffix.lower() == ".pdf"
                    kind = "scanned PDF" if is_pdf_source else "very sparse text"
                    logger.warning(
                        "Low text density (%.0f chars/page avg): %s may have %s. "
                        "Extraction quality may be reduced.",
                        avg_chars, source_path.name, kind,
                    )

            reconciliation = text.reconcile_slide_count(slide_texts, slide_count)
            slide_texts = reconciliation.slide_texts

            # Blank override MUST occur before Pass 2 density scoring
            # to prevent hallucinated evidence accumulation on blank slides.

            # Stage 4: LLM analysis
            logger.info("  Running LLM analysis...")
            profile = self.config.llm.resolve_profile(llm_profile, task="convert")
            fallback_profiles_list = [
                (fb.provider, fb.model, fb.api_key_env)
                for fb in self.config.llm.get_fallbacks(override=llm_profile, task="convert")
            ]
            # Pass full provider settings dict (Finding 1: each fallback needs its own settings)
            all_provider_settings = self.config.providers

            # PR 3: Compute pass-1 slide numbers, excluding unsupported_diagram
            # PR 6: Also exclude frozen pure diagram slides from Pass 1
            all_slide_nums = [r.slide_num for r in image_results]
            pass1_exclude = unsupported_diagram_slides | frozen_diagram_slides
            pass1_slide_numbers = [n for n in all_slide_nums if n not in pass1_exclude]
            pass1_image_paths = [
                r.path for r in image_results if r.slide_num not in pass1_exclude
            ]

            slide_analyses, pass1_stats, pass1_meta = analysis.analyze_slides(
                pass1_image_paths,
                model=profile.model,
                cache_dir=deck_dir,
                slide_texts=slide_texts,
                force_miss=no_cache,
                provider_name=profile.provider,
                api_key_env=profile.api_key_env,
                fallback_profiles=fallback_profiles_list,
                all_provider_settings=all_provider_settings,
                slide_numbers=pass1_slide_numbers,
            )

            # PR 3: Insert abstained DiagramAnalysis placeholders for unsupported_diagram
            for slide_num in unsupported_diagram_slides:
                slide_analyses[slide_num] = analysis.DiagramAnalysis(
                    slide_type="pending",
                    framework="pending",
                    visual_description="[Unsupported diagram — abstained]",
                    key_data="[pending]",
                    main_insight="[pending]",
                    diagram_type="unsupported",
                    abstained=True,
                    review_required=True,
                )

            # Override blank slides with pending() (API call ran but result is unreliable)
            for slide_num in blank_slides:
                if slide_num in slide_analyses:
                    slide_analyses[slide_num] = analysis.SlideAnalysis.pending()

            # M3: Blank and diagram classifications are mutually exclusive.
            # If this invariant ever breaks, the ordering below would silently
            # re-promote blank slides to DiagramAnalysis.
            assert not (blank_slides & diagram_or_mixed_slides), (
                f"Slide(s) classified as both blank and diagram: "
                f"{blank_slides & diagram_or_mixed_slides}"
            )

            # PR 3: Coerce diagram/mixed pages to DiagramAnalysis post pass-1
            for slide_num in diagram_or_mixed_slides:
                existing = slide_analyses.get(slide_num)
                if existing and not isinstance(existing, analysis.DiagramAnalysis):
                    classification = page_profiles.get(slide_num)
                    dtype = classification.classification if classification else "unknown"
                    slide_analyses[slide_num] = analysis.DiagramAnalysis.from_slide_analysis(
                        existing,
                        diagram_type=dtype,
                    )

            # PR 4: Diagram extraction for diagram/mixed slides
            # PR 6: Exclude frozen slides from diagram extraction and rendering
            diagram_extract_slides = diagram_or_mixed_slides - all_frozen_diagram_slides
            if diagram_extract_slides:
                from .pipeline import diagram_extraction as diag_ext
                slide_analyses, diagram_stats, diagram_meta = diag_ext.analyze_diagram_pages(
                    pass1_results=slide_analyses,
                    page_profiles=page_profiles,
                    image_results=image_results,
                    slide_texts=slide_texts,
                    cache_dir=deck_dir,
                    force_miss=no_cache,
                    provider_name=profile.provider,
                    model=profile.model,
                    api_key_env=profile.api_key_env,
                    all_provider_settings=all_provider_settings,
                    slide_numbers=sorted(diagram_extract_slides),
                )
                # Merge stats (diagram pass is additive, not replacing pass1)
                pass1_stats = pass1_stats.merge(diagram_stats)

                # PR 5: Deterministic diagram rendering
                # Runs after PR 4 extraction and before assess_review_state()
                # so render-time omit-and-flag behavior feeds review-state computation.
                from .output import diagram_rendering
                slide_analyses = diagram_rendering.render_diagram_analyses(slide_analyses)

            # PR 6: Hydrate frozen diagram analyses
            for slide_num, payload in frozen_payloads.items():
                classification = page_profiles.get(slide_num)
                if not classification:
                    continue
                if classification.classification == "diagram":
                    # Pure diagram: use frozen analysis directly
                    slide_analyses[slide_num] = payload.analysis
                elif classification.classification == "mixed":
                    # Mixed: overlay diagram fields onto fresh Pass 1 result
                    existing_analysis = slide_analyses.get(slide_num)
                    if existing_analysis and isinstance(existing_analysis, analysis.DiagramAnalysis):
                        frozen_a = payload.analysis
                        existing_analysis.diagram_type = frozen_a.diagram_type
                        existing_analysis.graph = frozen_a.graph
                        existing_analysis.mermaid = frozen_a.mermaid
                        existing_analysis.description = frozen_a.description
                        existing_analysis.component_table = frozen_a.component_table
                        existing_analysis.connection_table = frozen_a.connection_table
                        existing_analysis.diagram_confidence = frozen_a.diagram_confidence
                        existing_analysis.extraction_confidence = frozen_a.extraction_confidence
                        existing_analysis.confidence_reasoning = frozen_a.confidence_reasoning
                        existing_analysis.review_required = frozen_a.review_required
                        existing_analysis.review_questions = frozen_a.review_questions
                        existing_analysis.abstained = frozen_a.abstained
                        existing_analysis._extraction_metadata = frozen_a._extraction_metadata

            # Stage 4b: Optional depth pass
            effective_passes = passes if passes is not None else self.config.conversion.default_passes
            pass2_meta = None
            if effective_passes >= 2:
                logger.info("  Running depth pass (Pass 2)...")
                slide_analyses, pass2_stats, pass2_meta = analysis.analyze_slides_deep(
                    pass1_results=slide_analyses,
                    slide_texts=slide_texts,
                    image_paths=image_paths,
                    model=profile.model,
                    cache_dir=deck_dir,
                    density_threshold=self.config.conversion.density_threshold,
                    skip_slides=blank_slides | diagram_like_slides,
                    force_miss=no_cache,
                    provider_name=profile.provider,
                    api_key_env=profile.api_key_env,
                    fallback_profiles=fallback_profiles_list,
                    all_provider_settings=all_provider_settings,
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

        # existing_fm already loaded at method start for ID stability (B1)

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
        # _llm_metadata per spec §7.4 — execution-derived from StageLLMMetadata
        # F2: use per_slide_providers for accurate mixed-provider provenance
        p1_providers = set(pass1_meta.per_slide_providers.values()) if pass1_meta else set()
        p1_primary = (pass1_meta.provider if pass1_meta else profile.provider,
                      pass1_meta.model if pass1_meta else profile.model)
        p1_fallback = pass1_meta.fallback_activated if pass1_meta else False
        p1_provider = pass1_meta.fallback_provider if p1_fallback else p1_primary[0]
        p1_model = pass1_meta.fallback_model if p1_fallback else p1_primary[1]

        pass2_ran = effective_passes >= 2 and pass2_meta is not None
        p2_providers = set(pass2_meta.per_slide_providers.values()) if pass2_meta else set()
        p2_fallback = pass2_meta.fallback_activated if pass2_meta else False
        p2_provider = pass2_meta.fallback_provider if p2_fallback else (pass2_meta.provider if pass2_meta else None)
        p2_model = pass2_meta.fallback_model if p2_fallback else (pass2_meta.model if pass2_meta else None)

        # Overall: if any pass used fallback, report it
        any_fallback = p1_fallback or p2_fallback
        # Determine if run used multiple providers
        all_providers = p1_providers | p2_providers
        mixed_providers = len(set(p for p, _ in all_providers)) > 1 if all_providers else False
        # Use the most recently active provider as the "actual" provider
        actual_provider = p2_provider if (pass2_ran and p2_provider) else p1_provider
        actual_model = p2_model if (pass2_ran and p2_model) else p1_model

        pass1_meta_dict: dict = {
            "provider": p1_provider,
            "model": p1_model,
            "fallback_used": p1_fallback,
        }
        if p1_providers and len(set(p for p, _ in p1_providers)) > 1:
            pass1_meta_dict["providers_used"] = sorted(set(p for p, _ in p1_providers))

        pass2_meta_dict: dict = {
            "status": "executed" if pass2_ran else "skipped",
        }
        if not pass2_ran:
            pass2_meta_dict["reason"] = "pass_disabled"
        else:
            pass2_meta_dict["provider"] = p2_provider
            pass2_meta_dict["model"] = p2_model
            pass2_meta_dict["fallback_used"] = p2_fallback
            if p2_providers and len(set(p for p, _ in p2_providers)) > 1:
                pass2_meta_dict["providers_used"] = sorted(set(p for p, _ in p2_providers))

        llm_meta = {
            "convert": {
                "requested_profile": llm_profile or profile.name,
                "profile": profile.name,
                "provider": actual_provider,
                "model": actual_model,
                "fallback_used": any_fallback,
                "mixed_providers": mixed_providers,
                "status": "executed",
                "pass1": pass1_meta_dict,
                "pass2": pass2_meta_dict,
            },
        }

        # FR-700: Compute review state
        existing_review_status = None
        if isinstance(existing_fm, dict):
            existing_review_status = existing_fm.get("review_status")
        review_assessment = analysis.assess_review_state(
            slide_analyses,
            slide_texts,
            effective_passes=effective_passes,
            density_threshold=self.config.conversion.density_threshold,
            review_confidence_threshold=self.config.conversion.review_confidence_threshold,
            existing_review_status=existing_review_status,
            known_blank_slides=blank_slides,
        )

        # PR 6: Emit standalone diagram notes (after review state, before frontmatter)
        diagram_note_refs = emit_diagram_notes(
            deck_dir=deck_dir,
            deck_slug=deck_name,
            deck_title=_title_from_name(deck_name),
            created_date=created_date,
            analyses=slide_analyses,
            page_profiles=page_profiles,
        )

        fm = frontmatter.generate(
            title=_title_from_name(deck_name),
            deck_id=deck_id,
            source_relative_path=source_info.relative_path,
            source_hash=source_info.file_hash,
            source_type=_detect_source_type(source_path),
            version_info=version_info,
            analyses=slide_analyses,
            subtype=subtype,
            client=effective_client,
            engagement=effective_engagement,
            industry=industry,
            extra_tags=extra_tags,
            existing_frontmatter=existing_fm,
            reconciliation_metadata=reconciliation_meta,
            llm_metadata=llm_meta,
            review_status=review_assessment.review_status,
            review_flags=review_assessment.review_flags,
            extraction_confidence=review_assessment.extraction_confidence,
        )

        # PR 6: Build slide classification map for markdown assembly
        slide_classifications = {
            p: prof.classification
            for p, prof in page_profiles.items()
        }

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
            slide_classifications=slide_classifications,
            diagram_note_refs=diagram_note_refs,
        )

        # Write output (atomic)
        tmp_md = markdown_path.with_suffix(".md.tmp")
        tmp_md.write_text(md_content)
        tmp_md.rename(markdown_path)

        # Upsert registry entry — only for in-library targets (S2)
        library_root = self.config.library_root.resolve()
        in_library = True
        try:
            md_rel = str(markdown_path.relative_to(library_root)).replace("\\", "/")
            deck_dir_rel = str(deck_dir.relative_to(library_root)).replace("\\", "/")
        except ValueError:
            # Target is outside library_root — skip registry upsert
            logger.debug(
                "Output %s is outside library_root %s — skipping registry upsert",
                deck_dir, library_root,
            )
            in_library = False

        if in_library:
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Preserve authority/curation_level from existing frontmatter
            reg_authority = "captured"
            reg_curation = "L0"
            if isinstance(existing_fm, dict):
                prev_auth = existing_fm.get("authority")
                if isinstance(prev_auth, str) and prev_auth:
                    reg_authority = prev_auth
                prev_curation = existing_fm.get("curation_level")
                if isinstance(prev_curation, str) and prev_curation:
                    reg_curation = prev_curation

            reg_entry = registry.RegistryEntry(
                id=deck_id,
                title=_title_from_name(deck_name),
                markdown_path=md_rel,
                deck_dir=deck_dir_rel,
                source_relative_path=source_info.relative_path,
                source_hash=source_info.file_hash,
                source_type=_detect_source_type(source_path),
                version=version_info.version,
                converted=now_str,
                modified=now_str,
                client=effective_client,
                engagement=effective_engagement,
                authority=reg_authority,
                curation_level=reg_curation,
                staleness_status="current",
                review_status=review_assessment.review_status,
                review_flags=review_assessment.review_flags,
                extraction_confidence=review_assessment.extraction_confidence,
                grounding_summary=frontmatter._compute_grounding_summary(slide_analyses),
            )
            registry_path = library_root / "registry.json"
            registry.upsert_entry(registry_path, reg_entry)

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
            renderer_used=renderer_used,
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

        # Source-root-aware routing
        match = self.config.match_source_root(source_path)
        if match:
            src_config, rel_path = match
            prefix = FolioConfig.normalize_target_prefix(src_config.target_prefix)
            relative_parent = rel_path.parent
            if prefix:
                return library_root / prefix / relative_parent / deck_name
            else:
                return library_root / relative_parent / deck_name

        # Fallback: original client/engagement routing
        if client and engagement:
            engagement_short = _sanitize_name(engagement)
            return library_root / client / engagement_short / deck_name
        elif client:
            return library_root / client / deck_name
        else:
            return library_root / deck_name

    def _infer_from_source_root(
        self,
        source_path: Path,
        explicit_client: Optional[str],
        explicit_engagement: Optional[str],
    ) -> tuple[Optional[str], Optional[str]]:
        """Infer client/engagement from source-root-relative path.

        Only infers when target_prefix is empty and CLI flags are not set.
        Returns (client, engagement) — either or both may be None.
        """
        match = self.config.match_source_root(source_path)
        if not match:
            return (None, None)

        src_config, rel_path = match
        prefix = FolioConfig.normalize_target_prefix(src_config.target_prefix)

        # Only infer client/engagement when target_prefix is empty
        if prefix:
            return (None, None)

        parts = rel_path.parent.parts
        if len(parts) >= 2:
            return (parts[0], parts[1])
        elif len(parts) == 1:
            return (parts[0], None)
        else:
            return (None, None)


def _alignment_status(confidence: float) -> str:
    """Map alignment confidence to a status string."""
    if confidence >= 0.7:
        return "accepted"
    elif confidence >= 0.3:
        return "degraded"
    return "untrusted"


def _detect_source_type(source_path: Path) -> str:
    """Detect source type from file extension.

    Returns ``"deck"`` for .pptx/.ppt, ``"pdf"`` for everything else.
    The ontology also defines ``"report"`` but that requires semantic
    classification (not file-extension detection) and is deferred to a
    future ``--source-type`` CLI override or subtype-based inference.
    See spec Section 7 and Ontology Section 12.4.
    """
    ext = source_path.suffix.lower()
    if ext in (".pptx", ".ppt"):
        return "deck"
    if ext != ".pdf":
        logger.warning("Unrecognized extension '%s', defaulting source_type to 'pdf'", ext)
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
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
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

    Uses line-delimited fence detection: the opening ``---`` must be line 1 and
    the closing ``---`` must appear alone on a subsequent line.  This avoids
    false matches when a YAML scalar contains the substring ``---``.

    Returns the parsed YAML dict, or None if the file doesn't exist,
    doesn't have valid frontmatter, or the parsed content is not a dict.
    """
    if not markdown_path.exists():
        return None
    try:
        content = markdown_path.read_text()
        lines = content.split("\n")
        if not lines or lines[0].strip() != "---":
            return None
        # Find closing fence (standalone --- on its own line)
        end_idx = None
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end_idx = i
                break
        if end_idx is None:
            return None
        yaml_block = "\n".join(lines[1:end_idx])
        result = yaml_lib.safe_load(yaml_block)
        if not isinstance(result, dict):
            return None
        return result
    except (yaml_lib.YAMLError, OSError):
        return None
