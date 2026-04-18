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


class ScopeOrCommandGroup(click.Group):
    """Click group that accepts either a subcommand or a bare scope argument.

    v1.2 extension (folio-enrich-diagnose CB-2 closure): handles BOTH
    bare-positional-first (`folio enrich ClientA`) AND option-before-scope
    (`folio enrich --dry-run ClientA`) forms by walking args, recognizing
    Click option-with-value pairs, and rewriting the FIRST non-option,
    non-subcommand token as `--scope X` regardless of position.

    v1.3 extension (folio-enrich-diagnose CB-2 final closure): once a
    registered subcommand token is encountered, the parser passes the
    subcommand token AND all remaining tokens verbatim — no further
    `--scope` rewrites. Prevents subcommand positional args from being
    rewritten to group-level `--scope`.
    """

    def parse_args(self, ctx, args):
        # Determine which group-level options take a value (so their value
        # token is not mistaken for a positional scope).
        value_taking_short = set()
        value_taking_long = set()
        for param in self.params:
            if isinstance(param, click.Option) and not param.is_flag and not param.count:
                for opt in param.opts:
                    if opt.startswith("--"):
                        value_taking_long.add(opt)
                    elif opt.startswith("-"):
                        value_taking_short.add(opt)

        new_args: list[str] = []
        rewrote = False
        skip_next = False
        saw_subcommand = False
        i = 0
        while i < len(args):
            arg = args[i]
            if saw_subcommand:
                # v1.3 closure: pass subcommand args verbatim (do NOT rewrite
                # the subcommand's positional scope to group-level --scope).
                new_args.extend(args[i:])
                break
            if skip_next:
                new_args.append(arg)
                skip_next = False
                i += 1
                continue
            if arg.startswith("-"):
                new_args.append(arg)
                opt_name = arg.split("=", 1)[0]
                if "=" not in arg and (
                    opt_name in value_taking_long or opt_name in value_taking_short
                ):
                    skip_next = True
                i += 1
                continue
            # Non-option token
            if rewrote:
                new_args.append(arg)
                i += 1
                continue
            if self.get_command(ctx, arg) is not None:
                # Registered subcommand; pass through and stop rewriting.
                new_args.append(arg)
                saw_subcommand = True
                i += 1
            else:
                # Treat as scope. Rewrite to --scope X.
                new_args.extend(["--scope", arg])
                rewrote = True
                i += 1
        return super().parse_args(ctx, new_args)


def _matches_scope(path: str, scope: str) -> bool:
    """Check if a path falls under a scope prefix using segment boundaries.

    Normalizes with trailing '/' to prevent prefix collisions:
    'ClientA' must not match 'ClientA2/deck'.
    """
    norm_scope = scope.rstrip("/") + "/"
    return path == scope or path.startswith(norm_scope)


# Enrich/provenance relationship fields for D12/PR D passthrough
_ENRICH_RELATIONSHIP_FIELDS = (
    "depends_on", "draws_from", "impacts",
    "relates_to", "supersedes", "instantiates",
)

_ENRICH_FINGERPRINT_FIELDS = (
    "input_fingerprint", "managed_body_fingerprint",
    "entity_resolution_fingerprint", "relationship_context_fingerprint",
)


def _extract_enrich_passthrough(fm: dict) -> dict | None:
    """Extract enrich/provenance passthrough fields from existing frontmatter.

    Returns a dict suitable for ``preserved_enrich_fields`` parameter,
    or None if nothing to preserve.
    """
    if not isinstance(fm, dict):
        return None

    result: dict = {}

    # Preserve canonical relationship fields (human-owned)
    for field_name in _ENRICH_RELATIONSHIP_FIELDS:
        if field_name in fm:
            result[field_name] = fm[field_name]

    if "provenance_links" in fm:
        result["provenance_links"] = fm["provenance_links"]

    # Preserve _llm_metadata.enrich / provenance / links
    llm_meta = fm.get("_llm_metadata")
    if isinstance(llm_meta, dict):
        metadata: dict = {}
        if isinstance(llm_meta.get("enrich"), dict):
            metadata["enrich"] = dict(llm_meta["enrich"])
        if isinstance(llm_meta.get("provenance"), dict):
            metadata["provenance"] = dict(llm_meta["provenance"])
        if isinstance(llm_meta.get("links"), dict):
            metadata["links"] = dict(llm_meta["links"])
        if metadata:
            result["_llm_metadata"] = metadata

    if not result:
        return None

    return result


def _mark_enrich_stale(preserved: dict) -> None:
    """Mark enrich/provenance metadata stale when source hash changes.

    Clears enrich fingerprints/proposals and provenance pair cache while
    preserving human-owned canonical relationships and links.
    """
    enrich = preserved.get("_llm_metadata", {}).get("enrich")
    if enrich:
        enrich["status"] = "stale"

        # Clear fingerprints
        for fp_field in _ENRICH_FINGERPRINT_FIELDS:
            enrich.pop(fp_field, None)

        # Clear relationship proposals
        axes = enrich.get("axes")
        if isinstance(axes, dict):
            relationships = axes.get("relationships")
            if isinstance(relationships, dict):
                relationships.pop("proposals", None)

    provenance = preserved.get("_llm_metadata", {}).get("provenance")
    if isinstance(provenance, dict):
        pairs = provenance.get("pairs")
        if isinstance(pairs, dict):
            for pair in pairs.values():
                if not isinstance(pair, dict):
                    continue
                pair.pop("pair_fingerprint", None)
                pair.pop("repair_error", None)
                pair.pop("repair_error_detail", None)
                pair.pop("re_evaluate_requested", None)
                proposals = pair.get("proposals")
                if isinstance(proposals, list):
                    for proposal in proposals:
                        if not isinstance(proposal, dict):
                            continue
                        state = proposal.get("lifecycle_state")
                        if state is None:
                            state = proposal.get("status")
                        if state in ("queued", "pending_human_confirmation"):
                            proposal["lifecycle_state"] = "stale_pending"


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
    if "config" not in ctx.obj:
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

    # Per-type summary when multiple types exist
    type_counts: dict[str, int] = {}
    for _deck_id, _entry_data in data.get("decks", {}).items():
        _entry = registry.entry_from_dict(_entry_data)
        if scope:
            if not (_matches_scope(_entry.markdown_path, scope) or
                    _matches_scope(_entry.deck_dir, scope)):
                continue
        t = _entry.type or "evidence"
        type_counts[t] = type_counts.get(t, 0) + 1
    if len(type_counts) > 1:
        parts = ", ".join(f"{t} {c}" for t, c in sorted(type_counts.items()))
        click.echo(f"  By type: {parts}")

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
            if entry.source_relative_path:
                click.echo(f"  {entry.markdown_path} (source: {entry.source_relative_path})")
            else:
                click.echo(f"  {entry.markdown_path} (note file missing)")


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
        # Skip source-less managed docs (e.g., context)
        if entry.source_relative_path is None:
            continue
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
        # Skip source-less managed docs
        if entry.source_relative_path is None:
            continue
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
            if entry.source_relative_path:
                click.echo(f"  {entry.markdown_path} (source: {entry.source_relative_path})")
            else:
                click.echo(f"  {entry.markdown_path} (note file missing)")


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
    from .lock import LibraryLockError, library_lock

    try:
        with library_lock(library_root, "refresh"):
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
            skipped_context = []
            skipped_analysis = []
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

                if entry.type == "context":
                    skipped_context.append(entry)
                    continue

                if entry.type == "analysis":
                    skipped_analysis.append(entry)
                    continue

                # Refresh staleness
                entry = registry.refresh_entry_status(library_root, entry)

                if convert_all or entry.staleness_status == "stale":
                    entries_to_refresh.append(entry)

            for entry in skipped_context:
                click.echo(
                    f"↷ {entry.id}: skipping context document (human-authored, no source to refresh)"
                )

            if skipped_context:
                click.echo(f"Skipped context entries: {len(skipped_context)}")

            for entry in skipped_analysis:
                if entry.subtype == "digest":
                    click.echo(
                        f"↷ {entry.id}: skipping digest (source-less); rerun `folio digest` instead"
                    )
                else:
                    click.echo(
                        f"↷ {entry.id}: skipping analysis document (source-less); rerun the originating analysis workflow instead"
                    )

            if skipped_analysis:
                click.echo(f"Skipped analysis entries: {len(skipped_analysis)}")

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

                    # Refresh preserves canonical relationship and provenance
                    # fields in frontmatter, but regenerates the note body.
                    preserved = _extract_enrich_passthrough(existing_fm) if existing_fm else None

                    # If source changed (stale entry), mark enrich/provenance stale
                    if preserved and entry.staleness_status == "stale":
                        _mark_enrich_stale(preserved)

                    result = converter.convert(
                        source_path=source_path,
                        client=entry.client,
                        engagement=entry.engagement,
                        target=library_root / entry.deck_dir,
                        subtype=existing_fm.get("subtype", "research") if existing_fm else "research",
                        industry=existing_fm.get("industry") if existing_fm else None,
                        extra_tags=existing_fm.get("tags") if existing_fm else None,
                        preserved_enrich_fields=preserved,
                    )
                    click.echo(f"✓ {entry.id} (v{result.version}, {result.slide_count} slides)")
                    success += 1
                except Exception as e:
                    click.echo(f"✗ {entry.id}: {e}")
                    failed += 1

            click.echo("")
            click.echo(f"Refresh complete: {success} succeeded, {failed} failed")
    except LibraryLockError as e:
        click.echo(f"✗ {e}")
        sys.exit(1)


