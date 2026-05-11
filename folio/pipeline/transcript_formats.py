"""Transcript-native text normalization for caption formats."""

from __future__ import annotations

import html
import re

TRANSCRIPT_FORMAT_EXTENSIONS = frozenset({".vtt", ".srt"})

_TIMING_LINE_RE = re.compile(
    r"^\s*"
    r"(?P<start>(?:\d{2}:)?\d{2}:\d{2}[\.,]\d{3})"
    r"\s+-->\s+"
    r"(?P<end>(?:\d{2}:)?\d{2}:\d{2}[\.,]\d{3})"
    r"(?:\s+.*)?$"
)
_VOICE_TAG_RE = re.compile(r"<v(?:\.[^>\s]+)?\s+([^>]+)>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_SPEAKER_PREFIX_RE = re.compile(r"^(?:[A-Z][\w .'\-/]{0,60}|Speaker \d+):\s+\S")


def normalize_transcript_text(text: str, extension: str) -> str:
    """Normalize VTT/SRT caption text into transcript-like plain text."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    extension = extension.lower()
    if extension == ".vtt":
        return _normalize_blocks(normalized, skip_vtt_control_blocks=True)
    if extension == ".srt":
        return _normalize_blocks(normalized, skip_vtt_control_blocks=False)
    raise ValueError(f"Unsupported transcript format: {extension}")


def _normalize_blocks(text: str, *, skip_vtt_control_blocks: bool) -> str:
    lines: list[str] = []
    for block in _split_blocks(text):
        if not block:
            continue

        timing_index = _find_timing_line(block)
        control_kind = _vtt_control_kind(block) if skip_vtt_control_blocks else ""
        if control_kind in {"NOTE", "STYLE", "REGION"}:
            continue
        if control_kind == "WEBVTT" and timing_index is None:
            continue
        if timing_index is None:
            continue

        timing = _TIMING_LINE_RE.match(block[timing_index])
        if timing is None:
            continue

        start = _normalize_timestamp(timing.group("start"))
        end = _normalize_timestamp(timing.group("end"))
        for utterance in _cue_utterances(block[timing_index + 1:]):
            lines.append(f"[{start} - {end}] {utterance}")

    return "\n".join(lines)


def _split_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip():
            current.append(line.strip("\ufeff"))
            continue
        if current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _vtt_control_kind(block: list[str]) -> str:
    first = block[0].lstrip("\ufeff").strip()
    upper = first.upper()
    if upper.startswith("WEBVTT"):
        return "WEBVTT"
    if upper.startswith("NOTE"):
        return "NOTE"
    if upper in {"STYLE", "REGION"}:
        return upper
    return ""


def _find_timing_line(block: list[str]) -> int | None:
    for index, line in enumerate(block):
        if _TIMING_LINE_RE.match(line):
            return index
    return None


def _normalize_timestamp(value: str) -> str:
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) == 2:
        hours = "00"
        minutes, seconds = parts
    else:
        hours, minutes, seconds = parts
    return f"{int(hours):02d}:{int(minutes):02d}:{seconds}"


def _cue_utterances(text_lines: list[str]) -> list[str]:
    cleaned_lines = [
        cleaned
        for cleaned in (_clean_caption_text(line) for line in text_lines)
        if cleaned
    ]
    if not cleaned_lines:
        return []

    utterances: list[str] = []
    current: list[str] = []
    for line in cleaned_lines:
        if current and _SPEAKER_PREFIX_RE.match(line):
            utterances.append(" ".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        utterances.append(" ".join(current))
    return utterances


def _clean_caption_text(line: str) -> str:
    voice_match = _VOICE_TAG_RE.search(line)
    speaker = _clean_speaker(voice_match.group(1)) if voice_match else ""
    cleaned = _VOICE_TAG_RE.sub("", line)
    cleaned = _TAG_RE.sub("", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if speaker and cleaned:
        return f"{speaker}: {cleaned}"
    return cleaned


def _clean_speaker(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned.rstrip(":")
