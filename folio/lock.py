"""Library-wide command lock for long-running Folio mutations."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path


class LibraryLockError(RuntimeError):
    """Raised when the library lock cannot be acquired."""


LOCK_STALE_AFTER = timedelta(hours=2)


def _pid_alive(pid: int) -> bool:
    """Return True when a PID is still alive."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _parse_lock_timestamp(value: object) -> datetime | None:
    """Parse a lock timestamp into an aware UTC datetime."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _lock_is_stale(existing: dict) -> bool:
    """Return True when an existing lock should be treated as stale."""
    now = datetime.now(timezone.utc)
    timestamp = _parse_lock_timestamp(existing.get("timestamp"))
    if timestamp is not None and now - timestamp > LOCK_STALE_AFTER:
        return True
    existing_pid = existing.get("pid")
    if isinstance(existing_pid, int) and not _pid_alive(existing_pid):
        return True
    return False


@contextmanager
def library_lock(library_root: Path, command_name: str):
    """Acquire the library-wide `.folio.lock` file with stale-lock cleanup."""
    library_root = Path(library_root).resolve()
    lock_path = library_root / ".folio.lock"
    payload = {
        "pid": os.getpid(),
        "command": command_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                existing = json.loads(lock_path.read_text(encoding="utf-8") or "{}")
            except Exception:
                existing = {}
            existing_pid = existing.get("pid")
            if not _lock_is_stale(existing):
                owner = existing.get("command", "unknown")
                pid_label = existing_pid if isinstance(existing_pid, int) else "unknown"
                raise LibraryLockError(
                    f"library lock already held by pid {pid_label} ({owner})"
                )
            try:
                lock_path.unlink()
            except FileNotFoundError:
                continue

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