@cli.group(cls=ScopeOrCommandGroup, invoke_without_command=True)
@click.option("--scope", default=None, hidden=True)
@click.option("--dry-run", is_flag=True, default=False,
              help="Show what would happen without writing files or calling LLM APIs.")
@click.option("--llm-profile", default=None,
              help="Override LLM profile (defined in folio.yaml).")
@click.option("--force", is_flag=True, default=False,
              help="Bypass fingerprint skip; still respects body protection rules.")
@click.pass_context
def enrich(ctx, scope, dry_run, llm_profile, force):
    """Enrich existing evidence and interaction notes with tags, entities, and relationships.

    Subcommands: diagnose (read-only enrichability health check).

    Examples:

        folio enrich

        folio enrich ClientA

        folio enrich ClientA/DD_Q1_2026 --dry-run

        folio enrich --llm-profile anthropic_sonnet --force

        folio enrich diagnose ClientA/DD_Q1_2026

        folio enrich diagnose --json --limit 50
    """
    if ctx.invoked_subcommand is not None:
        return  # delegate to subcommand (e.g. `enrich diagnose`)

    config = ctx.obj["config"]

    from .enrich import enrich_batch
    from .lock import LibraryLockError

    try:
        result = enrich_batch(
            config,
            scope=scope,
            dry_run=dry_run,
            llm_profile=llm_profile,
            force=force,
            echo=click.echo,
        )
    except LibraryLockError as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"✗ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Fatal error: {e}")
        logger.exception("Enrich fatal error")
        sys.exit(1)

    # PROD-SF-006: enrich → diagnose breadcrumb when notes stalled.
    # DSF-002 closure (D.4): shlex.quote scope to prevent shell-injection
    #   if a malicious scope token contains backticks etc.
    # PROD-DSF-001 closure (D.4): branch on scope presence to avoid the
    #   trailing-space-inside-backticks rendering when scope=None.
    if result.protected + result.conflicted > 0:
        import shlex
        if scope:
            quoted = shlex.quote(scope)
            tip = f"  Tip: run `folio enrich diagnose {quoted}`"
        else:
            tip = "  Tip: run `folio enrich diagnose`"
        click.echo(tip + " to see why these notes stalled.")

    if result.failed > 0:
        sys.exit(1)


# v1.0.0 diagnose CLI: BEGIN  (CB-4 firewall marker)
@enrich.command("diagnose")
@click.argument("scope", required=False, default=None)
@click.option("--json", "json_output", is_flag=True, default=False,
              help="Emit findings as a JSON envelope (schema_version 1.0).")
@click.option("--limit", type=click.IntRange(min=1), default=None,
              help="Cap rendered findings (post-sort). Default unbounded.")
@click.pass_context
def enrich_diagnose_cmd(ctx, scope, json_output, limit):
    """Identify evidence and interaction notes whose managed sections cannot be safely updated by `folio enrich`.

    Read-only diagnostic — never writes notes, frontmatter, or registry.

    Examples:

        folio enrich diagnose

        folio enrich diagnose ClientA/DD_Q1_2026

        folio enrich diagnose ClientA/DD_Q1_2026 --limit 10

        folio enrich diagnose --json

        folio enrich diagnose --json --limit 25

    Notes: Findings on flagged notes are annotated with `[flagged]` inside
    the severity bracket (e.g., `[error [flagged]]`). Diagnose surfaces
    flagged notes by design — it is a diagnostic surface, not a discovery
    surface; the discovery-surface flag for including flagged inputs (used
    by sibling commands like `folio digest` and `folio search`) does not
    apply to diagnose.
    """
    config = ctx.obj["config"]
    from .enrich import diagnose_notes, ScopeResolutionError
    try:
        result = diagnose_notes(config, scope=scope, limit=limit)
    except ScopeResolutionError as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"✗ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Fatal error: {e}")
        logger.exception("Enrich diagnose fatal error")
        sys.exit(1)

    if json_output:
        click.echo(_render_diagnose_json(result))
    else:
        _render_diagnose_text(result, click.echo)
# v1.0.0 diagnose CLI: END  (CB-4 firewall marker)


def _render_diagnose_text(result, echo) -> None:
    """Render DiagnoseResult as human-readable text per spec §4.3.

    DCB-1 closure (D.4): emits "showing N of M" using result.unfiltered_total.
    DCSF-1 / PROD-DSF-002 closure (D.4): pluralization-aware summary line.
    """
    if not result.findings:
        echo("No enrichment hygiene findings.")
        return

    for finding in result.findings:
        suffix = " [flagged]" if finding.trust_status == "flagged" else ""
        echo(
            f"[{finding.severity}{suffix}] {finding.code} "
            f"{finding.subject_id}: {finding.detail}"
        )
        echo(f"  Action: {finding.recommended_action}")

    if result.truncated:
        # DCB-1 closure: emit actual unfiltered total (M), not "more".
        echo(
            f"... (showing {result.summary.total} of {result.unfiltered_total}; "
            f"raise --limit to see more)"
        )

    by_severity: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
    for f in result.findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
    parts = []
    for sev in ("error", "warning", "info"):
        n = by_severity.get(sev, 0)
        if n:
            # PROD-DSF-002 / PEER-DSF-004 closure: per-severity pluralization.
            parts.append(f"{n} {sev}{'s' if n != 1 else ''}")
    flagged_part = (
        f" ({result.summary.flagged_total} flagged)"
        if result.summary.flagged_total
        else ""
    )
    # PROD-DSF-002 closure: total pluralization.
    total_noun = "finding" if result.summary.total == 1 else "findings"
    echo("")
    echo(
        f"{result.summary.total} {total_noun}{flagged_part}: "
        + ", ".join(parts)
        + "."
    )


def _render_diagnose_json(result) -> str:
    """Render DiagnoseResult as the §7 JSON envelope (schema_version 1.0).

    DCB-1 closure (D.4): summary.unfiltered_total exposed in the JSON
    envelope so consumers can compute the truncation gap (M - N).
    """
    payload = {
        "schema_version": result.schema_version,
        "command": result.command,
        "scope": result.scope,
        "limit": result.limit,
        "findings": [
            {
                "code": f.code,
                "severity": f.severity,
                "subject_id": f.subject_id,
                "detail": f.detail,
                "recommended_action": f.recommended_action,
                "trust_status": f.trust_status,
            }
            for f in result.findings
        ],
        "summary": {
            "total": result.summary.total,
            "by_code": dict(result.summary.by_code),
            "flagged_total": result.summary.flagged_total,
            "unfiltered_total": result.unfiltered_total,
        },
        "truncated": result.truncated,
    }
    return json.dumps(payload, indent=2)


