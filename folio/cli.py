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
                file_name=f.name, renderer=renderer_label,
                duration=duration, outcome="success",
                slide_count=result.slide_count,
            ))
            if is_pptx:
                pptx_conversion_count += 1
        except Exception as e:
            duration = time.monotonic() - start
            outcome = _classify_outcome(e)

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
                        file_name=f.name, renderer=renderer_label,
                        duration=retry_duration, outcome="success",
                        slide_count=result.slide_count,
                    ))
                    pptx_conversion_count += 1
                    continue
                except Exception as retry_e:
                    retry_duration = time.monotonic() - retry_start
                    outcome = _classify_outcome(retry_e)
                    click.echo(f"✗ {f.name} (retry failed: {outcome}, {retry_duration:.1f}s)")
                    outcomes.append(BatchOutcome(
                        file_name=f.name, renderer=renderer_label,
                        duration=retry_duration, outcome=outcome,
                    ))
                    if is_pptx:
                        pptx_conversion_count += 1
                    continue

            click.echo(f"✗ {f.name} ({outcome}, {duration:.1f}s)")
            outcomes.append(BatchOutcome(
                file_name=f.name, renderer=renderer_label,
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
@click.pass_context
def status(ctx, scope: Optional[str]):
    """Show library status.

    Optionally scope to a client or engagement:

        folio status

        folio status ClientA
    """
    config = ctx.obj["config"]
    library_root = config.library_root.resolve()

    if not library_root.exists():
        click.echo(f"Library not found at {library_root}")
        click.echo("Run 'folio convert' to create your first conversion.")
        return

    # Find all markdown files in the library
    from .tracking.sources import check_staleness
    import yaml as yaml_lib

    search_path = library_root / scope if scope else library_root
    md_files = sorted(search_path.rglob("*.md"))

    current = 0
    stale = 0
    missing = 0
    stale_decks = []
    missing_decks = []

    for md_file in md_files:
        # Skip non-folio markdown (no frontmatter)
        try:
            content = md_file.read_text()
            if not content.startswith("---"):
                continue
            end = content.index("---", 3)
            fm = yaml_lib.safe_load(content[3:end])
            if not fm or "source" not in fm or "source_hash" not in fm:
                continue
        except (ValueError, yaml_lib.YAMLError):
            continue

        result = check_staleness(md_file, fm["source"], fm["source_hash"])

        if result["status"] == "current":
            current += 1
        elif result["status"] == "stale":
            stale += 1
            stale_decks.append((md_file.relative_to(library_root), result))
        elif result["status"] == "missing":
            missing += 1
            missing_decks.append((md_file.relative_to(library_root), result))

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
        for path, _ in stale_decks:
            click.echo(f"  {path}")

    if missing_decks:
        click.echo("")
        click.echo("Missing:")
        for path, info in missing_decks:
            click.echo(f"  {path} (source: {info.get('source_path', 'unknown')})")


def main():
    """Entry point."""
    cli()
