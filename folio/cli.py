"""CLI interface for Folio."""

import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click

from .config import FolioConfig
from .converter import FolioConverter, PPTX_EXTENSIONS
from .ingest import IngestAmbiguityError, IngestError, IngestSubtypeMismatchError, ingest_source
from .pipeline.images import ImageExtractionError
from .llm.runtime import EndpointNotAllowedError

logger = logging.getLogger(__name__)


def _matches_scope(path: str, scope: str) -> bool:
    """Check if a path falls under a scope prefix using segment boundaries.

    Normalizes with trailing '/' to prevent prefix collisions:
    'ClientA' must not match 'ClientA2/deck'.
    """
    norm_scope = scope.rstrip("/") + "/"
    return path == scope or path.startswith(norm_scope)


# Restart cadence: preemptive PowerPoint restart every N automated PPTX/PPT conversions.
_RESTART_CADENCE = 15

_HASH_CHUNK_SIZE = 65536


def _content_hash(path: Path) -> str:
    """Streaming SHA-256 of file contents (64 KB chunks)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(_HASH_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _split_csv_values(value: Optional[str]) -> list[str] | None:
    """Split a comma-separated option into a trimmed, deduplicated list."""
    if not value:
        return None

    values: list[str] = []
    seen: set[str] = set()
    for raw in value.split(","):
        cleaned = raw.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        values.append(cleaned)
    return values or None


# AppleScript error codes are 4-digit negative numbers following "error number"
# or "error (" patterns.  We anchor to these patterns to avoid false matches
# on arbitrary negative numbers in unrelated error messages.
_APPLESCRIPT_ERROR_RE = re.compile(r"error\s+(?:number\s+)?(-\d{4,})")


def _configure_logging(verbose: bool) -> None:
    """Configure CLI logging without adding new user-facing flags."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s" if not verbose else "%(name)s: %(message)s",
    )
    third_party_loggers = (
        "pdfminer",
        "pdfplumber",
        "PIL",
        "PIL.PngImagePlugin",
    )
    third_party_level = logging.WARNING if verbose else logging.NOTSET
    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(third_party_level)


@dataclass
class BatchOutcome:
    """Per-file batch outcome record."""
    file_name: str
    renderer: str
    duration: float
    outcome: str  # success | applescript_<code> | timeout | unknown
    slide_count: int = 0


def _classify_outcome(exc: Exception) -> str:
    """Classify an exception into an allowed outcome bucket.

    Stage 1 additions: recognizes oversized image, model API, PDF
    corruption, and rate-limiting failures for better batch reports.
    """
    msg = str(exc).lower()
    exc_type = type(exc).__name__

    # Timeout
    if "timed out" in msg or "timeout" in msg:
        return "timeout"

    # AppleScript error codes (e.g., "error number -9074")
    match = _APPLESCRIPT_ERROR_RE.search(str(exc))
    if match:
        return f"applescript_{match.group(1)}"

    # Stage 1: Oversized image (Pillow MAX_IMAGE_PIXELS or DPI backoff failure)
    if isinstance(exc, ImageExtractionError) and (
        "too large" in msg or "exceeds limit" in msg
    ):
        return "oversized_image"
    if "decompression bomb" in msg or "max_image_pixels" in msg:
        return "oversized_image"

    # Stage 1: Model / LLM API errors
    if any(kw in exc_type.lower() for kw in ("apierror", "apiconnection", "apistatus")):
        return "model_error"
    if any(kw in msg for kw in ("api error", "model not found", "invalid api key")):
        return "model_error"

    # Stage 1: Rate limiting
    if "rate limit" in msg or "429" in msg or "too many requests" in msg:
        return "rate_limited"

    # Stage 1: PDF corruption / rendering failure
    if isinstance(exc, ImageExtractionError):
        # S-2 fix: distinguish dependency/environment errors
        if "not found" in msg or "install" in msg:
            return "missing_dependency"
        return "pdf_render_error"
    if any(kw in msg for kw in ("corrupt", "invalid pdf", "unable to open")):
        return "pdf_corrupt"

    # R4-#4: Provider endpoint blocked / misconfigured
    if isinstance(exc, EndpointNotAllowedError):
        return "endpoint_blocked"

    return "unknown"


def _restart_powerpoint() -> None:
    """Quit and relaunch PowerPoint for fatigue resilience."""
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "Microsoft PowerPoint" to quit'],
            capture_output=True, timeout=10,
        )
    except Exception:
        logger.debug("PowerPoint quit failed (non-fatal)", exc_info=True)
    time.sleep(5)
    try:
        subprocess.run(
            ["open", "-a", "Microsoft PowerPoint"],
            capture_output=True, timeout=10,
        )
    except Exception:
        logger.debug("PowerPoint relaunch failed (non-fatal)", exc_info=True)
    # Wait-for-ready: lightweight AppleScript probe to confirm PowerPoint is responsive.
    try:
        subprocess.run(
            ["osascript", "-e",
             'tell application "Microsoft PowerPoint" to return name'],
            capture_output=True, timeout=10,
        )
    except Exception:
        logger.debug("PowerPoint ready-check timed out (non-fatal)", exc_info=True)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.option("--config", "-c", type=click.Path(), default=None, help="Path to folio.yaml.")