@cli.group(cls=ScopeOrCommandGroup, invoke_without_command=True)
@click.option("--scope", default=None, hidden=True)
@click.option("--date", "date_str", default=None,
              help="Digest date (YYYY-MM-DD); default local today.")
@click.option("--week", "week_mode", is_flag=True, default=False,
              help="Generate weekly digest for the ISO week containing --date.")
@click.option("--include-flagged", is_flag=True, default=False,
              help="Include source-backed inputs whose review_status is flagged "
                   "(daily mode only; no-op in --week).")
@click.option("--llm-profile", default=None,
              help="Override routing.digest for this invocation.")
@click.pass_context
def digest(ctx, scope: Optional[str], date_str: Optional[str], week_mode: bool,
           include_flagged: bool, llm_profile: Optional[str]):
    """Generate a daily or weekly digest for a single engagement scope.

    Examples:

        folio digest ClientA/DD_Q1_2026

        folio digest ClientA/DD_Q1_2026 --date 2026-04-04

        folio digest ClientA/DD_Q1_2026 --week --date 2026-04-04

        folio digest ClientA/DD_Q1_2026 --include-flagged

    Re-run after upstream notes change to refresh the digest.
    """
    if ctx.invoked_subcommand is not None:
        return
    if scope is None:
        raise click.UsageError(
            "scope is required (e.g. `folio digest ClientA/DD_Q1_2026`)"
        )

    config = ctx.obj["config"]
    from . import digest as digest_module
    from .lock import library_lock, LibraryLockError

    fn = digest_module.generate_weekly_digest if week_mode else digest_module.generate_daily_digest

    try:
        with library_lock(config.library_root, "digest"):
            result = fn(
                config,
                scope=scope,
                date=date_str,
                include_flagged=include_flagged,
                llm_profile=llm_profile,
            )
    except LibraryLockError as e:
        click.echo(f"✗ {e}")
        ctx.exit(1)

    _emit_digest_result(result, week_mode=week_mode, include_flagged=include_flagged)
    ctx.exit(result.exit_code)


def _emit_digest_result(result, *, week_mode: bool, include_flagged: bool) -> None:
    """Render DigestResult to stdout per spec §4 + §13.

    Owns three-branch pluralization (SF-12), `✓`/`✗` prefixes (SF-13),
    `--week --include-flagged` advisory (SF-14), `--include-flagged` echo
    on empty results (SF-15), success+override echo (MN-9 / SF-107).
    """
    if result.status == "error":
        click.echo(f"✗ {result.message}")
        return

    if result.status == "empty":
        click.echo(result.message)
        if week_mode and include_flagged:
            click.echo(
                "Note: --include-flagged has no effect in --week mode; "
                "weekly inputs are existing daily digests, which are "
                "already filtered at write time."
            )
        return

    # status == "written" or "rerun"
    click.echo(f"✓ {result.message}")
    if result.path is not None:
        click.echo(f"  Path: {result.path}")

    n = result.draws_from_count
    if week_mode:
        noun = "daily digest" if n == 1 else "daily digests"
    else:
        noun = "input" if n == 1 else "inputs"

    suffix = ""
    if not week_mode and include_flagged and result.flagged_counts.included > 0:
        m = result.flagged_counts.included
        flagged_noun = "flagged input" if m == 1 else "flagged inputs"
        suffix = f" (--include-flagged honored; {m} {flagged_noun} included)"

    click.echo(f"  Drawn from {n} {noun}{suffix}.")

    if week_mode and include_flagged:
        click.echo(
            "Note: --include-flagged has no effect in --week mode; "
            "weekly inputs are existing daily digests, which are "
            "already filtered at write time."
        )


@cli.group(cls=ScopeOrCommandGroup, invoke_without_command=True)
@click.option("--scope", default=None, hidden=True)
@click.option("--dry-run", is_flag=True, default=False,
              help="Show what would happen without writing files or calling LLM APIs.")
@click.option("--llm-profile", default=None,
              help="Override LLM profile (defined in folio.yaml).")
@click.option("--limit", type=int, default=None,
              help="Maximum number of source-target pairs to evaluate.")
@click.option("--force", is_flag=True, default=False,
              help="Bypass pair fingerprint skips.")
@click.option("--clear-rejections", is_flag=True, default=False,
              help="Clear stored rejection bases in scope. Requires --force.")
@click.pass_context
def provenance(ctx, scope: Optional[str], dry_run: bool, llm_profile: Optional[str], limit: Optional[int], force: bool, clear_rejections: bool):
    """Generate and manage claim-level provenance links."""
    if ctx.invoked_subcommand is not None:
        return

    config = ctx.obj["config"]
    from .lock import LibraryLockError
    from .provenance import provenance_batch

    try:
        result = provenance_batch(
            config,
            scope=scope,
            dry_run=dry_run,
            llm_profile=llm_profile,
            limit=limit,
            force=force,
            clear_rejections=clear_rejections,
            echo=click.echo,
        )
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Fatal error: {e}")
        logger.exception("Provenance fatal error")
        sys.exit(1)

    if result.failed > 0:
        sys.exit(1)


@provenance.command("review")
@click.argument("scope", required=False, default=None)
@click.option("--include-low", is_flag=True, default=False,
              help="Include low-confidence pending proposals.")
@click.option("--stale", "stale_only", is_flag=True, default=False,
              help="Show stale / repair-needed confirmed links instead of pending proposals.")
@click.option("--doc", "doc_id", default=None,
              help="Filter to a single source document ID.")
@click.option("--target", "target_id", default=None,
              help="Filter to a single target document ID.")
@click.option("--page", type=int, default=1,
              help="1-based review page number.")
@click.pass_context
def provenance_review_cmd(ctx, scope: Optional[str], include_low: bool, stale_only: bool, doc_id: Optional[str], target_id: Optional[str], page: int):
    """Read-only review surface for pending or stale provenance items."""
    from .provenance import PAGE_SIZE, collect_pending_proposals, collect_stale_links, paginate

    config = ctx.obj["config"]
    page = max(1, page)

    if stale_only:
        rows = collect_stale_links(config, scope=scope, doc_id=doc_id, target_id=target_id)
        window, total_pages = paginate(rows, page)
        click.echo(f"Stale Review ({len(rows)} item(s))")
        click.echo(
            f"Page {page}/{total_pages} ({len(window)} items, page size {PAGE_SIZE}, ordered: source doc → surfaced state → link_id)"
        )
        for row in window:
            link = row.link
            state = row.state
            orphan = " ORPHANED" if row.orphaned else ""
            click.echo(
                f"[{link.get('link_id')}] {row.source_id} -> {row.target_id} "
                f"slide {link.get('source_slide')}, claim {link.get('source_claim_index')} "
                f"-> slide {link.get('target_slide')}, claim {link.get('target_claim_index')} "
                f"({state}{orphan})"
            )
        return

    proposals = collect_pending_proposals(
        config,
        scope=scope,
        doc_id=doc_id,
        target_id=target_id,
        include_low=include_low,
    )
    window, total_pages = paginate(proposals, page)
    click.echo(f"Pending ({len(proposals)} item(s))")
    click.echo(
        f"Page {page}/{total_pages} ({len(window)} items, page size {PAGE_SIZE}, ordered: source doc → confidence desc → proposal_id)"
    )
    for view in window:
        proposal = view.proposal
        source_claim = proposal.source_claim
        target_evidence = proposal.target_evidence
        click.echo(
            f"[{proposal.proposal_id}] "
            f"{view.source_id} slide {source_claim.get('slide_number')}, claim {source_claim.get('claim_index')} "
            f"-> {view.target_id} slide {target_evidence.get('slide_number')}, claim {target_evidence.get('claim_index')} "
            f"({proposal.confidence})"
        )
        click.echo(f"  Claim: {json.dumps(source_claim.get('claim_text', ''), ensure_ascii=False)}")
        click.echo(f"  Evidence: {json.dumps(target_evidence.get('claim_text', ''), ensure_ascii=False)}")
        click.echo(f"  Confidence: {proposal.confidence} | Rationale: {proposal.rationale or '-'}")
        click.echo(f"  Replaces: {proposal.replaces_link_id or '-'}")


