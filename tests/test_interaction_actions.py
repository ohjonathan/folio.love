"""Tests for action item extraction and rendering."""

from __future__ import annotations

from folio.output.interaction_markdown import assemble_interaction
from folio.pipeline import interaction_analysis as interaction_analysis_module
from folio.pipeline.interaction_analysis import InteractionAnalysisResult, InteractionFinding
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


def test_action_items_are_coerced_validated_and_counted():
    payload = {
        "summary": "The call closed with a follow-up.",
        "tags": ["follow-up"],
        "findings": {
            "claims": [],
            "data_points": [],
            "decisions": [],
            "open_questions": [],
            "action_items": [
                {
                    "statement": "Jed will come back with next steps.",
                    "quote": "come back to you with some next steps",
                    "element_type": "action",
                    "confidence": "high",
                    "speaker": "Jed Cairo",
                    "timestamp": "00:23:30",
                    "owner": "Jed Cairo",
                    "due": "next couple of business days",
                }
            ],
        },
        "entities": {},
        "notable_quotes": [],
        "warnings": [],
    }

    result = interaction_analysis_module._coerce_result(
        payload,
        "00:23:30 Jed Cairo\nLet me digest the conversation and come back to you with some next steps.",
        pass_strategy="single_pass",
        subtype="expert_interview",
    )

    assert result.action_items[0].element_type == "action"
    assert result.action_items[0].owner == "Jed Cairo"
    assert result.action_items[0].due == "next couple of business days"
    assert result.action_items[0].validated is True
    assert result.grounding_summary["total_claims"] == 1
    assert result.review_status == "clean"


def test_action_items_render_as_next_steps_with_owner_and_due():
    result = InteractionAnalysisResult(
        summary="The interview closed with a commitment.",
        action_items=[
            InteractionFinding(
                statement="Jed will return with offer thinking.",
                quote="come back to you with some thinking on an offer soon",
                element_type="action",
                confidence="high",
                speaker="Jed Cairo",
                timestamp="00:23:35",
                owner="Jed Cairo",
                due="next couple of business days",
                validated=True,
            )
        ],
        review_status="clean",
        review_flags=[],
    )

    markdown = assemble_interaction(
        title="Jed Cairo Interview",
        frontmatter="---\nid: test\n---",
        source_display_path="../../../transcripts/jed.txt",
        version_info=_version_info(),
        analysis_result=result,
        raw_transcript="00:23:35 Jed Cairo\ncome back to you with some thinking on an offer soon",
        subtype="expert_interview",
    )

    assert "### Next Steps" in markdown
    assert "### Action Items" not in markdown
    assert "owner: Jed Cairo" in markdown
    assert "due: next couple of business days" in markdown


def test_empty_action_bucket_omits_action_header():
    result = InteractionAnalysisResult(summary="No actions.")

    markdown = assemble_interaction(
        title="Internal Sync",
        frontmatter="---\nid: test\n---",
        source_display_path="../../../transcripts/sync.txt",
        version_info=_version_info(),
        analysis_result=result,
        raw_transcript="No follow-ups were discussed.",
        subtype="internal_sync",
    )

    assert "### Next Steps" not in markdown
    assert "### Action Items" not in markdown