@click.pass_context
def cli(ctx, verbose: bool, config: Optional[str]):
    """Folio: Your consulting portfolio, searchable and AI-ready."""
    _configure_logging(verbose)

    config_path = Path(config) if config else None
    ctx.ensure_object(dict)
    ctx.obj["config"] = FolioConfig.load(config_path)


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("--note", "-n", default=None, help="Version note (e.g. 'Updated per client feedback').")
@click.option("--client", default=None, help="Client name.")
@click.option("--engagement", default=None, help="Engagement identifier.")
@click.option("--target", "-t", type=click.Path(), default=None, help="Override target directory.")
@click.option("--passes", "-p", type=click.IntRange(1, 2), default=None,
              help="Analysis depth: 1=standard, 2=deep (selective second pass on dense slides).")
@click.option("--no-cache", is_flag=True, default=False,
              help="Force re-analysis; fresh results replace cached entries.")
@click.option("--subtype", type=click.Choice(["research", "data_extract", "external_report", "benchmark"]),
              default="research", help="Evidence subtype (default: research).")
@click.option("--industry", default=None, help="Industry tags (comma-separated, e.g. 'retail,ecommerce').")
@click.option("--tags", default=None, help="Manual tags to merge with auto-generated (comma-separated).")
@click.option("--llm-profile", default=None, help="Override LLM profile (defined in folio.yaml).")
@click.pass_context
def convert(ctx, source: str, note: str, client: str, engagement: str, target: str, passes: int, no_cache: bool,
            subtype: str, industry: str, tags: str, llm_profile: str):
    """Convert a single deck to Folio markdown.

    SOURCE is the path to a PPTX or PDF file.

    Examples:

        folio convert deck.pptx

        folio convert deck.pptx --client ClientA --engagement "DD Q1 2026"

        folio convert deck.pptx --note "Updated risk figures"

        folio convert deck.pptx --subtype research --industry "retail,ecommerce" --tags "market-sizing"
    """
    config = ctx.obj["config"]
    converter = FolioConverter(config)

    industry_list = [s.strip() for s in industry.split(",") if s.strip()] if industry else None
    tags_list = [s.strip() for s in tags.split(",") if s.strip()] if tags else None

    try:
        result = converter.convert(
            source_path=Path(source),
            note=note,
            client=client,
            engagement=engagement,
            target=Path(target) if target else None,
            passes=passes,
            no_cache=no_cache,
            subtype=subtype,
            industry=industry_list,
            extra_tags=tags_list,
            llm_profile=llm_profile,
        )
        click.echo(f"✓ {Path(source).name}")
        click.echo(f"  {result.slide_count} slides → {result.output_path}")
        click.echo(f"  Version: {result.version} | ID: {result.deck_id}")

        if result.changes.has_changes and result.version > 1:
            if result.changes.modified:
                click.echo(f"  Modified: slides {', '.join(str(s) for s in result.changes.modified)}")
            if result.changes.added:
                click.echo(f"  Added: slides {', '.join(str(s) for s in result.changes.added)}")
            if result.changes.removed:
                click.echo(f"  Removed: slides {', '.join(str(s) for s in result.changes.removed)}")

        if result.cache_stats and result.cache_stats.total > 0:
            s = result.cache_stats
            click.echo(f"  Cache: {s.hits}/{s.total} hits ({s.hit_rate:.0%})")

    except FileNotFoundError as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Conversion failed: {e}", err=True)
        if ctx.obj.get("verbose"):
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--type",
    "subtype",
    type=click.Choice(["client_meeting", "expert_interview", "internal_sync", "partner_check_in", "workshop"]),
    required=True,
    help="Interaction subtype.",
)
@click.option("--date", "event_date", type=click.DateTime(formats=["%Y-%m-%d"]), required=True, help="Event date (YYYY-MM-DD).")
@click.option("--client", default=None, help="Client name.")
@click.option("--engagement", default=None, help="Engagement identifier.")
@click.option("--participants", default=None, help="Comma-separated participant names.")
@click.option("--duration-minutes", type=click.IntRange(min=1), default=None, help="Meeting duration in minutes.")
@click.option(
    "--source-recording",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional source recording path.",
)
@click.option("--title", default=None, help="Override note title.")
@click.option("--target", type=click.Path(path_type=Path), default=None, help="Override output path or directory.")
@click.option("--llm-profile", default=None, help="Override LLM profile (defined in folio.yaml).")
@click.option("--note", "-n", default=None, help="Version note (e.g. 'Initial ingest from cleaned transcript').")
@click.pass_context
def ingest(
    ctx,
    source: Path,
    subtype: str,
    event_date: datetime,
    client: str,
    engagement: str,
    participants: str,
    duration_minutes: int,
    source_recording: Path,
    title: str,
    target: Path,
    llm_profile: str,
    note: str,
):
    """Ingest a transcript or notes file into an interaction note."""
    if event_date.date() > datetime.now().date():
        raise click.BadParameter("--date cannot be in the future", param_hint="--date")

    config = ctx.obj["config"]
    participant_list = _split_csv_values(participants)

    try:
        result = ingest_source(
            config,
            source_path=source,
            subtype=subtype,
            event_date=event_date.date(),
            client=client,
            engagement=engagement,
            participants=participant_list,
            duration_minutes=duration_minutes,
            source_recording=source_recording,
            title=title,
            target=target,
            llm_profile=llm_profile,
            note=note,
        )
    except (FileNotFoundError, IngestSubtypeMismatchError, IngestAmbiguityError, IngestError) as exc:
        click.echo(f"✗ Ingest failed: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"✗ Ingest failed: {exc}", err=True)
        if ctx.obj.get("verbose"):
            import traceback
            traceback.print_exc()
        sys.exit(1)

    click.echo(f"✓ {source.name}")
    click.echo(f"  {result.output_path}")
    click.echo(
        f"  Version: {result.version} | ID: {result.interaction_id} | Review: {result.review_status}"
    )
    if result.degraded:
        click.echo("  ⚠ analysis unavailable")


@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--pattern", default="*.pptx", help="File glob pattern (default: *.pptx).")
@click.option("--note", "-n", default=None, help="Version note for all conversions.")
@click.option("--client", default=None, help="Client name for all conversions.")
@click.option("--engagement", default=None, help="Engagement identifier for all conversions.")
@click.option("--passes", type=click.IntRange(1, 2), default=None,
              help="Analysis depth: 1=standard, 2=deep (selective second pass on dense slides).")
@click.option("--no-cache", is_flag=True, default=False,
              help="Force re-analysis; fresh results replace cached entries.")
@click.option("--subtype", type=click.Choice(["research", "data_extract", "external_report", "benchmark"]),
              default="research", help="Evidence subtype (default: research).")
@click.option("--industry", default=None, help="Industry tags (comma-separated).")
@click.option("--tags", default=None, help="Manual tags to merge with auto-generated (comma-separated).")
@click.option("--llm-profile", default=None, help="Override LLM profile (defined in folio.yaml).")
@click.option("--dedicated-session/--no-dedicated-session", default=True,
              help="Assume dedicated PowerPoint session (enables restart automation).")
@click.pass_context
def batch(ctx, directory: str, pattern: str, note: str, client: str, engagement: str, passes: int, no_cache: bool,
          subtype: str, industry: str, tags: str, llm_profile: str, dedicated_session: bool):
    """Batch convert all matching files in a directory.

    Automated PPTX conversion (Tier 1):

        folio batch ./materials

        folio batch ./materials --client ClientA

    PDF mitigation for unconvertible files (NOT Tier 1):

        folio batch ./pdfs --pattern "*.pdf" --client ClientA

    \b
    Note: Operator-exported PDFs are mitigation-only and do NOT count
    toward the Tier 1 automated conversion gate.
    """
    config = ctx.obj["config"]
    converter = FolioConverter(config)
    dir_path = Path(directory)

    industry_list = [s.strip() for s in industry.split(",") if s.strip()] if industry else None
    tags_list = [s.strip() for s in tags.split(",") if s.strip()] if tags else None

    files = sorted(dir_path.glob(pattern))
    if not files:
        click.echo(f"No files matching '{pattern}' in {directory}")
        return

    # P0: Content-hash deduplication — skip duplicates and empty files
    seen_hashes: dict[str, Path] = {}  # hash -> first file
    files_to_process: list[Path] = []
    duplicates_skipped = 0
    empty_files_skipped = 0
    for f in files:
        try:
            if os.path.getsize(f) == 0:
                click.echo(f"⚠ {f.name} (empty, skipped)")
                empty_files_skipped += 1
                continue
            h = _content_hash(f)
        except OSError as exc:
            click.echo(f"⚠ {f.name} (read error: {exc}, processing anyway)")
            files_to_process.append(f)
            continue
        first_seen = seen_hashes.get(h)
        if first_seen is not None:
            click.echo(f"⊘ {f.name} (duplicate of {first_seen.name}, skipped)")
            duplicates_skipped += 1
            continue
        seen_hashes[h] = f
        files_to_process.append(f)

    # Classify files into automated PPTX vs PDF mitigation
    is_pdf_batch = bool(files_to_process) and all(
        f.suffix.lower() == ".pdf" for f in files_to_process
    )

    click.echo(f"Converting {len(files_to_process)} files...")
    if is_pdf_batch:
        click.echo("  Mode: PDF mitigation (not Tier 1)")
    click.echo("")

    outcomes: list[BatchOutcome] = []
    pptx_conversion_count = 0  # Track PPTX conversions for restart cadence

    for f in files_to_process:
        is_pptx = f.suffix.lower() in PPTX_EXTENSIONS
        # Config-based fallback for non-NormalizationError failures.
        # NormalizationError carries .renderer_used for accurate reporting.
        renderer_label = config.conversion.pptx_renderer if is_pptx else "pdf-copy"

        # Preemptive restart before PowerPoint fatigue
        if (
            is_pptx
            and dedicated_session
            and pptx_conversion_count > 0
            and pptx_conversion_count % _RESTART_CADENCE == 0
        ):
            click.echo(f"  ↻ Restarting PowerPoint (after {pptx_conversion_count} conversions)")
            _restart_powerpoint()

        start = time.monotonic()
        try:
            result = converter.convert(
                source_path=f,
                note=note,
                client=client,
                engagement=engagement,
                passes=passes,
                no_cache=no_cache,
                subtype=subtype,
                industry=industry_list,
                extra_tags=tags_list,
                llm_profile=llm_profile,
            )
            duration = time.monotonic() - start
            click.echo(f"✓ {f.name} ({result.slide_count} slides, {duration:.1f}s)")
            outcomes.append(BatchOutcome(
                file_name=f.name, renderer=result.renderer_used,
                duration=duration, outcome="success",
                slide_count=result.slide_count,
            ))
            if is_pptx:
                pptx_conversion_count += 1
        except Exception as e:
            duration = time.monotonic() - start
            outcome = _classify_outcome(e)
            # Use actual renderer from NormalizationError if available
            fail_renderer = getattr(e, 'renderer_used', None) or renderer_label

            # Retry-once for unexpected -9074 in dedicated session
            if (
                outcome == "applescript_-9074"
                and is_pptx
                and dedicated_session
            ):
                click.echo(f"  ⚠ {f.name}: -9074, restarting and retrying...")
                _restart_powerpoint()
                retry_start = time.monotonic()
                try:
                    result = converter.convert(
                        source_path=f,
                        note=note,
                        client=client,
                        engagement=engagement,
                        passes=passes,
                        no_cache=no_cache,
                        subtype=subtype,
                        industry=industry_list,
                        extra_tags=tags_list,
                        llm_profile=llm_profile,
                    )
                    retry_duration = time.monotonic() - retry_start
                    click.echo(f"✓ {f.name} (retry succeeded, {retry_duration:.1f}s)")
                    outcomes.append(BatchOutcome(
                        file_name=f.name, renderer=result.renderer_used,
                        duration=retry_duration, outcome="success",
                        slide_count=result.slide_count,
                    ))
                    pptx_conversion_count += 1
                    continue
                except Exception as retry_e:
                    retry_duration = time.monotonic() - retry_start
                    outcome = _classify_outcome(retry_e)
                    retry_renderer = getattr(retry_e, 'renderer_used', None) or renderer_label
                    click.echo(f"✗ {f.name} (retry failed: {outcome}, {retry_duration:.1f}s)")
                    outcomes.append(BatchOutcome(
                        file_name=f.name, renderer=retry_renderer,
                        duration=retry_duration, outcome=outcome,
                    ))
                    if is_pptx:
                        pptx_conversion_count += 1
                    continue

            click.echo(f"✗ {f.name} ({outcome}, {duration:.1f}s)")
            outcomes.append(BatchOutcome(
                file_name=f.name, renderer=fail_renderer,
                duration=duration, outcome=outcome,
            ))
            if is_pptx:
                pptx_conversion_count += 1

    # Summary
    click.echo("")
    pptx_outcomes = [o for o in outcomes if o.renderer != "pdf-copy"]
    pdf_outcomes = [o for o in outcomes if o.renderer == "pdf-copy"]

    pptx_ok = sum(1 for o in pptx_outcomes if o.outcome == "success")
    pptx_fail = len(pptx_outcomes) - pptx_ok
    pdf_ok = sum(1 for o in pdf_outcomes if o.outcome == "success")
    pdf_fail = len(pdf_outcomes) - pdf_ok

    if pptx_outcomes:
        click.echo(f"Automated PPTX: {pptx_ok} succeeded, {pptx_fail} failed")
    if pdf_outcomes:
        click.echo(f"PDF mitigation (not Tier 1): {pdf_ok} succeeded, {pdf_fail} failed")
    if not pptx_outcomes and not pdf_outcomes:
        click.echo("No files processed.")
    click.echo(f"Duplicates skipped: {duplicates_skipped}")
    click.echo(f"Empty files skipped: {empty_files_skipped}")

    # Detail failures
    failures = [o for o in outcomes if o.outcome != "success"]
    if failures:
        click.echo("")
        click.echo("Failures:")
        for o in failures:
            click.echo(f"  ✗ {o.file_name}: {o.outcome} ({o.duration:.1f}s)")
        if any(o.renderer != "pdf-copy" for o in failures):
            click.echo("")
            click.echo(
                "Tip: For files that fail automated conversion, export to PDF manually\n"
                "     (File → Export → PDF, slides only) and run:\n"
                '     folio batch <dir> --pattern "*.pdf"'
            )


@cli.command()
@click.argument("scope", required=False, default=None)
@click.option("--refresh", "do_refresh", is_flag=True, default=False,
              help="Re-check source hashes to update staleness (slower).")
@click.pass_context
def status(ctx, scope: Optional[str], do_refresh: bool):
    """Show library status.

    Optionally scope to a client or engagement:

        folio status

        folio status ClientA

        folio status --refresh
    """
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()

    if not library_root.exists():
        click.echo(f"Library not found at {library_root}")
        click.echo("Run 'folio convert' to create your first conversion.")
        return

    from .tracking import registry

    registry_path = library_root / "registry.json"
    if registry_path.exists():
        data = registry.load_registry(registry_path)
        # B2: detect corrupt registries and rebuild
        if data.get("_corrupt"):
            click.echo("⚠ Registry corrupt — rebuilding from library...")
            data = registry.rebuild_registry(library_root)
            registry.save_registry(registry_path, data)
    else:
        click.echo("Bootstrapping registry from existing library...")
        data = registry.rebuild_registry(library_root)
        registry.save_registry(registry_path, data)

    # Tally staleness counts; only re-hash sources when --refresh is passed
    current = 0
    stale = 0
    missing = 0
    stale_decks = []
    missing_decks = []

    for deck_id, entry_data in data.get("decks", {}).items():
        entry = registry.entry_from_dict(entry_data)

        # Scope filter
        if scope:
            if not (_matches_scope(entry.markdown_path, scope) or
                    _matches_scope(entry.deck_dir, scope)):
                continue

        if do_refresh:
            entry = registry.refresh_entry_status(library_root, entry)
            data["decks"][deck_id] = entry.to_dict()

        if entry.staleness_status == "current":
            current += 1
        elif entry.staleness_status == "stale":
            stale += 1
            stale_decks.append(entry)
        elif entry.staleness_status == "missing":
            missing += 1
            missing_decks.append(entry)

    if do_refresh:
        # Reconcile frontmatter-authoritative fields (B2)
        data = registry.reconcile_from_frontmatter(library_root, data)
        registry.save_registry(registry_path, data)

    # FR-700: tally flagged documents AFTER reconciliation so --refresh
    # picks up manually edited review_status from frontmatter.
    flagged = 0
    flagged_decks = []
    for deck_id, entry_data in data.get("decks", {}).items():
        entry = registry.entry_from_dict(entry_data)
        if scope:
            if not (_matches_scope(entry.markdown_path, scope) or
                    _matches_scope(entry.deck_dir, scope)):
                continue
        if entry_data.get("review_status") == "flagged":
            flagged += 1
            flagged_decks.append(entry)

    total = current + stale + missing
    click.echo(f"Library: {total} documents")
    if flagged:
        click.echo(f"  ! Flagged: {flagged}")
    click.echo(f"  ✓ Current: {current}")
    if stale:
        click.echo(f"  ⚠ Stale: {stale}")
    if missing:
        click.echo(f"  ✗ Missing source: {missing}")

    # Entity count (v0.5.1)
    entities_path = library_root / "entities.json"
    if entities_path.exists():
        try:
            from .tracking.entities import EntityRegistry, EntityRegistryError
            ent_reg = EntityRegistry(entities_path)
            ent_reg.load()
            total_ent = ent_reg.entity_count()
            unconf = ent_reg.unconfirmed_count()
            if total_ent > 0:
                if unconf:
                    click.echo(f"  Entities: {total_ent} ({unconf} unconfirmed)")
                else:
                    click.echo(f"  Entities: {total_ent}")
        except Exception:
            click.echo("  ⚠ entities.json unreadable")

    if flagged_decks:
        click.echo("")
        click.echo("Flagged:")
        for entry in flagged_decks:
            ed = data["decks"].get(entry.id, {})
            flags = ed.get("review_flags", [])
            flags_str = ", ".join(flags) if flags else "(no flags)"
            click.echo(f"  {entry.markdown_path}  [{flags_str}]")

    if stale_decks:
        click.echo("")
        click.echo("Stale:")
        for entry in stale_decks:
            click.echo(f"  {entry.markdown_path}")

    if missing_decks:
        click.echo("")
        click.echo("Missing:")
        for entry in missing_decks:
            click.echo(f"  {entry.markdown_path} (source: {entry.source_relative_path})")


@cli.command()
@click.option("--scope", default=None, help="Limit to sources matching a path prefix.")
@click.pass_context
def scan(ctx, scope: Optional[str]):
    """Scan configured source roots for new, stale, or missing files.

    Examples:

        folio scan

        folio scan --scope ClientA
    """
    config = ctx.obj["config"]

    if not config.sources:
        click.echo("No source roots configured in folio.yaml.")
        click.echo("")
        click.echo("Add sources to folio.yaml:")
        click.echo("  sources:")
        click.echo("    - name: client-materials")
        click.echo("      path: ../client_materials")
        click.echo("      target_prefix: \"\"")
        return

    library_root = config.library_root.resolve()

    from .tracking import registry
    from .tracking.sources import compute_file_hash

    registry_path = library_root / "registry.json"
    if registry_path.exists():
        data = registry.load_registry(registry_path)
        if data.get("_corrupt"):
            click.echo("⚠ Registry corrupt — rebuilding from library...")
            data = registry.rebuild_registry(library_root)
            registry.save_registry(registry_path, data)
    else:
        data = registry.rebuild_registry(library_root)
        registry.save_registry(registry_path, data)

    # Build lookup: resolved_source_path -> registry entry
    source_to_entry = {}
    for entry_data in data.get("decks", {}).values():
        entry = registry.entry_from_dict(entry_data)
        try:
            abs_source = registry.resolve_entry_source(library_root, entry)
            source_to_entry[str(abs_source)] = entry
        except Exception:
            logger.debug("Could not resolve source for %s", entry.id, exc_info=True)

    # Walk source roots
    new_sources = []
    stale_sources = []
    missing_sources = []
    scanned = 0

    from .converter import PPTX_EXTENSIONS
    scan_extensions = PPTX_EXTENSIONS | {".pdf", ".txt", ".md"}

    for src_config, resolved_root in config.resolve_source_roots():
        if not resolved_root.exists():
            click.echo(f"  ⚠ Source root not found: {src_config.name} ({resolved_root})")
            continue

        for source_file in sorted(resolved_root.rglob("*")):
            if not source_file.is_file():
                continue
            if source_file.suffix.lower() not in scan_extensions:
                continue

            # Scope filter
            if scope:
                try:
                    rel = source_file.relative_to(resolved_root)
                    if not _matches_scope(str(rel), scope):
                        continue
                except ValueError:
                    continue

            scanned += 1
            abs_str = str(source_file.resolve())

            if abs_str not in source_to_entry:
                new_sources.append(source_file)
            else:
                entry = source_to_entry[abs_str]
                current_hash = compute_file_hash(source_file)
                if current_hash != entry.source_hash:
                    stale_sources.append((source_file, entry))

    # Check for missing: registry entries whose sources no longer exist
    for entry_data in data.get("decks", {}).values():
        entry = registry.entry_from_dict(entry_data)
        try:
            abs_source = registry.resolve_entry_source(library_root, entry)
            if not abs_source.exists():
                # Scope filter
                if scope and not _matches_scope(entry.markdown_path, scope):
                    continue
                missing_sources.append(entry)
        except Exception:
            logger.debug("Could not resolve source for %s", entry.markdown_path, exc_info=True)

    click.echo(f"Sources scanned: {scanned}")
    click.echo(f"  New: {len(new_sources)}")
    click.echo(f"  Stale: {len(stale_sources)}")
    click.echo(f"  Missing: {len(missing_sources)}")

    if new_sources:
        click.echo("")
        click.echo("New (not yet converted):")
        for f in new_sources:
            click.echo(f"  {f}")

    if stale_sources:
        click.echo("")
        click.echo("Stale (source changed since last conversion):")
        for f, entry in stale_sources:
            click.echo(f"  {f} → {entry.markdown_path}")

    if missing_sources:
        click.echo("")
        click.echo("Missing (source file not found):")
        for entry in missing_sources:
            click.echo(f"  {entry.markdown_path} (source: {entry.source_relative_path})")


@cli.command()
@click.option("--scope", default=None, help="Limit to entries under a library-relative path.")
@click.option("--all", "convert_all", is_flag=True, default=False,
              help="Re-convert all entries in scope, not just stale ones.")
@click.pass_context
def refresh(ctx, scope: Optional[str], convert_all: bool):
    """Re-convert stale documents in the library.

    Examples:

        folio refresh

        folio refresh --scope ClientA/DD_Q1_2026

        folio refresh --all
    """
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()

    if not library_root.exists():
        click.echo(f"Library not found at {library_root}")
        return

    from .tracking import registry

    registry_path = library_root / "registry.json"
    if registry_path.exists():
        data = registry.load_registry(registry_path)
        if data.get("_corrupt"):
            click.echo("⚠ Registry corrupt — rebuilding from library...")
            data = registry.rebuild_registry(library_root)
            registry.save_registry(registry_path, data)
    else:
        click.echo("Bootstrapping registry from existing library...")
        data = registry.rebuild_registry(library_root)
        registry.save_registry(registry_path, data)

    # Select entries to refresh
    entries_to_refresh = []
    skipped_interactions = []
    for deck_id, entry_data in data.get("decks", {}).items():
        entry = registry.entry_from_dict(entry_data)

        # Scope filter
        if scope:
            if not (_matches_scope(entry.markdown_path, scope) or
                    _matches_scope(entry.deck_dir, scope)):
                continue

        if entry.type == "interaction":
            skipped_interactions.append(entry)
            continue

        # Refresh staleness
        entry = registry.refresh_entry_status(library_root, entry)

        if convert_all or entry.staleness_status == "stale":
            entries_to_refresh.append(entry)

    for entry in skipped_interactions:
        click.echo(
            f"↷ {entry.id}: skipping interaction entry, re-run `folio ingest` instead"
        )

    if skipped_interactions:
        click.echo(f"Skipped interaction entries: {len(skipped_interactions)}")

    if not entries_to_refresh:
        click.echo("Nothing to refresh.")
        return

    click.echo(f"Refreshing {len(entries_to_refresh)} document(s)...")
    click.echo("")

    converter = FolioConverter(config)
    from .converter import _read_existing_frontmatter
    success = 0
    failed = 0

    for entry in entries_to_refresh:
        source_path = registry.resolve_entry_source(library_root, entry)
        if not source_path.exists():
            click.echo(f"✗ {entry.id}: source missing ({entry.source_relative_path})")
            failed += 1
            continue

        try:
            # Read existing frontmatter to preserve metadata across refresh
            existing_fm = _read_existing_frontmatter(library_root / entry.markdown_path)

            result = converter.convert(
                source_path=source_path,
                client=entry.client,
                engagement=entry.engagement,
                target=library_root / entry.deck_dir,
                subtype=existing_fm.get("subtype", "research") if existing_fm else "research",
                industry=existing_fm.get("industry") if existing_fm else None,
                extra_tags=existing_fm.get("tags") if existing_fm else None,
            )
            click.echo(f"✓ {entry.id} (v{result.version}, {result.slide_count} slides)")
            success += 1
        except Exception as e:
            click.echo(f"✗ {entry.id}: {e}")
            failed += 1

    click.echo("")
    click.echo(f"Refresh complete: {success} succeeded, {failed} failed")


@cli.command()
@click.argument("deck_id")
@click.argument("level", type=click.Choice(["L1", "L2", "L3"]))
@click.pass_context
def promote(ctx, deck_id: str, level: str):
    """Promote a deck's curation level.

    DECK_ID is the document ID from the registry.
    LEVEL is the target curation level (L1, L2, or L3).

    Examples:

        folio promote clienta_ddq126_evidence_20260310_market-sizing L1
    """
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()

    from .tracking import registry
    from .tracking.versions import append_promotion_event

    registry_path = library_root / "registry.json"
    if not registry_path.exists():
        click.echo("Bootstrapping registry from existing library...")
        data = registry.rebuild_registry(library_root)
        registry.save_registry(registry_path, data)
    else:
        data = registry.load_registry(registry_path)
        # B2: detect corrupt registries and rebuild
        if data.get("_corrupt"):
            click.echo("⚠ Registry corrupt — rebuilding from library...")
            data = registry.rebuild_registry(library_root)
            registry.save_registry(registry_path, data)
    if deck_id not in data.get("decks", {}):
        click.echo(f"✗ Deck '{deck_id}' not found in registry.")
        click.echo("")
        click.echo("Available IDs:")
        for did in sorted(data.get("decks", {}).keys()):
            click.echo(f"  {did}")
        sys.exit(1)

    entry = registry.entry_from_dict(data["decks"][deck_id])
    current_level = entry.curation_level or "L0"

    # Validate transition direction
    level_order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
    if level_order.get(level, 0) <= level_order.get(current_level, 0):
        click.echo(f"✗ Cannot promote from {current_level} to {level} (must go upward).")
        sys.exit(1)

    # Read existing markdown frontmatter for validation
    md_path = library_root / entry.markdown_path
    if not md_path.exists():
        click.echo(f"✗ Markdown file not found: {entry.markdown_path}")
        sys.exit(1)

    from .converter import _read_existing_frontmatter
    fm = _read_existing_frontmatter(md_path)
    if fm is None:
        click.echo(f"✗ Cannot read frontmatter from {entry.markdown_path}")
        sys.exit(1)

    # FR-700: Block promotion of flagged documents
    if fm.get("review_status") == "flagged":
        flags = fm.get("review_flags", [])
        click.echo(f"✗ Cannot promote: document is flagged for review.")
        for f in flags:
            click.echo(f"  - {f}")
        click.echo("")
        click.echo("To resolve: address the flagged issues, then set")
        click.echo("  review_status: reviewed")
        click.echo("in the document's YAML frontmatter.")
        sys.exit(1)
    if fm.get("review_status") is None:
        click.echo("⚠ No review status found (legacy document). "
                    "Re-convert to generate review assessment.")
        click.echo("")

    warnings = []

    # L0 -> L1 validation
    if current_level == "L0" and level in ("L1", "L2", "L3"):
        if not fm.get("client"):
            click.echo(f"✗ L0 → L1 requires 'client' to be populated.")
            sys.exit(1)
        if not fm.get("tags"):
            click.echo(f"✗ L0 → L1 requires 'tags' to be populated.")
            sys.exit(1)
        doc_type = fm.get("type", "")
        engagement_types = {"analysis", "evidence", "deliverable", "interaction"}
        if doc_type in engagement_types and not fm.get("engagement"):
            click.echo(f"✗ L0 → L1 requires 'engagement' for {doc_type}-type documents.")
            sys.exit(1)
        if doc_type == "interaction" and not fm.get("participants"):
            click.echo(f"✗ L0 → L1 requires 'participants' for interaction-type documents.")
            sys.exit(1)

    # L1 -> L2 validation (warning only)
    if current_level == "L1" and level in ("L2", "L3"):
        relationship_fields = [
            "depends_on", "draws_from", "relates_to",
            "supersedes", "instantiates", "impacts",
        ]
        has_relationships = any(
            fm.get(f) for f in relationship_fields
        )
        if not has_relationships:
            warnings.append(
                "No relationship fields found (depends_on, draws_from, etc.). "
                "Consider adding relationships before promoting to L2."
            )

    # Update curation_level in markdown file via targeted string replacement.
    # Avoids full YAML round-trip which corrupts timestamps and strips comments.
    content = md_path.read_text()
    new_content, count = re.subn(
        r"(?m)^curation_level:\s*L\d",
        f"curation_level: {level}",
        content,
        count=1,
    )
    if count == 0:
        click.echo("✗ Cannot find 'curation_level' field in frontmatter.")
        sys.exit(1)

    # Atomic write
    tmp_md = md_path.with_suffix(".md.tmp")
    tmp_md.write_text(new_content)
    tmp_md.rename(md_path)

    # Update registry
    entry.curation_level = level
    data["decks"][deck_id] = entry.to_dict()
    registry.save_registry(registry_path, data)

    # Append promotion event to version_history.json
    deck_dir = library_root / entry.deck_dir
    history_path = deck_dir / "version_history.json"
    from datetime import datetime, timezone
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": "promotion",
        "from_level": current_level,
        "to_level": level,
        "warnings": warnings,
    }
    append_promotion_event(history_path, event)

    click.echo(f"✓ Promoted {deck_id}: {current_level} → {level}")
    for w in warnings:
        click.echo(f"  ⚠ {w}")