@provenance.command("status")
@click.argument("scope", required=False, default=None)
@click.pass_context
def provenance_status_cmd(ctx, scope: Optional[str]):
    """Summarize provenance coverage and repair state."""
    from .provenance import provenance_status_summary

    config = ctx.obj["config"]
    rows = provenance_status_summary(config, scope=scope)
    if not rows:
        click.echo("No provenance data found.")
        return

    total_pairs = 0
    total_claims = 0
    total_pending = 0
    total_confirmed = 0
    total_fresh = 0
    total_stale = 0
    total_ack = 0
    total_re_eval = 0
    total_blocked = 0
    total_orphaned = 0
    total_rejected = 0
    coverage_num = 0
    click.echo("| Source Document | Pairs | Claims | Pending | Fresh | Stale | Ack'd | Re-eval Pending | Blocked | Orphaned | Rejected |")
    click.echo("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        total_pairs += row["pairs"]
        total_claims += row["claims"]
        total_pending += row["pending"]
        total_confirmed += row["fresh"] + row["stale"] + row["acknowledged"] + row["re_evaluate_pending"] + row["blocked"]
        total_fresh += row["fresh"]
        total_stale += row["stale"]
        total_ack += row["acknowledged"]
        total_re_eval += row["re_evaluate_pending"]
        total_blocked += row["blocked"]
        total_orphaned += row["orphaned"]
        total_rejected += row["rejected"]
        coverage_num += row["coverage_numerator"]
        click.echo(
            f"| {row['source_id']} | {row['pairs']} | {row['claims']} | {row['pending']} | "
            f"{row['fresh']} | {row['stale']} | {row['acknowledged']} | "
            f"{row['re_evaluate_pending']} | {row['blocked']} | {row['orphaned']} | {row['rejected']} |"
        )
    coverage_pct = (coverage_num / total_claims * 100.0) if total_claims else 0.0
    click.echo("")
    click.echo(
        f"Total: {total_pairs} pairs, {total_claims} claims, {total_pending} pending, "
        f"{total_confirmed} confirmed"
    )
    click.echo(
        f"       ({total_fresh} fresh, {total_stale} stale, {total_ack} acknowledged, "
        f"{total_re_eval} re-evaluate pending, {total_blocked} blocked, {total_orphaned} orphaned), "
        f"{total_rejected} rejected"
    )
    click.echo(f"Coverage: {coverage_num}/{total_claims} claims have fresh confirmed provenance ({coverage_pct:.1f}%)")


@provenance.command("confirm")
@click.argument("proposal_id")
@click.pass_context
def provenance_confirm_cmd(ctx, proposal_id: str):
    """Confirm one pending provenance proposal."""
    from .lock import LibraryLockError, library_lock
    from .provenance import confirm_proposal

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "provenance"):
            link_id = confirm_proposal(config, proposal_id)
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Confirmed {proposal_id} -> {link_id}")


@provenance.command("reject")
@click.argument("proposal_id")
@click.pass_context
def provenance_reject_cmd(ctx, proposal_id: str):
    """Reject one pending provenance proposal."""
    from .lock import LibraryLockError, library_lock
    from .provenance import reject_proposal

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "provenance"):
            reject_proposal(config, proposal_id)
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Rejected {proposal_id}")


def _ordered_pending_ids(config, scope=None, doc_id=None, target_id=None):
    from .provenance import collect_pending_proposals

    proposals = collect_pending_proposals(
        config,
        scope=scope,
        doc_id=doc_id,
        target_id=target_id,
        include_low=True,
    )
    return [view.proposal.proposal_id for view in proposals]


@provenance.command("confirm-range")
@click.argument("proposal_range")
@click.argument("scope", required=False, default=None)
@click.option("--doc", "doc_id", default=None)
@click.option("--target", "target_id", default=None)
@click.pass_context
def provenance_confirm_range_cmd(ctx, proposal_range: str, scope: Optional[str], doc_id: Optional[str], target_id: Optional[str]):
    """Confirm a contiguous range in the deterministic pending ordering."""
    from .lock import LibraryLockError, library_lock
    from .provenance import confirm_range

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "provenance"):
            count = confirm_range(config, proposal_range, scope=scope, doc_id=doc_id, target_id=target_id)
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Confirmed {count} proposal(s)")


@provenance.command("confirm-doc")
@click.argument("doc_id")
@click.argument("scope", required=False, default=None)
@click.option("--target", "target_id", default=None)
@click.pass_context
def provenance_confirm_doc_cmd(ctx, doc_id: str, scope: Optional[str], target_id: Optional[str]):
    """Confirm all pending proposals for one source document."""
    from .lock import LibraryLockError, library_lock
    from .provenance import confirm_doc

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "provenance"):
            count = confirm_doc(config, doc_id, target_id=target_id)
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Confirmed {count} proposal(s)")


@provenance.command("reject-doc")
@click.argument("doc_id")
@click.argument("scope", required=False, default=None)
@click.option("--target", "target_id", default=None)
@click.pass_context
def provenance_reject_doc_cmd(ctx, doc_id: str, scope: Optional[str], target_id: Optional[str]):
    """Reject all pending proposals for one source document."""
    from .lock import LibraryLockError, library_lock
    from .provenance import reject_doc

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "provenance"):
            count = reject_doc(config, doc_id, target_id=target_id)
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Rejected {count} proposal(s)")


@provenance.group("stale")
def provenance_stale_group():
    """Mutate stale or repair-needed canonical provenance links."""


@provenance_stale_group.command("refresh-hashes")
@click.argument("link_id")
@click.pass_context
def provenance_stale_refresh_hashes_cmd(ctx, link_id: str):
    from .lock import LibraryLockError, library_lock
    from .provenance import stale_refresh_hashes

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "provenance"):
            preview = stale_refresh_hashes(config, link_id)
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(
        f"Source: persisted slide {preview.source_before['slide_number']}, claim {preview.source_before['claim_index']} "
        f"-> current slide {preview.source_after['slide_number']}, claim {preview.source_after['claim_index']}"
    )
    click.echo(f"  Persisted Claim: {json.dumps(preview.source_before['claim_text'], ensure_ascii=False)}")
    click.echo(f"  Persisted Quote: {json.dumps(preview.source_before['supporting_quote'], ensure_ascii=False)}")
    click.echo(f"  Current Claim:   {json.dumps(preview.source_after['claim_text'], ensure_ascii=False)}")
    click.echo(f"  Current Quote:   {json.dumps(preview.source_after['supporting_quote'], ensure_ascii=False)}")
    click.echo(
        f"Target: persisted slide {preview.target_before['slide_number']}, claim {preview.target_before['claim_index']} "
        f"-> current slide {preview.target_after['slide_number']}, claim {preview.target_after['claim_index']}"
    )
    click.echo(f"  Persisted Claim: {json.dumps(preview.target_before['claim_text'], ensure_ascii=False)}")
    click.echo(f"  Persisted Quote: {json.dumps(preview.target_before['supporting_quote'], ensure_ascii=False)}")
    click.echo(f"  Current Claim:   {json.dumps(preview.target_after['claim_text'], ensure_ascii=False)}")
    click.echo(f"  Current Quote:   {json.dumps(preview.target_after['supporting_quote'], ensure_ascii=False)}")
    click.echo(f"✓ Refreshed {link_id}")


@provenance_stale_group.command("re-evaluate")
@click.argument("link_id")
@click.pass_context
def provenance_stale_re_evaluate_cmd(ctx, link_id: str):
    from .lock import LibraryLockError, library_lock
    from .provenance import stale_re_evaluate

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "provenance"):
            stale_re_evaluate(config, link_id)
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Marked {link_id} for re-evaluation")


@provenance_stale_group.command("remove")
@click.argument("link_id")
@click.pass_context
def provenance_stale_remove_cmd(ctx, link_id: str):
    from .lock import LibraryLockError, library_lock
    from .provenance import stale_remove

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "provenance"):
            stale_remove(config, link_id)
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Removed {link_id}")


