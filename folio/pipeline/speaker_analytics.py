"""Deterministic speaker analytics for interaction transcripts."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Iterable

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_BRACKET_TURN_RE = re.compile(
    r"^\[(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)"
    r"\s+-\s+"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\]\s*"
    r"(?P<speaker>[A-Z][\w .'\-/]{0,80}|Speaker \d+):\s*"
    r"(?P<text>.+?)\s*$"
)
_TIMESTAMP_HEADER_RE = re.compile(
    r"^(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\s+"
    r"(?P<speaker>[A-Z][\w .'\-/]{0,80}|Speaker \d+)\s*$"
)
_SPEAKER_KEY_RE = re.compile(r"[^a-z0-9]+")
_DEFAULT_LAST_TURN_WPM = 150


@dataclass(frozen=True)
class Turn:
    """One contiguous speaker turn extracted from a transcript."""

    speaker: str
    text: str
    start_seconds: float
    end_seconds: float | None
    timestamp: str


@dataclass(frozen=True)
class TurnStats:
    """Aggregate stats for one speaker."""

    speaker: str
    word_count: int
    word_share: float
    turn_count: int
    avg_words_per_turn: float
    longest_turn_words: int
    longest_turn_timestamp: str
    talk_time_seconds: int
    talk_share: float
    first_turn_timestamp: str
    last_turn_timestamp: str

    def to_frontmatter(self) -> dict:
        return {
            "speaker": self.speaker,
            "word_count": self.word_count,
            "word_share": self.word_share,
            "turn_count": self.turn_count,
            "avg_words_per_turn": self.avg_words_per_turn,
            "longest_turn_words": self.longest_turn_words,
            "longest_turn_timestamp": self.longest_turn_timestamp,
            "talk_time_seconds": self.talk_time_seconds,
            "talk_share": self.talk_share,
            "first_turn_timestamp": self.first_turn_timestamp,
            "last_turn_timestamp": self.last_turn_timestamp,
        }


@dataclass(frozen=True)
class SpeakerStats:
    """Per-speaker and aggregate interaction analytics."""

    per_speaker: dict[str, TurnStats]
    total_words: int
    total_duration_seconds: int
    speaker_count: int
    balance_score: float
    dominant_speaker: str

    def to_frontmatter(self) -> dict[str, dict]:
        return {
            _speaker_key(stats.speaker): stats.to_frontmatter()
            for stats in self.per_speaker.values()
        }

    def to_summary(self) -> dict:
        return {
            "total_words": self.total_words,
            "duration_seconds": self.total_duration_seconds,
            "speaker_count": self.speaker_count,
            "balance_score": self.balance_score,
            "dominant_speaker": self.dominant_speaker,
            "shares": {
                stats.speaker: stats.word_share
                for stats in self.per_speaker.values()
            },
        }


def parse_turns(source_text: str) -> list[Turn]:
    """Parse timestamped speaker turns from normalized transcript text."""

    bracket_turns = _parse_bracket_turns(source_text)
    if bracket_turns:
        return _merge_adjacent_speaker_turns(bracket_turns)
    return _merge_adjacent_speaker_turns(_parse_timestamp_header_turns(source_text))


def compute_speaker_stats(
    source_text: str | Iterable[Turn],
    *,
    speaker_aliases: dict[str, str] | None = None,
) -> SpeakerStats | None:
    """Compute deterministic speaker stats.

    Returns ``None`` when fewer than two timestamped speaker turns are
    available. A single speaker can still be valid if there are multiple turns;
    completely unstructured notes simply skip analytics.
    """

    turns = list(parse_turns(source_text) if isinstance(source_text, str) else source_text)
    if speaker_aliases:
        turns = [
            replace(
                turn,
                speaker=_canonical_speaker(turn.speaker, speaker_aliases),
            )
            for turn in turns
        ]
    turns = [turn for turn in turns if turn.text.strip()]
    if not turns:
        return None

    timed_turns = _with_inferred_end_times(turns)
    totals_by_speaker: dict[str, list[tuple[Turn, int, int]]] = {}
    for turn, word_count, duration_seconds in timed_turns:
        totals_by_speaker.setdefault(turn.speaker, []).append(
            (turn, word_count, duration_seconds)
        )

    total_words = sum(word_count for _, word_count, _ in timed_turns)
    if total_words <= 0:
        return None
    first_start = min(turn.start_seconds for turn, _, _ in timed_turns)
    last_end = max(turn.end_seconds or turn.start_seconds for turn, _, _ in timed_turns)
    total_duration_seconds = max(1, round(last_end - first_start))
    total_talk_seconds = max(1, sum(duration for _, _, duration in timed_turns))

    per_speaker: dict[str, TurnStats] = {}
    for speaker, speaker_turns in totals_by_speaker.items():
        speaker_word_counts = [word_count for _, word_count, _ in speaker_turns]
        word_count = sum(speaker_word_counts)
        talk_time_seconds = sum(duration for _, _, duration in speaker_turns)
        longest_index, longest_turn_words = max(
            enumerate(speaker_word_counts),
            key=lambda item: item[1],
        )
        longest_turn = speaker_turns[longest_index][0]
        first_turn = speaker_turns[0][0]
        last_turn = speaker_turns[-1][0]
        turn_count = len(speaker_turns)
        per_speaker[speaker] = TurnStats(
            speaker=speaker,
            word_count=word_count,
            word_share=round(word_count / total_words, 4),
            turn_count=turn_count,
            avg_words_per_turn=round(word_count / turn_count, 1),
            longest_turn_words=longest_turn_words,
            longest_turn_timestamp=longest_turn.timestamp,
            talk_time_seconds=talk_time_seconds,
            talk_share=round(talk_time_seconds / total_talk_seconds, 4),
            first_turn_timestamp=first_turn.timestamp,
            last_turn_timestamp=last_turn.timestamp,
        )

    ordered = dict(
        sorted(
            per_speaker.items(),
            key=lambda item: (-item[1].word_count, item[0].lower()),
        )
    )
    dominant_speaker = next(iter(ordered.values())).speaker
    return SpeakerStats(
        per_speaker=ordered,
        total_words=total_words,
        total_duration_seconds=total_duration_seconds,
        speaker_count=len(ordered),
        balance_score=round(1.0 - _gini([stats.word_share for stats in ordered.values()]), 4),
        dominant_speaker=dominant_speaker,
    )


def format_duration(seconds: int) -> str:
    """Format seconds as compact human-readable minutes/seconds."""

    seconds = max(0, int(seconds))
    minutes, remainder = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {remainder:02d}s"
    return f"{remainder}s"


def _canonical_speaker(speaker: str, speaker_aliases: dict[str, str]) -> str:
    return speaker_aliases.get(speaker.strip().lower(), speaker)


def _parse_bracket_turns(source_text: str) -> list[Turn]:
    turns: list[Turn] = []
    for line in source_text.splitlines():
        match = _BRACKET_TURN_RE.match(line.strip())
        if not match:
            continue
        speaker = _clean_speaker(match.group("speaker"))
        text = match.group("text").strip()
        if not speaker or not text:
            continue
        timestamp = _normalize_timestamp_label(match.group("start"))
        turns.append(
            Turn(
                speaker=speaker,
                text=text,
                start_seconds=_parse_timestamp_seconds(match.group("start")),
                end_seconds=_parse_timestamp_seconds(match.group("end")),
                timestamp=timestamp,
            )
        )
    return turns


def _parse_timestamp_header_turns(source_text: str) -> list[Turn]:
    turns: list[Turn] = []
    current_start: float | None = None
    current_timestamp = ""
    current_speaker = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_start, current_timestamp, current_speaker, current_lines
        text = " ".join(line.strip() for line in current_lines if line.strip())
        if current_start is not None and current_speaker and text:
            turns.append(
                Turn(
                    speaker=current_speaker,
                    text=text,
                    start_seconds=current_start,
                    end_seconds=None,
                    timestamp=current_timestamp,
                )
            )
        current_start = None
        current_timestamp = ""
        current_speaker = ""
        current_lines = []

    for line in source_text.splitlines():
        match = _TIMESTAMP_HEADER_RE.match(line.strip())
        if match:
            flush()
            current_start = _parse_timestamp_seconds(match.group("start"))
            current_timestamp = _normalize_timestamp_label(match.group("start"))
            current_speaker = _clean_speaker(match.group("speaker"))
            continue
        if current_start is not None:
            current_lines.append(line)
    flush()
    return turns


def _merge_adjacent_speaker_turns(turns: list[Turn]) -> list[Turn]:
    merged: list[Turn] = []
    for turn in turns:
        if not merged or merged[-1].speaker.lower() != turn.speaker.lower():
            merged.append(turn)
            continue
        previous = merged[-1]
        merged[-1] = Turn(
            speaker=previous.speaker,
            text=f"{previous.text} {turn.text}".strip(),
            start_seconds=previous.start_seconds,
            end_seconds=turn.end_seconds,
            timestamp=previous.timestamp,
        )
    return merged


def _with_inferred_end_times(turns: list[Turn]) -> list[tuple[Turn, int, int]]:
    timed: list[tuple[Turn, int, int]] = []
    for index, turn in enumerate(turns):
        word_count = len(_WORD_RE.findall(turn.text))
        if turn.end_seconds is not None and turn.end_seconds > turn.start_seconds:
            end_seconds = turn.end_seconds
        elif index + 1 < len(turns) and turns[index + 1].start_seconds > turn.start_seconds:
            end_seconds = turns[index + 1].start_seconds
        else:
            end_seconds = turn.start_seconds + _estimate_turn_seconds(word_count)
        duration_seconds = max(1, round(end_seconds - turn.start_seconds))
        timed_turn = Turn(
            speaker=turn.speaker,
            text=turn.text,
            start_seconds=turn.start_seconds,
            end_seconds=end_seconds,
            timestamp=turn.timestamp,
        )
        timed.append((timed_turn, word_count, duration_seconds))
    return timed


def _estimate_turn_seconds(word_count: int) -> float:
    return max(1.0, (max(1, word_count) / _DEFAULT_LAST_TURN_WPM) * 60.0)


def _parse_timestamp_seconds(value: str) -> float:
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) == 2:
        hours = 0
        minutes = int(parts[0])
        seconds = float(parts[1])
    elif len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
    else:
        raise ValueError(f"Unsupported timestamp: {value}")
    return (hours * 3600) + (minutes * 60) + seconds


def _normalize_timestamp_label(value: str) -> str:
    total = _parse_timestamp_seconds(value)
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    seconds = total % 60
    if seconds.is_integer():
        seconds_text = f"{int(seconds):02d}"
    else:
        seconds_text = f"{seconds:06.3f}".rstrip("0").rstrip(".")
    return f"{hours:02d}:{minutes:02d}:{seconds_text}"


def _clean_speaker(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().rstrip(":")


def _speaker_key(value: str) -> str:
    slug = _SPEAKER_KEY_RE.sub("_", value.strip().lower()).strip("_")
    return slug or "speaker"


def _gini(values: list[float]) -> float:
    if not values:
        return 0.0
    total = sum(values)
    if total <= 0:
        return 0.0
    diff_sum = 0.0
    for left in values:
        for right in values:
            diff_sum += abs(left - right)
    return diff_sum / (2 * len(values) * total)
