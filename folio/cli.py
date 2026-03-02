"""CLI interface for Folio."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .config import FolioConfig
from .converter import FolioConverter


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
@click.pass_context
def convert(ctx, source: str, note: str, client: str, engagement: str, target: str, passes: int):
    """Convert a single deck to Folio markdown.

    SOURCE is the path to a PPTX or PDF file.

    Examples:

        folio convert deck.pptx

        folio convert deck.pptx --client ClientA --engagement "DD Q1 2026"

        folio convert deck.pptx --note "Updated risk figures"
    """
    config = ctx.obj["config"]
    converter = FolioConverter(config)

    try:
        result = converter.convert(
            source_path=Path(source),
            note=note,
            client=client,
            engagement=engagement,
            target=Path(target) if target else None,
            passes=passes,
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
@click.option("--passes", "-p", type=click.IntRange(1, 2), default=None,
              help="Analysis depth: 1=standard, 2=deep (selective second pass on dense slides).")
@click.pass_context
def batch(ctx, directory: str, pattern: str, note: str, client: str, engagement: str, passes: int):
    """Batch convert all matching files in a directory.

    Examples:

        folio batch ./materials

        folio batch ./materials --pattern "*.pdf" --client ClientA
    """
    config = ctx.obj["config"]
    converter = FolioConverter(config)
    dir_path = Path(directory)

    files = sorted(dir_path.glob(pattern))
    if not files:
        click.echo(f"No files matching '{pattern}' in {directory}")
        return

    click.echo(f"Converting {len(files)} files...")
    click.echo("")

    succeeded = 0
    failed = 0

    for f in files:
        try:
            result = converter.convert(
                source_path=f,
                note=note,
                client=client,
                engagement=engagement,
                passes=passes,
            )
            click.echo(f"✓ {f.name} ({result.slide_count} slides)")
            succeeded += 1
        except Exception as e:
            click.echo(f"✗ {f.name} ({e})")
            failed += 1

    click.echo("")
    click.echo(f"Complete: {succeeded} succeeded, {failed} failed")


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