@provenance_stale_group.command("acknowledge")
@click.argument("link_id")
@click.pass_context
def provenance_stale_acknowledge_cmd(ctx, link_id: str):
    from .lock import LibraryLockError, library_lock
    from .provenance import stale_acknowledge

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "provenance"):
            stale_acknowledge(config, link_id)
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Acknowledged {link_id}")


@provenance_stale_group.command("remove-doc")
@click.argument("doc_id")
@click.argument("scope", required=False, default=None)
@click.pass_context
def provenance_stale_remove_doc_cmd(ctx, doc_id: str, scope: Optional[str]):
    from .lock import LibraryLockError, library_lock
    from .provenance import stale_remove_doc

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "provenance"):
            count = stale_remove_doc(config, doc_id, scope=scope)
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Removed {count} stale link(s)")


@provenance_stale_group.command("acknowledge-doc")
@click.argument("doc_id")
@click.argument("scope", required=False, default=None)
@click.pass_context
def provenance_stale_ack_doc_cmd(ctx, doc_id: str, scope: Optional[str]):
    from .lock import LibraryLockError, library_lock
    from .provenance import stale_acknowledge_doc

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "provenance"):
            count = stale_acknowledge_doc(config, doc_id, scope=scope)
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Acknowledged {count} stale link(s)")


@cli.group(cls=ScopeOrCommandGroup, invoke_without_command=False)
@click.option("--scope", default=None, hidden=True)
@click.pass_context
def links(ctx, scope: Optional[str]):
    """Review document-level relationship proposals."""
    ctx.ensure_object(dict)
    ctx.obj["links_scope"] = scope


@links.command("review")
@click.argument("scope", required=False, default=None)
@click.option("--doc", "doc_id", default=None, help="Filter to one source document ID.")
@click.option("--target", "target_id", default=None, help="Filter to one target document ID.")
@click.option("--page", type=int, default=1, show_default=True, help="1-based review page number.")
@click.option(
    "--include-flagged",
    is_flag=True,
    default=False,
    help="Include proposals involving flagged-input documents (review_status: flagged).",
)
@click.pass_context
def links_review_cmd(
    ctx,
    scope: Optional[str],
    doc_id: Optional[str],
    target_id: Optional[str],
    page: int,
    include_flagged: bool,
):
    """Read-only review surface for pending relationship proposals."""
    from .links import PAGE_SIZE, collect_pending_relationship_proposals, paginate

    config = ctx.obj["config"]
    proposals, counts = collect_pending_relationship_proposals(
        config,
        scope=scope,
        doc_id=doc_id,
        target_id=target_id,
        include_flagged=include_flagged,
    )
    window, total_pages = paginate(proposals, page)
    if len(proposals) == 0 and counts.flagged_input > 0:
        click.echo(
            f"Pending (0 items — {counts.flagged_input} excluded because source or "
            "target has review_status: flagged; use --include-flagged to review)"
        )
    else:
        click.echo(f"Pending ({len(proposals)} item(s))")
    click.echo(
        f"Page {min(max(1, page), total_pages)}/{total_pages} "
        f"({len(window)} items, page size {PAGE_SIZE}, ordered: source doc → confidence desc → proposal_id)"
    )
    for view in window:
        proposal = view.proposal
        revived_tag = " (revived — basis changed)" if view.revived else ""
        flagged_tag = (
            f" (flagged: {', '.join(view.flagged_inputs)})" if view.flagged_inputs else ""
        )
        click.echo(
            f"[{proposal.proposal_id}] {view.source_id} -> {proposal.target_id} "
            f"({proposal.relation}, {proposal.confidence}, {proposal.producer})"
            f"{revived_tag}{flagged_tag}"
        )
        click.echo(f"  Rationale: {proposal.rationale or '-'}")
        if proposal.signals:
            click.echo(f"  Signals: {', '.join(proposal.signals)}")
    total_rejection_memory = sum(counts.rejection_memory.values())
    if total_rejection_memory == 0:
        click.echo("No proposals suppressed by rejection memory.")
    elif total_rejection_memory == 1:
        click.echo("1 proposal suppressed by rejection memory.")
    else:
        click.echo(f"{total_rejection_memory} proposals suppressed by rejection memory.")
    if counts.flagged_input and not include_flagged:
        plural = "proposal" if counts.flagged_input == 1 else "proposals"
        click.echo(
            f"{counts.flagged_input} {plural} excluded (flagged inputs). "
            "Use --include-flagged to review."
        )


@links.command("status")
@click.argument("scope", required=False, default=None)
@click.option(
    "--include-flagged",
    is_flag=True,
    default=False,
    help="Count proposals involving flagged-input documents toward Pending.",
)
@click.pass_context
def links_status_cmd(ctx, scope: Optional[str], include_flagged: bool):
    """Summarize canonical and pending document-level relationships."""
    from .links import relationship_status_summary

    config = ctx.obj["config"]
    rows, total_flagged_excluded = relationship_status_summary(
        config, scope=scope, include_flagged=include_flagged
    )
    if not rows:
        # When rows is empty, flagged_excluded is necessarily zero because a
        # source with flagged_excluded > 0 would have been emitted as a row.
        # (Dead-code guard removed per D.3 DS-G.)
        click.echo("No document-level relationship data found.")
        return

    total_pending = 0
    total_confirmed = 0
    show_flagged_col = total_flagged_excluded > 0
    if show_flagged_col:
        click.echo("| Source Document | Pending | Confirmed | Flagged Excluded |")
        click.echo("|---|---:|---:|---:|")
    else:
        click.echo("| Source Document | Pending | Confirmed |")
        click.echo("|---|---:|---:|")
    for row in rows:
        total_pending += row.pending
        total_confirmed += row.confirmed
        if show_flagged_col:
            click.echo(
                f"| {row.source_id} | {row.pending} | {row.confirmed} | {row.flagged_excluded} |"
            )
        else:
            click.echo(f"| {row.source_id} | {row.pending} | {row.confirmed} |")
    click.echo("")
    if show_flagged_col:
        click.echo(
            f"Total: {total_pending} pending, {total_confirmed} confirmed, "
            f"{total_flagged_excluded} flagged-excluded"
        )
        click.echo(
            "Use folio links status --include-flagged to count excluded proposals as pending, "
            "or folio links review --include-flagged to inspect them."
        )
    else:
        click.echo(f"Total: {total_pending} pending, {total_confirmed} confirmed")


@links.command("confirm")
@click.argument("proposal_id")
@click.option(
    "--include-flagged",
    is_flag=True,
    default=False,
    help="Allow confirmation of a flagged-input proposal.",
)
@click.pass_context
def links_confirm_cmd(ctx, proposal_id: str, include_flagged: bool):
    """Confirm one pending document-level relationship proposal."""
    from .links import confirm_proposal
    from .lock import LibraryLockError, library_lock

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "links"):
            proposal, flagged_inputs = confirm_proposal(
                config, proposal_id, include_flagged=include_flagged
            )
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    flagged_suffix = (
        f" (flagged: {', '.join(flagged_inputs)})" if flagged_inputs else ""
    )
    click.echo(
        f"✓ Confirmed {proposal.proposal_id}: {proposal.relation} -> "
        f"{proposal.target_id}{flagged_suffix}"
    )


@links.command("reject")
@click.argument("proposal_id")
@click.option(
    "--include-flagged",
    is_flag=True,
    default=False,
    help="Allow rejection of a flagged-input proposal.",
)
@click.pass_context
def links_reject_cmd(ctx, proposal_id: str, include_flagged: bool):
    """Reject one pending document-level relationship proposal."""
    from .links import reject_proposal
    from .lock import LibraryLockError, library_lock

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "links"):
            proposal, flagged_inputs = reject_proposal(
                config, proposal_id, include_flagged=include_flagged
            )
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    flagged_suffix = (
        f" (flagged: {', '.join(flagged_inputs)})" if flagged_inputs else ""
    )
    click.echo(
        f"✓ Rejected {proposal.proposal_id}: {proposal.relation} -> "
        f"{proposal.target_id}{flagged_suffix}"
    )


