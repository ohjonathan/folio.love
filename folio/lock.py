"""Library-wide command lock for long-running Folio mutations."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class LibraryLockError(RuntimeError):
    """Raised when the library lock cannot be acquired."""


def _pid_alive(pid: int) -> bool:
    """Return True when a PID is still alive."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


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
            if isinstance(existing_pid, int) and _pid_alive(existing_pid):
                owner = existing.get("command", "unknown")
                raise LibraryLockError(
                    f"library lock already held by pid {existing_pid} ({owner})"
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
