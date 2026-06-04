"""Canonical timestamp normalization for transcript-derived analysis fields.

Shared single source of truth used by both the VTT/SRT cue normalizer
(:mod:`folio.pipeline.transcript_formats`) and the interaction-analysis
extraction pipeline (:mod:`folio.pipeline.interaction_analysis`) so that every
timestamp emitted into generated notes uses one canonical, machine-parseable
format::

    HH:MM:SS.mmm
    HH:MM:SS.mmm - HH:MM:SS.mmm   (ranges)

Cue timestamps fed to the LLM are already canonical, but the model sometimes
reformats them when populating extracted findings/quotes/action items — e.g.
``04:21:900`` or ``01:20:49:519`` (a colon before the milliseconds instead of a
decimal point). Those unambiguous cases are *repaired*; anything that cannot be
repaired safely (a non-numeric token, an out-of-range field, or an inverted
range such as ``03:03:03.650 - 03:18:819``) is *flagged* so the caller can mark
the finding for review rather than silently emit bad data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["CanonResult", "canonicalize_timestamp"]

# Separators that may join the two ends of a range. ``-->`` is matched before a
# bare ``-`` so VTT cue arrows split cleanly. Timestamp tokens never contain a
# hyphen, so splitting on ``-`` is unambiguous.
_RANGE_SPLIT_RE = re.compile(r"\s*(?:-->|–|—|-)\s*")


@dataclass(frozen=True)
class CanonResult:
    """Outcome of canonicalizing a timestamp string.

    Attributes:
        value: Canonical timestamp/range string, or ``None`` when flagged.
        status: ``"ok"`` (already canonical), ``"repaired"`` (a malformed input
            was fixed), or ``"flagged"`` (could not be repaired safely — the
            caller should drop the value and mark the finding for review).
    """

    value: str | None
    status: str

    @property
    def ok(self) -> bool:
        """True when a usable canonical ``value`` was produced."""
        return self.value is not None


def canonicalize_timestamp(raw: str | None) -> CanonResult:
    """Canonicalize a single timestamp or ``start - end`` range.

    Returns a :class:`CanonResult`. ``status`` is ``"flagged"`` (with
    ``value=None``) when the input cannot be repaired safely.
    """
    if raw is None:
        return CanonResult(None, "flagged")
    text = str(raw).strip()
    if not text:
        return CanonResult(None, "flagged")

    parts = _RANGE_SPLIT_RE.split(text)

    if len(parts) == 1:
        parsed = _parse_token(parts[0])
        if parsed is None:
            return CanonResult(None, "flagged")
        total_ms, had_ms = parsed
        value = _format(total_ms, had_ms)
        return CanonResult(value, "ok" if value == text else "repaired")

    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        start = _parse_token(parts[0])
        end = _parse_token(parts[1])
        if start is None or end is None:
            return CanonResult(None, "flagged")
        if end[0] < start[0]:
            # Inverted range (e.g. the dropped-hour ``03:03:03.650 - 03:18:819``
            # whose end resolves before its start): not safely repairable.
            return CanonResult(None, "flagged")
        with_ms = start[1] or end[1]
        value = f"{_format(start[0], with_ms)} - {_format(end[0], with_ms)}"
        return CanonResult(value, "ok" if value == text else "repaired")

    # Zero, or more than two, range segments — ambiguous.
    return CanonResult(None, "flagged")


def _parse_token(token: str) -> tuple[int, bool] | None:
    """Parse one timestamp token into ``(total_milliseconds, had_ms)``.

    Returns ``None`` when the token cannot be parsed into a valid
    ``HH:MM:SS(.mmm)`` time. Milliseconds are recognized either after a decimal
    point or — for the malformed colon form — as a trailing three-digit group
    (VTT mandates three-digit milliseconds and two-digit seconds, so the digit
    width disambiguates ``…:49:519`` from a genuine ``HH:MM:SS``).
    """
    raw = token.strip().replace(",", ".")
    if not raw:
        return None

    ms: int | None = None
    if "." in raw:
        head, _, frac = raw.rpartition(".")
        if not frac.isdigit() or not head:
            return None
        ms = int((frac + "000")[:3])
        groups = head.split(":")
    else:
        groups = raw.split(":")
        if len(groups) >= 2 and groups[-1].isdigit() and len(groups[-1]) == 3:
            ms = int(groups[-1])
            groups = groups[:-1]

    if not groups or not all(g.isdigit() for g in groups):
        return None
    if len(groups) > 3:
        return None

    nums = [int(g) for g in groups]
    while len(nums) < 3:
        nums.insert(0, 0)
    hours, minutes, seconds = nums
    if minutes >= 60 or seconds >= 60:
        return None

    total_ms = ((hours * 3600) + (minutes * 60) + seconds) * 1000 + (ms or 0)
    return total_ms, ms is not None


def _format(total_ms: int, with_ms: bool) -> str:
    """Render total milliseconds as ``HH:MM:SS`` or ``HH:MM:SS.mmm``."""
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, ms = divmod(rem, 1_000)
    base = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{base}.{ms:03d}" if with_ms else base