@links.command("confirm-doc")
@click.argument("doc_id")
@click.option(
    "--include-flagged",
    is_flag=True,
    default=False,
    help="Act on proposals involving flagged-input documents.",
)
@click.pass_context
def links_confirm_doc_cmd(ctx, doc_id: str, include_flagged: bool):
    """Confirm all pending relationship proposals for one source document."""
    from .links import confirm_doc
    from .lock import LibraryLockError, library_lock

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "links"):
            acted, flagged_excluded = confirm_doc(
                config, doc_id, include_flagged=include_flagged
            )
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Confirmed {acted} proposal(s)")
    if flagged_excluded > 0 and not include_flagged:
        click.echo(
            f"{flagged_excluded} proposal(s) excluded from {doc_id} (flagged inputs); "
            "use --include-flagged to act on them."
        )


@links.command("reject-doc")
@click.argument("doc_id")
@click.option(
    "--include-flagged",
    is_flag=True,
    default=False,
    help="Act on proposals involving flagged-input documents.",
)
@click.pass_context
def links_reject_doc_cmd(ctx, doc_id: str, include_flagged: bool):
    """Reject all pending relationship proposals for one source document."""
    from .links import reject_doc
    from .lock import LibraryLockError, library_lock

    config = ctx.obj["config"]
    try:
        with library_lock(config.library_root.resolve(), "links"):
            acted, flagged_excluded = reject_doc(
                config, doc_id, include_flagged=include_flagged
            )
    except (LibraryLockError, ValueError) as e:
        click.echo(f"✗ {e}")
        sys.exit(1)
    click.echo(f"✓ Rejected {acted} proposal(s)")
    if flagged_excluded > 0 and not include_flagged:
        click.echo(
            f"{flagged_excluded} proposal(s) excluded from {doc_id} (flagged inputs); "
            "use --include-flagged to act on them."
        )


@cli.command()
@click.argument("scope", required=False, default=None)
@click.option("--json", "json_output", is_flag=True, default=False, help="Output as shared envelope JSON.")
@click.option(
    "--include-flagged",
    is_flag=True,
    default=False,
    help="Include proposals whose source or target document has `review_status: flagged`.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=0),
    default=None,
    help="Maximum number of findings to emit (default: unbounded).",
)
@click.pass_context
def synthesize(ctx, scope, json_output, include_flagged, limit):
    """List proposal-linked cross-references in a scope (v0.8.0 structural MVP).

    v0.8.0 is read-only: no LLM calls, no registry mutations. Narrative
    synthesis (LLM-backed) is planned for a future version; this version
    surfaces the §5 shared proposal contract as a structural report.
    See CHANGELOG v0.8.0 for the full contract.
    """
    from .synthesize import (
        ScopeResolutionError,
        _render_synthesis_stdout,
        render_envelope,
        synthesize as run_synthesize,
    )

    config = ctx.obj["config"]
    try:
        report = run_synthesize(
            config, scope=scope, include_flagged=include_flagged, limit=limit
        )
    except ScopeResolutionError as exc:
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(1)
    if json_output:
        click.echo(json.dumps(render_envelope(report), indent=2))
        return
    _render_synthesis_stdout(report)


@cli.command()
@click.argument("query", required=True, callback=lambda ctx, p, v: _search_validate_query(ctx, p, v))
@click.option(
    "--scope",
    type=str,
    default=None,
    help="Restrict search to an engagement subtree or document ID. Omit or pass '-' for library-wide.",
)
@click.option(
    "--producer",
    type=str,
    default=None,
    help="Restrict to findings emitted by this exact producer name (case-sensitive).",
)
@click.option(
    "--include-flagged",
    is_flag=True,
    default=False,
    help="Include proposals whose source or target document has `review_status: flagged`.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    default=False,
    help="Emit the shared payload-level envelope as JSON (schema_version 1.1).",
)
@click.option(
    "--limit",
    type=click.IntRange(min=0),
    default=None,
    help="Maximum number of findings to emit (non-negative integer; default: unbounded). 0 emits zero findings but still reports counts.",
)
@click.pass_context
def search(ctx, query, scope, producer, include_flagged, json_output, limit):
    """Search pending relationship proposals by QUERY substring (v0.9.0 structural MVP).

    QUERY is matched case-insensitively against six text fields on each
    pending proposal: source_id, target_id, relation, producer,
    reason_summary, and any element of evidence_bundle. Matching is a
    plain substring check via NFC + str.casefold(); regex and semantic
    search are not available in v0.9.0 (planned for v0.9.1+).

    Tip: QUERY matches `relation` too, so `folio search draws_from` will
    match every draws_from-typed proposal in scope (~1/6 of the queue).
    Use `--scope ENGAGEMENT` to narrow.

    Read-only: no LLM calls, no registry mutations. Emits the shared
    payload-level --json envelope at schema_version 1.1 with a new
    `query` top-level key (first minor-version bump of the shared
    envelope; see CHANGELOG v0.9.0).
    """
    from .search import (
        ScopeResolutionError,
        _render_search_stdout,
        render_envelope,
        search as run_search,
    )

    config = ctx.obj["config"]
    try:
        report = run_search(
            config,
            query=query,
            scope=scope,
            producer=producer,
            include_flagged=include_flagged,
            limit=limit,
        )
    except ScopeResolutionError as exc:
        click.echo(
            f"Error: {exc} Try `folio graph status` for an engagement "
            f"overview, or inspect `<library>/registry.json` for valid "
            f"document IDs.",
            err=True,
        )
        ctx.exit(1)
        return
    if json_output:
        click.echo(json.dumps(render_envelope(report), indent=2))
        return
    _render_search_stdout(report)


def _search_validate_query(ctx, param, value):
    """Thin wrapper delegating to folio.search._validate_query (lazy import)."""
    from .search import _validate_query

    return _validate_query(ctx, param, value)


@cli.group()
@click.pass_context
def graph(ctx):
    """Graph health reporting."""
    pass


@graph.command("status")
@click.argument("scope", required=False, default=None)
@click.pass_context
def graph_status_cmd(ctx, scope: Optional[str]):
    """Show aggregate graph-health metrics."""
    from .graph import graph_status

    config = ctx.obj["config"]
    status = graph_status(config, scope=scope)
    click.echo(f"Pending relationship proposals: {status.pending_relationship_proposals}")
    click.echo(f"Docs without canonical graph links: {status.docs_without_canonical_graph_links}")
    click.echo(f"Orphaned canonical relation targets: {status.orphaned_canonical_relation_targets}")
    click.echo(f"Enrich-protected notes: {status.enrich_protected_notes}")
    click.echo(f"Unconfirmed entities: {status.unconfirmed_entities}")
    click.echo(f"Confirmed entities missing stubs: {status.confirmed_entities_missing_stubs}")
    click.echo(f"Reviewable duplicate person candidates: {status.duplicate_person_candidates}")
    click.echo(f"Stale analysis artifacts: {status.stale_analysis_artifacts}")