# ---------------------------------------------------------------------------
# entities group (v0.5.1)
# ---------------------------------------------------------------------------

_ENTITY_TYPE_LABELS = {
    "person": "People",
    "department": "Departments",
    "system": "Systems",
    "process": "Processes",
}


def _entities_list(ctx, entity_type, unconfirmed, json_output):
    """Default handler: list entities."""
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()
    entities_path = library_root / "entities.json"

    from .tracking.entities import EntityRegistry, EntityRegistryError

    reg = EntityRegistry(entities_path)
    try:
        reg.load()
    except EntityRegistryError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    if reg.entity_count() == 0:
        click.echo("No entities in library.")
        return

    if json_output:
        click.echo(json.dumps(reg._data, indent=2))
        return

    counts = reg.count_by_type()
    types = [entity_type] if entity_type else ["person", "department", "system", "process"]

    for etype in types:
        info = counts.get(etype, {"total": 0, "unconfirmed": 0})
        if info["total"] == 0 and entity_type is None:
            continue
        label = _ENTITY_TYPE_LABELS.get(etype, etype.title())
        header = f"{label} ({info['total']} total"
        if info["unconfirmed"]:
            header += f", {info['unconfirmed']} unconfirmed"
        header += ")"
        click.echo(header)

        for _et, _key, entry in reg.iter_entities(
            entity_type=etype, unconfirmed_only=unconfirmed
        ):
            status = "unconfirmed" if entry.needs_confirmation else "confirmed"
            detail = ""
            if entry.title:
                detail = entry.title
                if entry.department:
                    detail += f", {entry.department}"
            elif entry.department:
                detail = entry.department
            if detail:
                click.echo(f"  {entry.canonical_name:<20s} {detail:<25s} {status}")
            else:
                click.echo(f"  {entry.canonical_name:<20s} {'':25s} {status}")
        click.echo("")


