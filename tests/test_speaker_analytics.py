"""Tests for deterministic speaker analytics."""

from __future__ import annotations

import yaml

from folio.output.frontmatter import generate_interaction
from folio.ingest import _apply_speaker_analytics_state
from folio.pipeline.interaction_analysis import InteractionAnalysisResult
from folio.pipeline.speaker_analytics import compute_speaker_stats, parse_turns
from folio.tracking.registry import RegistryEntry
from folio.tracking.versions import ChangeSet, VersionInfo


def _version_info() -> VersionInfo:
    return VersionInfo(
        version=1,
        timestamp="2026-04-24T12:00:00Z",
        source_hash="abc123def456",
        source_path="transcripts/interview.txt",
        note=None,
        slide_count=1,
        changes=ChangeSet(added=[1]),
    )


def _parse_frontmatter(fm: str) -> dict:
    return yaml.safe_load(fm.split("---", 2)[1].strip())


def test_parse_turns_merges_adjacent_caption_cues_for_same_speaker():
    text = "\n".join(
        [
            "[00:00:00.000 - 00:00:02.000] Alice Lee: First cue.",
            "[00:00:02.000 - 00:00:04.000] Alice Lee: Second cue.",
            "[00:00:04.000 - 00:00:07.000] Bob Chen: Other words here.",
        ]
    )

    turns = parse_turns(text)

    assert len(turns) == 2
    assert turns[0].speaker == "Alice Lee"
    assert turns[0].text == "First cue. Second cue."
    assert turns[0].end_seconds == 4.0


def test_compute_speaker_stats_from_timestamp_header_transcript():
    text = "\n".join(
        [
            "00:00:00 Alice Lee",
            "alpha beta gamma",
            "00:00:03 Bob Chen",
            "one two three four five",
            "00:00:09 Alice Lee",
            "delta epsilon",
        ]
    )

    stats = compute_speaker_stats(text)

    assert stats is not None
    assert stats.total_words == 10
    assert stats.total_duration_seconds == 10
    assert stats.speaker_count == 2
    assert stats.balance_score == 1.0
    assert stats.dominant_speaker == "Alice Lee"
    assert stats.per_speaker["Alice Lee"].word_count == 5
    assert stats.per_speaker["Alice Lee"].turn_count == 2
    assert stats.per_speaker["Bob Chen"].longest_turn_words == 5
    assert stats.per_speaker["Bob Chen"].longest_turn_timestamp == "00:00:03"


def test_speaker_stats_frontmatter_and_registry_summary():
    stats = compute_speaker_stats(
        "\n".join(
            [
                "00:00:00 Alice Lee",
                "alpha beta gamma",
                "00:00:03 Bob Chen",
                "one two three four five",
            ]
        )
    )
    assert stats is not None
    result = InteractionAnalysisResult(
        summary="Structured interview.",
        review_status="clean",
        review_flags=[],
        speaker_stats=stats,
    )

    fm = _parse_frontmatter(
        generate_interaction(
            interaction_id="client_interview_20260424_alice_bob",
            title="Alice Bob Interview",
            subtype="expert_interview",
            event_date="2026-04-24",
            version_info=_version_info(),
            source_transcript="../../../transcripts/interview.txt",
            source_hash="abc123def456",
            analysis_result=result,
        )
    )

    assert fm["speakers"]["alice_lee"]["word_count"] == 3
    assert fm["total_words"] == 8
    assert fm["speaker_summary"]["dominant_speaker"] == "Bob Chen"

    entry = RegistryEntry(
        id="client_interview_20260424_alice_bob",
        title="Alice Bob Interview",
        markdown_path="interactions/alice_bob.md",
        deck_dir="interactions",
        type="interaction",
        speaker_summary=stats.to_summary(),
    )
    assert entry.to_dict()["speaker_summary"]["speaker_count"] == 2


def test_speaker_stats_merge_existing_entity_aliases():
    stats = compute_speaker_stats(
        "\n".join(
            [
                "00:00:00 J. Oh",
                "alpha beta",
                "00:00:02 Jonathan Oh",
                "gamma delta epsilon",
            ]
        ),
        speaker_aliases={"j. oh": "Jonathan Oh"},
    )

    assert stats is not None
    assert stats.speaker_count == 1
    assert stats.total_words == 5
    assert stats.per_speaker["Jonathan Oh"].turn_count == 2


def test_missing_speaker_stats_sets_review_flag_without_llm_dependency():
    result = InteractionAnalysisResult(summary="Free-form note.", review_status="clean")

    _apply_speaker_analytics_state(result, None)

    assert result.speaker_stats is None
    assert result.review_status == "flagged"
    assert result.review_flags == ["speaker_analytics_unavailable"]
