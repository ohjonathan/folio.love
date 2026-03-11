"""CLI interface for Folio."""

import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click

from .config import FolioConfig
from .converter import FolioConverter, PPTX_EXTENSIONS

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

# AppleScript error codes are 4-digit negative numbers following "error number"
# or "error (" patterns.  We anchor to these patterns to avoid false matches
# on arbitrary negative numbers in unrelated error messages.
_APPLESCRIPT_ERROR_RE = re.compile(r"error\s+(?:number\s+)?(-\d{4,})")


@dataclass
class BatchOutcome:
    """Per-file batch outcome record."""
    file_name: str
    renderer: str
    duration: float
    outcome: str  # success | applescript_<code> | timeout | unknown
    slide_count: int = 0


def _classify_outcome(exc: Exception) -> str:
    """Classify an exception into an allowed outcome bucket."""
    msg = str(exc)
    if "timed out" in msg.lower():
        return "timeout"
    # Match AppleScript-style error codes (e.g., "error number -9074")
    match = _APPLESCRIPT_ERROR_RE.search(msg)
    if match:
        return f"applescript_{match.group(1)}"
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
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s" if not verbose else "%(name)s: %(message)s",
    )

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

    # Classify files into automated PPTX vs PDF mitigation
    is_pdf_batch = all(f.suffix.lower() == ".pdf" for f in files)

    click.echo(f"Converting {len(files)} files...")
    if is_pdf_batch:
        click.echo("  Mode: PDF mitigation (not Tier 1)")
    click.echo("")

    outcomes: list[BatchOutcome] = []
    pptx_conversion_count = 0  # Track PPTX conversions for restart cadence

    for f in files:
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

    total = current + stale + missing
    click.echo(f"Library: {total} decks")
    click.echo(f"  ✓ Current: {current}")
    if stale:
        click.echo(f"  ⚠ Stale: {stale}")
    if missing:
        click.echo(f"  ✗ Missing source: {missing}")

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
    scan_extensions = PPTX_EXTENSIONS | {".pdf"}

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
    """Re-convert stale decks in the library.

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
    for deck_id, entry_data in data.get("decks", {}).items():
        entry = registry.entry_from_dict(entry_data)

        # Scope filter
        if scope:
            if not (_matches_scope(entry.markdown_path, scope) or
                    _matches_scope(entry.deck_dir, scope)):
                continue

        # Refresh staleness
        entry = registry.refresh_entry_status(library_root, entry)

        if convert_all or entry.staleness_status == "stale":
            entries_to_refresh.append(entry)

    if not entries_to_refresh:
        click.echo("Nothing to refresh.")
        return

    click.echo(f"Refreshing {len(entries_to_refresh)} deck(s)...")
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


def main():
    """Entry point."""
    cli()