@cli.group(invoke_without_command=True)
@click.option("--type", "entity_type",
              type=click.Choice(["person", "department", "system", "process"]),
              default=None, help="Filter by entity type.")
@click.option("--unconfirmed", is_flag=True, default=False,
              help="Show only unconfirmed entities.")
@click.option("--json", "json_output", is_flag=True, default=False,
              help="Output as JSON.")
@click.pass_context
def entities(ctx, entity_type, unconfirmed, json_output):
    """Manage entities in the library."""
    ctx.ensure_object(dict)
    ctx.obj["entity_type"] = entity_type
    if ctx.invoked_subcommand is None:
        _entities_list(ctx, entity_type, unconfirmed, json_output)


@entities.command()
@click.argument("name")
@click.pass_context
def show(ctx, name):
    """Show detail for a single entity."""
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()
    entities_path = library_root / "entities.json"
    entity_type = ctx.obj.get("entity_type")

    from .tracking.entities import EntityRegistry, EntityRegistryError, EntityAmbiguousError

    reg = EntityRegistry(entities_path)
    try:
        reg.load()
    except EntityRegistryError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    matches = reg.lookup(name, entity_type=entity_type)

    if len(matches) == 0:
        click.echo(f"No entity found matching '{name}'.")
        sys.exit(1)

    if len(matches) > 1:
        click.echo(f"Multiple matches for \"{name}\":")
        for i, (etype, key, entry) in enumerate(matches, 1):
            click.echo(f"  {i}. {entry.canonical_name} ({etype}) — canonical name")
        click.echo("")
        click.echo("Use --type to disambiguate:")
        click.echo(f"  folio entities --type {matches[0][0]} show \"{name}\"")
        return

    etype, key, entry = matches[0]
    status = "confirmed" if not entry.needs_confirmation else "unconfirmed"
    click.echo(f"{entry.canonical_name} ({etype}) {status}")
    if entry.title:
        click.echo(f"  Title:       {entry.title}")
    if entry.department:
        click.echo(f"  Department:  {entry.department}")
    if entry.reports_to:
        click.echo(f"  Reports to:  {entry.reports_to}")
    if entry.aliases:
        click.echo(f"  Aliases:     {', '.join(entry.aliases)}")
    if entry.client:
        click.echo(f"  Client:      {entry.client}")
    if entry.head:
        click.echo(f"  Head:        {entry.head}")
    if entry.owner_dept:
        click.echo(f"  Owner dept:  {entry.owner_dept}")
    click.echo(f"  Source:      {entry.source}")
    if entry.first_seen:
        click.echo(f"  First seen:  {entry.first_seen[:10]}")
    if entry.created_at:
        click.echo(f"  Created:     {entry.created_at[:10]}")

    # Mentioned in: scan library markdown files
    mention_count = 0
    wikilink = f"[[{entry.canonical_name}]]"
    for md_file in library_root.rglob("*.md"):
        try:
            if wikilink in md_file.read_text():
                mention_count += 1
        except OSError:
            pass
    click.echo(f"  Mentioned in: {mention_count} interaction notes")


