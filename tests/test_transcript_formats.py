"""Tests for transcript-native caption normalization."""

from __future__ import annotations

from pathlib import Path

from folio.pipeline.transcript_formats import normalize_transcript_text


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "ingest"


def test_vtt_normalization_strips_transport_markup_and_preserves_speakers():
    text = (FIXTURE_DIR / "meeting_export.vtt").read_text()

    normalized = normalize_transcript_text(text, ".vtt")

    assert "WEBVTT" not in normalized
    assert "NOTE" not in normalized
    assert "STYLE" not in normalized
    assert "align:start" not in normalized
    assert "<b>" not in normalized
    assert "[00:00:01.200 - 00:00:04.000] Jane Smith: We reduced downtime from 12 hours to 2 hours." in normalized
    assert "[00:00:05.000 - 00:00:07.500] Johnny Oh: ServiceNow remained the operational backbone." in normalized
    assert "[00:00:08.000 - 00:00:10.250] Speaker 3: Incident triage still needs cleaner ownership." in normalized


def test_srt_normalization_strips_cue_numbers_and_joins_wrapped_lines():
    text = (FIXTURE_DIR / "meeting_export.srt").read_text()

    normalized = normalize_transcript_text(text, ".srt")

    assert "\n1\n" not in normalized
    assert "-->" not in normalized
    assert "[00:00:01.200 - 00:00:04.000] Jane Smith: We reduced downtime from 12 hours to 2 hours." in normalized
    assert "[00:00:05.000 - 00:00:07.500] Johnny Oh: Add a reporting checkpoint." in normalized
    assert "[00:00:08.000 - 00:00:10.250] ServiceNow remained the operational backbone." in normalized


def test_vtt_multispeaker_cue_renders_one_line_per_utterance():
    text = """WEBVTT

00:01.000 --> 00:04.000
<v Jane Smith>Hello there.
<v Johnny Oh>Thanks for joining.
"""

    normalized = normalize_transcript_text(text, ".vtt")

    assert normalized.splitlines() == [
        "[00:00:01.000 - 00:00:04.000] Jane Smith: Hello there.",
        "[00:00:01.000 - 00:00:04.000] Johnny Oh: Thanks for joining.",
    ]


def test_vtt_cue_range_renders_canonical_timestamps():
    # Issue #75 representative cue: both ends stay canonical HH:MM:SS.mmm so the
    # downstream analysis prompt never sees malformed timestamps.
    text = """WEBVTT

00:03:03.650 --> 00:03:18.819
<v Jane Smith>We reduced downtime.
"""

    normalized = normalize_transcript_text(text, ".vtt")

    assert normalized.splitlines() == [
        "[00:03:03.650 - 00:03:18.819] Jane Smith: We reduced downtime.",
    ]