@graph.command("doctor")
@click.argument("scope", required=False, default=None)
@click.option("--json", "json_output", is_flag=True, default=False, help="Output as JSON.")
@click.option("--limit", type=int, default=None, help="Maximum number of findings to emit.")
@click.option(
    "--include-flagged",
    is_flag=True,
    default=False,
    help="Include proposals whose source or target document has `review_status: flagged`.",
)
@click.pass_context
def graph_doctor_cmd(
    ctx,
    scope: Optional[str],
    json_output: bool,
    limit: Optional[int],
    include_flagged: bool,
):
    """Emit actionable graph-health findings.

    v0.7.1 breaking change: in `--json` output, pending-proposal findings now
    carry `proposal_id` (replacing `subject_id` for that use). See CHANGELOG
    for full details.
    """
    from .graph import _aggregate_producer_acceptance_rates, graph_doctor

    config = ctx.obj["config"]
    findings = graph_doctor(config, scope=scope, limit=limit, include_flagged=include_flagged)
    rates, missing_producer_count = _aggregate_producer_acceptance_rates(config, scope=scope)

    if json_output:
        rate_dicts = [
            {
                "producer": r.producer,
                "accepted": r.accepted,
                "rejected": r.rejected,
                "total_reviewed": r.total_reviewed,
                "rate": r.rate,
                "status": r.status,
                "warmup": r.warmup,
            }
            for r in rates
        ]
        payload = {
            "findings": findings,
            "producer_acceptance_rates": rate_dicts,
            "producer_acceptance_rates_data_integrity": {
                "missing_producer_count": missing_producer_count,
            },
        }
        click.echo(json.dumps(payload, indent=2))
        return

    if findings:
        for finding in findings:
            subject_or_proposal = (
                finding.get("proposal_id")
                or finding.get("subject_id")
                or "—"
            )
            severity_suffix = ""
            if finding.get("trust_status") == "flagged":
                severity_suffix += " [flagged]"
            gate = finding.get("schema_gate_result")
            if gate is not None:
                severity_suffix += f" [schema-gate: {gate.get('rule', 'unknown')}]"
            click.echo(
                f"[{finding['severity']}{severity_suffix}] {finding['code']} "
                f"{subject_or_proposal}: {finding['detail']}"
            )
            click.echo(f"  Action: {finding['recommended_action']}")
    else:
        click.echo("No graph-health findings.")

    click.echo("")
    click.echo("### Producer acceptance rates")
    if not rates:
        click.echo("No producer acceptance-rate data yet.")
    else:
        click.echo("| Producer | Accepted | Rejected | Reviewed | Rate | Status |")
        click.echo("|---|---:|---:|---:|---:|---|")
        for r in rates:
            if r.warmup:
                rate_cell = "—"
                status_cell = "warmup (< 10 reviewed)"
            elif r.status == "low-acceptance":
                rate_cell = f"{r.rate:.2f}" if r.rate is not None else "—"
                status_cell = "low-acceptance (< 50%)"
            else:
                rate_cell = f"{r.rate:.2f}" if r.rate is not None else "—"
                status_cell = "ok"
            click.echo(
                f"| {r.producer} | {r.accepted} | {r.rejected} | {r.total_reviewed} | {rate_cell} | {status_cell} |"
            )
        click.echo("")
        click.echo(
            "Status column is informational only in v0.6.0; `low-acceptance` "
            "producers continue to surface proposals at normal priority in this slice."
        )
    if missing_producer_count > 0:
        click.echo(
            f"Data-integrity: {missing_producer_count} accepted "
            f"{'entry' if missing_producer_count == 1 else 'entries'} excluded (missing `producer` field)."
        )


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
        click.echo(reg.to_json())
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
            if entry.type == "person":
                if entry.title:
                    detail = entry.title
                    if entry.department:
                        detail += f", {reg.resolve_key_to_name(entry.department, 'department')}"
                elif entry.department:
                    detail = reg.resolve_key_to_name(entry.department, "department")
            elif entry.type == "department" and entry.head:
                detail = f"Head: {reg.resolve_key_to_name(entry.head, 'person')}"
            elif entry.type in ("system", "process"):
                parts = []
                if entry.owner_dept:
                    parts.append(reg.resolve_key_to_name(entry.owner_dept, "department"))
                if entry.status:
                    parts.append(entry.status)
                detail = ", ".join(parts)
            proposal = ""
            if entry.needs_confirmation:
                if entry.proposed_match:
                    proposed_name = reg.resolve_key_to_name(entry.proposed_match, entry.type)
                    proposal = f" proposed: {proposed_name}"
                else:
                    proposal = " no proposed match"
            if detail:
                click.echo(f"  {entry.canonical_name:<20s} {detail:<25s} {status}{proposal}")
            else:
                click.echo(f"  {entry.canonical_name:<20s} {'':25s} {status}{proposal}")
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
        click.echo(f"  Department:  {reg.resolve_key_to_name(entry.department, 'department')}")
    if entry.reports_to:
        click.echo(f"  Reports to:  {reg.resolve_key_to_name(entry.reports_to, 'person')}")
    if entry.aliases:
        click.echo(f"  Aliases:     {', '.join(entry.aliases)}")
    if entry.client:
        click.echo(f"  Client:      {entry.client}")
    if entry.head:
        click.echo(f"  Head:        {reg.resolve_key_to_name(entry.head, 'person')}")
    if entry.owner_dept:
        click.echo(f"  Owner dept:  {reg.resolve_key_to_name(entry.owner_dept, 'department')}")
    if entry.needs_confirmation:
        if entry.proposed_match:
            click.echo(
                f"  Proposed match: {reg.resolve_key_to_name(entry.proposed_match, etype)}"
            )
        else:
            click.echo("  Proposed match: none")
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

    if result.org_chart_detected:
        click.echo("  Next: run `folio entities generate-stubs --force` to refresh entity notes.")


@entities.command("generate-stubs")
@click.option("--output-dir", type=click.Path(path_type=Path), default=None,
              help="Output directory for generated stubs (default: <library>/_entities).")
@click.option("--force", is_flag=True, default=False,
              help="Refresh auto-generated stubs that already exist.")
@click.pass_context
def generate_stubs_cmd(ctx, output_dir: Optional[Path], force: bool):
    """Generate lightweight markdown stubs for registry entities."""
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()
    entities_path = library_root / "entities.json"

    from .entity_stubs import generate_entity_stubs
    from .tracking.entities import EntityRegistry, EntityRegistryError

    reg = EntityRegistry(entities_path)
    try:
        reg.load()
    except EntityRegistryError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    resolved_output_dir = output_dir or (library_root / "_entities")
    if not resolved_output_dir.is_absolute():
        resolved_output_dir = library_root / resolved_output_dir

    try:
        result = generate_entity_stubs(
            registry=reg,
            output_dir=resolved_output_dir,
            force=force,
        )
    except OSError as e:
        click.echo(f"✗ Stub generation failed: {e}", err=True)
        sys.exit(1)

    generated_breakdown = ", ".join(
        f"{count} {entity_type}"
        for entity_type, count in sorted(result.generated_by_type.items())
        if count
    ) or "0 generated"
    skipped_total = result.skipped_existing + result.skipped_manual

    click.echo(
        f"Generated {result.generated} entity stubs ({generated_breakdown}). "
        f"{skipped_total} skipped."
    )
    if result.removed:
        click.echo(f"  Removed stale auto-generated stubs: {result.removed}")
    if result.skipped_manual:
        click.echo(f"  Manual stubs preserved: {result.skipped_manual}")

    for warning in result.warnings:
        click.echo(f"  ⚠ {warning}")


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


@entities.command("suggest-merges")
@click.option("--type", "entity_type",
              type=click.Choice(["person"]),
              default="person",
              show_default=True,
              help="Entity type to inspect for merge candidates.")
@click.option("--page", type=int, default=1, show_default=True,
              help="1-based page number.")