@entities.command("import")
@click.argument("csv_file", type=click.Path(exists=True))
@click.pass_context
def import_cmd(ctx, csv_file):
    """Import entities from a CSV org chart file."""
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()
    entities_path = library_root / "entities.json"

    from .tracking.entities import EntityRegistry, EntityRegistryError
    from .entity_import import import_csv

    reg = EntityRegistry(entities_path)
    try:
        reg.load()
    except EntityRegistryError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    try:
        result = import_csv(reg, Path(csv_file))
    except (ValueError, OSError) as e:
        click.echo(f"✗ Import failed: {e}", err=True)
        sys.exit(1)

    parts = []
    if result.people_imported:
        parts.append(f"Imported {result.people_imported} people")
    if result.people_updated:
        parts.append(f"Updated {result.people_updated} people")
    if result.people_skipped:
        parts.append(f"Skipped {result.people_skipped} people (no changes)")
    if result.departments_created:
        parts.append(f"Created {result.departments_created} departments")

    if parts:
        click.echo("✓ " + ", ".join(parts) + ".")
    else:
        click.echo("No entities imported.")

    for w in result.warnings:
        click.echo(f"  ⚠ {w}")


@entities.command()
@click.argument("name")
@click.pass_context
def confirm(ctx, name):
    """Confirm an unconfirmed entity."""
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()
    entities_path = library_root / "entities.json"
    entity_type = ctx.obj.get("entity_type")

    from .tracking.entities import (
        EntityRegistry, EntityRegistryError, EntityAmbiguousError,
    )

    reg = EntityRegistry(entities_path)
    try:
        reg.load()
    except EntityRegistryError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    try:
        match = reg.lookup_unique(name, entity_type=entity_type)
    except EntityAmbiguousError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    if match is None:
        click.echo(f"✗ No entity found matching '{name}'.", err=True)
        sys.exit(1)

    etype, key, entry = match
    if not entry.needs_confirmation:
        click.echo(f"Already confirmed: {entry.canonical_name} ({etype})")
        return

    reg.confirm_entity(etype, key)
    reg.save()
    click.echo(f"Confirmed: {entry.canonical_name} ({etype})")


@entities.command()
@click.argument("name")
@click.pass_context
def reject(ctx, name):
    """Reject an unconfirmed entity."""
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()
    entities_path = library_root / "entities.json"
    entity_type = ctx.obj.get("entity_type")

    from .tracking.entities import (
        EntityRegistry, EntityRegistryError, EntityAmbiguousError,
    )

    reg = EntityRegistry(entities_path)
    try:
        reg.load()
    except EntityRegistryError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    try:
        match = reg.lookup_unique(name, entity_type=entity_type)
    except EntityAmbiguousError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    if match is None:
        click.echo(f"✗ No entity found matching '{name}'.", err=True)
        sys.exit(1)

    etype, key, entry = match
    if not entry.needs_confirmation:
        click.echo(
            f"✗ Cannot reject confirmed entity. "
            f"Edit entities.json directly to remove confirmed entities.",
            err=True,
        )
        sys.exit(1)

    reg.remove_entity(etype, key)
    reg.save()
    click.echo(f"Rejected and removed: {entry.canonical_name} ({etype})")


def main():
    """Entry point."""
    cli()
