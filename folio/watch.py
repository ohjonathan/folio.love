"""Folder-based auto-ingestion for Folio."""

from __future__ import annotations

import shutil
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import FolioConfig
from .converter import DOCUMENT_EXTENSIONS, PPTX_EXTENSIONS, FolioConverter
from .correspondence import EMAIL_EXTENSIONS, ingest_email
from .ingest import SUPPORTED_INGEST_EXTENSIONS, ingest_source

CONVERT_EXTENSIONS = PPTX_EXTENSIONS | DOCUMENT_EXTENSIONS | {".pdf"}
WATCHABLE_EXTENSIONS = CONVERT_EXTENSIONS | SUPPORTED_INGEST_EXTENSIONS


@dataclass(frozen=True)
class WatchFileResult:
    source_path: Path
    action: str
    outcome: str
    output_path: Path | None = None
    error: str | None = None


def run_watch_once(
    config: FolioConfig,
    directory: Path,
    *,
    dry_run: bool = False,
    quiet: bool = False,
    emit: Callable[[str], None] | None = None,
    stability_seconds: float | None = None,
) -> list[WatchFileResult]:
    """Process the current contents of a watched directory once."""

    directory = Path(directory).resolve()
    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"Watch directory not found: {directory}")
    watch_config = _match_watch_config(config, directory)
    stable_seconds = (
        stability_seconds
        if stability_seconds is not None
        else float(watch_config.get("stability_seconds", 3))
    )
    results: list[WatchFileResult] = []
    for source_path in _iter_watch_files(directory):
        action = route_file(source_path)
        if action == "skip":
            result = WatchFileResult(source_path=source_path, action=action, outcome="skipped")
            results.append(result)
            _emit(emit, quiet, f"⊘ {source_path.name} (unsupported)")
            continue
        if dry_run:
            result = WatchFileResult(source_path=source_path, action=action, outcome="dry_run")
            results.append(result)
            _emit(emit, quiet, f"dry-run: {source_path.name} → {action}")
            continue
        try:
            _wait_for_stable_size(source_path, stable_seconds)
            output_path = _process_file(config, source_path, action)
            _archive_success(source_path, directory, watch_config)
            result = WatchFileResult(
                source_path=source_path,
                action=action,
                outcome="success",
                output_path=output_path,
            )
            _emit(emit, quiet, f"✓ {source_path.name} → {action}")
        except Exception as exc:
            failed_path = _write_failure(source_path, directory, exc)
            result = WatchFileResult(
                source_path=source_path,
                action=action,
                outcome="failed",
                output_path=failed_path,
                error=str(exc),
            )
            _emit(emit, False, f"✗ {source_path.name}: {exc}")
        results.append(result)
    return results


def run_watch_loop(
    config: FolioConfig,
    directory: Path,
    *,
    dry_run: bool = False,
    quiet: bool = False,
    interval_seconds: float = 3,
    emit: Callable[[str], None] | None = None,
) -> None:
    """Run a simple polling watcher until interrupted."""

    while True:
        run_watch_once(config, directory, dry_run=dry_run, quiet=quiet, emit=emit)
        time.sleep(interval_seconds)


def route_file(path: Path) -> str:
    """Return the pipeline action for a path."""

    suffix = Path(path).suffix.lower()
    if suffix in EMAIL_EXTENSIONS:
        return "ingest_email"
    if suffix in CONVERT_EXTENSIONS:
        return "convert"
    if suffix in SUPPORTED_INGEST_EXTENSIONS:
        return "ingest"
    return "skip"


def _process_file(config: FolioConfig, source_path: Path, action: str) -> Path:
    if action == "convert":
        return FolioConverter(config).convert(source_path=source_path).output_path
    if action == "ingest_email":
        return ingest_email(config, source_path=source_path).output_path
    if action == "ingest":
        return ingest_source(config, source_path=source_path).output_path
    raise ValueError(f"Unsupported watch action: {action}")


def _iter_watch_files(directory: Path) -> list[Path]:
    results = []
    for child in sorted(directory.iterdir()):
        if child.name in {"_archive", "_failed"}:
            continue
        if child.is_file():
            results.append(child)
    return results


def _wait_for_stable_size(path: Path, seconds: float) -> None:
    if seconds <= 0:
        return
    previous = path.stat().st_size
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))
        current = path.stat().st_size
        if current != previous:
            previous = current
            deadline = time.monotonic() + seconds


def _archive_success(source_path: Path, directory: Path, watch_config: dict) -> None:
    after = watch_config.get("after_process") if isinstance(watch_config, dict) else None
    action = "archive"
    destination = directory / "_archive"
    if isinstance(after, dict):
        action = str(after.get("action", "archive"))
        if after.get("to"):
            destination = Path(str(after["to"])).expanduser()
    if action == "leave":
        return
    if action == "delete":
        source_path.unlink(missing_ok=True)
        return
    destination.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source_path), str(_unique_destination(destination / source_path.name)))


def _write_failure(source_path: Path, directory: Path, exc: Exception) -> Path:
    failed_dir = directory / "_failed"
    failed_dir.mkdir(parents=True, exist_ok=True)
    failed_source_path = _unique_destination(failed_dir / source_path.name)
    if source_path.exists():
        shutil.move(str(source_path), str(failed_source_path))
    error_path = _unique_destination(failed_dir / f"{failed_source_path.name}.error.log")
    error_path.write_text(
        f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}",
        encoding="utf-8",
    )
    return failed_source_path


def _unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 10_000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find unique destination for {path}")


def _match_watch_config(config: FolioConfig, directory: Path) -> dict:
    for item in config.watch:
        raw_path = item.get("path")
        if not raw_path:
            continue
        configured = Path(str(raw_path)).expanduser()
        if not configured.is_absolute() and config.config_dir is not None:
            configured = config.config_dir / configured
        try:
            if configured.resolve() == directory.resolve():
                return item
        except OSError:
            continue
    return {}


def _emit(emit: Callable[[str], None] | None, quiet: bool, message: str) -> None:
    if quiet and not message.startswith("✗"):
        return
    if emit:
        emit(message)