@click.pass_context
def suggest_merges_cmd(ctx, entity_type: str, page: int):
    """Suggest deterministic entity merge candidates.

    Candidates rejected by prior ``folio entities reject-merge`` calls are
    suppressed by rejection memory. Output always discloses suppression
    count and total rejections recorded.
    """
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()
    entities_path = library_root / "entities.json"

    from .lock import library_lock
    from .tracking.entities import EntityRegistry, EntityRegistryError

    reg = EntityRegistry(entities_path)
    with library_lock(library_root, "entities suggest-merges"):
        try:
            reg.load()
        except EntityRegistryError as e:
            click.echo(f"✗ {e}", err=True)
            sys.exit(1)

        if entity_type != "person":
            click.echo("No merge heuristics available for this entity type.")
            _render_merge_disclosure(reg, suppressed_count=0)
            return

        unfiltered = reg.suggest_person_merges(apply_rejection_memory=False)
        suggestions = reg.suggest_person_merges(apply_rejection_memory=True)
        suppressed_count = len(unfiltered) - len(suggestions)

        if not suggestions:
            click.echo("No merge candidates found.")
            _render_merge_disclosure(reg, suppressed_count=suppressed_count)
            return

        page_size = 20
        total_pages = max(1, (len(suggestions) + page_size - 1) // page_size)
        page = min(max(1, page), total_pages)
        start = (page - 1) * page_size
        window = suggestions[start:start + page_size]

        click.echo(f"Merge Candidates ({len(suggestions)} total)")
        click.echo(
            f"Page {page}/{total_pages} ({len(window)} candidates, page size {page_size})"
        )
        for suggestion in window:
            reasons = ", ".join(suggestion.reasons)
            revived_suffix = " (revived — basis changed)" if suggestion.revived else ""
            click.echo(
                f"- {suggestion.left_name} [{suggestion.left_key}] <> "
                f"{suggestion.right_name} [{suggestion.right_key}]{revived_suffix}"
            )
            click.echo(f"  Reasons: {reasons}")

        _render_merge_disclosure(reg, suppressed_count=suppressed_count)


def _render_merge_disclosure(reg, suppressed_count: int) -> None:
    """Always-render disclosure block: suppression count + total rejections.

    Three-branch pluralization matches slice 1's ``folio links review`` pattern.
    """
    if suppressed_count == 0:
        click.echo("No merge candidates suppressed by rejection memory.")
    elif suppressed_count == 1:
        click.echo("1 merge candidate suppressed by rejection memory.")
    else:
        click.echo(f"{suppressed_count} merge candidates suppressed by rejection memory.")
    total = reg.count_entity_merge_suppressions()
    click.echo(f"({total} total rejections recorded.)")


@entities.command("reject-merge")
@click.argument("left")
@click.argument("right")
@click.pass_context
def reject_merge_cmd(ctx, left: str, right: str):
    """Reject a merge candidate so it stops surfacing in suggest-merges.

    Example: folio entities reject-merge alice_chen chen_alice

    The rejection is keyed on the sorted pair plus the current
    basis_fingerprint. If entity aliases later change enough to shift the
    fingerprint, the candidate revives with a ``(revived — basis changed)``
    annotation in ``folio entities suggest-merges`` output.
    """
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()
    entities_path = library_root / "entities.json"

    from .lock import library_lock
    from .tracking.entities import EntityRegistry, EntityRegistryError

    reg = EntityRegistry(entities_path)
    with library_lock(library_root, "entities reject-merge"):
        try:
            reg.load()
        except EntityRegistryError as e:
            click.echo(f"✗ {e}", err=True)
            sys.exit(1)

        try:
            changed, status = reg.reject_person_merge(left, right)
        except EntityRegistryError as e:
            click.echo(f"✗ Merge candidate is stale: {e}", err=True)
            sys.exit(1)

        if not changed:
            left_entry = reg.get_entity("person", left)
            right_entry = reg.get_entity("person", right)
            left_name = left_entry.canonical_name if left_entry else left
            right_name = right_entry.canonical_name if right_entry else right
            click.echo(
                f"= Already rejected: {left_name} <> {right_name} (no change)"
            )
            return

        reg.save()

        # Echo full context including reasons for the new record.
        left_entry = reg.get_entity("person", left)
        right_entry = reg.get_entity("person", right)
        left_name = left_entry.canonical_name if left_entry else left
        right_name = right_entry.canonical_name if right_entry else right
        # Look up reasons by re-checking the just-written record (last entry).
        rejected_records = reg._data.get("rejected_merges", [])
        reasons: list[str] = []
        if rejected_records and isinstance(rejected_records[-1], dict):
            maybe_reasons = rejected_records[-1].get("reasons_at_rejection", [])
            if isinstance(maybe_reasons, list):
                reasons = [r for r in maybe_reasons if isinstance(r, str)]
        reasons_str = ", ".join(reasons) if reasons else "none"
        click.echo(
            f"✓ Rejected merge candidate: {left_name} [{left}] <> "
            f"{right_name} [{right}] (reasons: {reasons_str})"
        )


@entities.command("merge")
@click.argument("winner")
@click.argument("loser")
@click.pass_context
def merge_entities_cmd(ctx, winner: str, loser: str):
    """Merge one person entity into another."""
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()
    entities_path = library_root / "entities.json"

    from .tracking.entities import EntityRegistry, EntityRegistryError, EntityAmbiguousError

    reg = EntityRegistry(entities_path)
    try:
        reg.load()
    except EntityRegistryError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    try:
        winner_match = reg.lookup_unique(winner, entity_type="person")
        loser_match = reg.lookup_unique(loser, entity_type="person")
    except EntityAmbiguousError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    if winner_match is None:
        click.echo(f"✗ No person found matching '{winner}'.", err=True)
        sys.exit(1)
    if loser_match is None:
        click.echo(f"✗ No person found matching '{loser}'.", err=True)
        sys.exit(1)

    _etype, winner_key, winner_entry = winner_match
    _etype, loser_key, loser_entry = loser_match

    try:
        result = reg.merge_person_entities(winner_key, loser_key)
        reg.save()
    except EntityRegistryError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    click.echo(
        f"Merged {loser_entry.canonical_name} ({loser_key}) into "
        f"{winner_entry.canonical_name} ({winner_key})."
    )
    click.echo(f"  Rewritten references: {result.rewritten_references}")
    if result.dropped_aliases:
        click.echo(f"  Dropped aliases: {', '.join(result.dropped_aliases)}")
    if result.warnings:
        for warning in result.warnings:
            click.echo(f"  ⚠ {warning}")
    click.echo("  Next: run `folio entities generate-stubs --force` to refresh entity notes.")


# ---------------------------------------------------------------------------
# Context document management
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def context(ctx):
    """Context document management."""
    pass


@context.command("init")
@click.option("--client", required=True, help="Client name.")
@click.option("--engagement", required=True, help="Engagement name.")
@click.option("--target", type=click.Path(path_type=Path), default=None,
              help="Override target path or directory.")
@click.pass_context
def context_init(ctx, client: str, engagement: str, target: Optional[Path]):
    """Create an engagement context document.

    Examples:

        folio context init --client "US Bank" --engagement "Tech Resilience DD"

        folio context init --client Acme --engagement "Ops Sprint 2026" --target ./custom/path/
    """
    config = ctx.obj["config"]

    from .context import create_context_document

    try:
        context_id, output_path = create_context_document(
            config,
            client=client,
            engagement=engagement,
            target=target,
        )
    except FileExistsError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    click.echo(f"✓ Created context document: {output_path}")
    click.echo(f"  ID: {context_id}")


@cli.group()
@click.pass_context
def analysis(ctx):
    """Managed analysis document commands."""
    pass


@analysis.command("init")
@click.argument("subtype", type=click.Choice([
    "hypothesis", "issue_tree", "synthesis", "framework_application", "digest",
]))
@click.option("--title", required=True, help="Analysis title.")
@click.option("--client", required=True, help="Client name.")
@click.option("--engagement", required=True, help="Engagement name.")
@click.option("--draws-from", "draws_from", multiple=True, help="Registry document ID to add to draws_from.")
@click.option("--depends-on", "depends_on", multiple=True, help="Registry document ID to add to depends_on.")
@click.option("--target", type=click.Path(path_type=Path), default=None,
              help="Override target path or directory.")
@click.pass_context
def analysis_init_cmd(
    ctx,
    subtype: str,
    title: str,
    client: str,
    engagement: str,
    draws_from: tuple[str, ...],
    depends_on: tuple[str, ...],
    target: Optional[Path],
):
    """Create a source-less managed analysis note."""
    from .analysis_docs import create_analysis_document

    config = ctx.obj["config"]
    try:
        analysis_id, output_path = create_analysis_document(
            config,
            subtype=subtype,
            title=title,
            client=client,
            engagement=engagement,
            draws_from=list(draws_from),
            depends_on=list(depends_on),
            target=target,
        )
    except (FileExistsError, ValueError) as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(1)

    click.echo(f"✓ Created analysis document: {output_path}")
    click.echo(f"  ID: {analysis_id}")


def main():
    """Entry point."""
    cli()
