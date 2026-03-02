"""Integration tests for the full conversion pipeline with mocked Anthropic client."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from folio.config import FolioConfig
from folio.converter import FolioConverter
from folio.pipeline.analysis import SlideAnalysis
from folio.pipeline.text import SlideText
from folio.output.frontmatter import _compute_grounding_summary


def _mock_anthropic_response(text: str):
    """Create a mock Anthropic API response."""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


MOCK_PASS1_RESPONSES = {
    1: """Slide Type: title
Framework: none
Visual Description: Title slide with company name and quarter indicator.
Key Data: Q1 2026
Main Insight: Opening slide for quarterly market review.
Evidence:
- Claim: Quarter identification
  Quote: "Q1 2026 Review"
  Element: body
  Confidence: high""",
    2: """Slide Type: data
Framework: tam-sam-som
Visual Description: Revenue metrics with TAM/SAM/SOM breakdown and growth projections.
Key Data: TAM $4.2B, SAM $1.2B, SOM $300M, CAGR 12%, Revenue $10M
Main Insight: Strong market opportunity with clear path to 5% market share.
Evidence:
- Claim: Market sizing
  Quote: "TAM $4.2B"
  Element: body
  Confidence: high
- Claim: Growth projection
  Quote: "CAGR 12% projected through 2028"
  Element: body
  Confidence: high
- Claim: Revenue figure
  Quote: "Revenue $10M in FY2025"
  Element: body
  Confidence: high""",
    3: """Slide Type: next-steps
Framework: none
Visual Description: Simple text slide with action items.
Key Data: None
Main Insight: Follow-up actions for client engagement.
Evidence:
- Claim: Action item
  Quote: "Follow up with client on timeline"
  Element: body
  Confidence: medium""",
}

MOCK_PASS2_RESPONSE = """Evidence:
- Claim: Revenue growth rate
  Quote: "projected $15M in FY2026"
  Element: body
  Confidence: high
- Claim: Expansion strategy
  Quote: "enterprise expansion, product-led growth"
  Element: body
  Confidence: medium
- Claim: International timeline
  Quote: "international markets opening Q3 2026"
  Element: body
  Confidence: high"""


class TestGroundingSummary:
    """Test frontmatter grounding summary computation."""

    def test_basic_summary(self):
        analyses = {
            1: SlideAnalysis(evidence=[
                {"claim": "A", "confidence": "high", "validated": True, "pass": 1},
                {"claim": "B", "confidence": "medium", "validated": False, "pass": 1},
            ]),
            2: SlideAnalysis(evidence=[
                {"claim": "C", "confidence": "low", "validated": True, "pass": 1},
            ]),
        }
        summary = _compute_grounding_summary(analyses)
        assert summary["total_claims"] == 3
        assert summary["high_confidence"] == 1
        assert summary["medium_confidence"] == 1
        assert summary["low_confidence"] == 1
        assert summary["validated"] == 2
        assert summary["unvalidated"] == 1

    def test_multi_pass_summary(self):
        analyses = {
            1: SlideAnalysis(evidence=[
                {"claim": "A", "confidence": "high", "validated": True, "pass": 1},
                {"claim": "B", "confidence": "high", "validated": True, "pass": 2},
            ]),
        }
        summary = _compute_grounding_summary(analyses)
        assert summary["total_claims"] == 2
        assert summary["pass_1_claims"] == 1
        assert summary["pass_2_claims"] == 1
        assert summary["pass_2_slides"] == 1

    def test_empty_analyses(self):
        summary = _compute_grounding_summary({})
        assert summary["total_claims"] == 0

    def test_no_evidence(self):
        analyses = {1: SlideAnalysis(), 2: SlideAnalysis()}
        summary = _compute_grounding_summary(analyses)
        assert summary["total_claims"] == 0


class TestMarkdownEvidenceRendering:
    """Test evidence rendering in markdown output."""

    def test_evidence_in_slide_output(self):
        from folio.output.markdown import _format_slide

        analysis = SlideAnalysis(
            slide_type="data",
            framework="tam-sam-som",
            visual_description="Revenue chart",
            key_data="$10M",
            main_insight="Growing revenue",
            evidence=[
                {"claim": "Revenue", "quote": "$10M", "element_type": "body",
                 "confidence": "high", "pass": 1, "validated": True},
                {"claim": "Growth", "quote": "CAGR 15%", "element_type": "body",
                 "confidence": "medium", "pass": 2, "validated": True},
            ],
        )
        text = SlideText(slide_num=1, full_text="Revenue $10M with CAGR 15%", elements=[])

        output = _format_slide(slide_num=1, text=text, analysis=analysis)

        assert "**Evidence:**" in output
        assert '**Revenue (high):**' in output
        assert '"$10M"' in output
        assert '*(body)*' in output
        # Pass 2 evidence shows pass label
        assert "pass 2" in output

    def test_no_evidence_no_block(self):
        from folio.output.markdown import _format_slide

        analysis = SlideAnalysis(
            slide_type="title",
            framework="none",
            visual_description="Title slide",
        )
        output = _format_slide(slide_num=1, text=None, analysis=analysis)
        assert "**Evidence:**" not in output


class TestPipelineIntegration:
    """End-to-end pipeline tests with mocked Anthropic client."""

    def _create_mock_client(self, call_count_ref: list):
        """Create a mock Anthropic client that returns canned responses."""
        mock_client = MagicMock()
        slide_counter = [0]

        def mock_create(**kwargs):
            slide_counter[0] += 1
            call_count_ref.append(slide_counter[0])
            slide_num = slide_counter[0]

            # Determine if this is a pass 1 or pass 2 call
            prompt_text = ""
            for msg in kwargs.get("messages", []):
                for content in msg.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "text":
                        prompt_text = content.get("text", "")

            if "previously analyzed" in prompt_text.lower():
                # This is a pass 2 call
                return _mock_anthropic_response(MOCK_PASS2_RESPONSE)
            else:
                # Pass 1 - use slide number
                response_num = min(slide_num, 3)
                return _mock_anthropic_response(MOCK_PASS1_RESPONSES[response_num])

        mock_client.messages.create = mock_create
        return mock_client

    @staticmethod
    def _make_unique_png(index: int) -> bytes:
        """Create unique PNG-like bytes for each slide to avoid cache collisions."""
        # Use unique padding per slide for unique hash
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            + bytes([index]) * 16
            + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass1_produces_evidence(self):
        """Test that Pass 1 analysis produces evidence blocks."""
        from folio.pipeline.analysis import analyze_slides

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_paths = []
            for i in range(3):
                img_path = tmpdir / f"slide-{i+1:03d}.png"
                img_path.write_bytes(self._make_unique_png(i + 1))
                image_paths.append(img_path)

            slide_texts = {
                1: SlideText(slide_num=1, full_text="Market Analysis\nQ1 2026 Review", elements=[]),
                2: SlideText(slide_num=2, full_text="TAM $4.2B, SAM $1.2B, SOM $300M. CAGR 12% projected through 2028. Revenue $10M in FY2025", elements=[]),
                3: SlideText(slide_num=3, full_text="Follow up with client on timeline", elements=[]),
            }

            calls = []
            mock_client = self._create_mock_client(calls)

            with patch("anthropic.Anthropic", return_value=mock_client):
                results = analyze_slides(
                    image_paths,
                    model="test-model",
                    slide_texts=slide_texts,
                )

            assert len(results) == 3
            # Slide 1: title with 1 evidence item
            assert results[1].slide_type == "title"
            assert len(results[1].evidence) == 1
            # Slide 2: data with 3 evidence items
            assert results[2].slide_type == "data"
            assert len(results[2].evidence) == 3
            assert results[2].framework == "tam-sam-som"
            # Slide 3: next-steps with 1 evidence item
            assert len(results[3].evidence) == 1

            # Check that evidence was validated
            for ev in results[2].evidence:
                assert ev["validated"] is True  # All quotes match source text

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass2_adds_evidence(self):
        """Test that Pass 2 adds additional evidence to dense slides."""
        from folio.pipeline.analysis import analyze_slides, analyze_slides_deep

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image_paths = []
            for i in range(3):
                img_path = tmpdir / f"slide-{i+1:03d}.png"
                img_path.write_bytes(self._make_unique_png(i + 1))
                image_paths.append(img_path)

            # Make slide 2 have enough text to be high density
            long_text = (
                "TAM $4.2B, SAM $1.2B, SOM $300M. "
                "CAGR 12% projected through 2028. "
                "Revenue $10M in FY2025, projected $15M in FY2026. "
                "Key drivers: enterprise expansion, product-led growth, "
                "international markets opening Q3 2026. "
                + " ".join(["additional context word"] * 40)
            )

            slide_texts = {
                1: SlideText(slide_num=1, full_text="Market Analysis\nQ1 2026 Review", elements=[]),
                2: SlideText(slide_num=2, full_text=long_text, elements=[]),
                3: SlideText(slide_num=3, full_text="Follow up with client on timeline", elements=[]),
            }

            calls = []
            mock_client = self._create_mock_client(calls)

            with patch("anthropic.Anthropic", return_value=mock_client):
                # Pass 1 (no cache to keep it clean)
                pass1_results = analyze_slides(
                    image_paths,
                    model="test-model",
                    slide_texts=slide_texts,
                )

                pass1_evidence_count = sum(
                    len(a.evidence) for a in pass1_results.values()
                )

                # Pass 2
                pass2_results = analyze_slides_deep(
                    pass1_results=pass1_results,
                    slide_texts=slide_texts,
                    image_paths=image_paths,
                    model="test-model",
                    density_threshold=2.0,
                )

            pass2_evidence_count = sum(
                len(a.evidence) for a in pass2_results.values()
            )

            # Pass 2 should add more evidence (at least on slide 2)
            assert pass2_evidence_count >= pass1_evidence_count

            # Slide 2's evidence should have pass 2 items
            slide2_passes = set(ev.get("pass", 1) for ev in pass2_results[2].evidence)
            assert 2 in slide2_passes

            # Slide 1 and 3 should be unchanged (low density)
            assert pass2_results[1].evidence == pass1_results[1].evidence
            assert pass2_results[3].evidence == pass1_results[3].evidence

    def test_frontmatter_grounding_populated(self):
        """Test that frontmatter includes grounding_summary when evidence exists."""
        import yaml

        from folio.output.frontmatter import generate
        from folio.tracking.versions import VersionInfo, ChangeSet

        analyses = {
            1: SlideAnalysis(
                slide_type="data",
                framework="tam-sam-som",
                evidence=[
                    {"claim": "TAM", "quote": "$4.2B", "confidence": "high",
                     "validated": True, "pass": 1},
                    {"claim": "Growth", "quote": "CAGR 12%", "confidence": "high",
                     "validated": True, "pass": 2},
                ],
            ),
        }
        version_info = VersionInfo(
            version=1,
            timestamp="2026-01-01T00:00:00Z",
            source_hash="abc123",
            source_path="deck.pptx",
            note=None,
            slide_count=1,
            changes=ChangeSet(added=[1]),
        )

        fm = generate(
            title="Test Deck",
            deck_id="test_id",
            source_relative_path="deck.pptx",
            source_hash="abc123",
            version_info=version_info,
            analyses=analyses,
        )

        # Parse the YAML
        content = fm.strip("---").strip()
        parsed = yaml.safe_load(content)

        assert "grounding_summary" in parsed
        gs = parsed["grounding_summary"]
        assert gs["total_claims"] == 2
        assert gs["high_confidence"] == 2
        assert gs["validated"] == 2
        assert gs["pass_1_claims"] == 1
        assert gs["pass_2_claims"] == 1


class TestEvidenceVerificationIndicator:
    """Test that unverified evidence gets a visual indicator in markdown."""

    def test_unverified_evidence_indicator(self):
        from folio.output.markdown import _format_slide

        analysis = SlideAnalysis(
            slide_type="data",
            framework="none",
            visual_description="Chart",
            key_data="$10M",
            main_insight="Revenue",
            evidence=[
                {"claim": "Revenue", "quote": "$10M", "element_type": "body",
                 "confidence": "high", "pass": 1, "validated": False},
            ],
        )
        output = _format_slide(slide_num=1, text=None, analysis=analysis)
        assert "[unverified]" in output

    def test_verified_evidence_no_indicator(self):
        from folio.output.markdown import _format_slide

        analysis = SlideAnalysis(
            slide_type="data",
            framework="none",
            visual_description="Chart",
            key_data="$10M",
            main_insight="Revenue",
            evidence=[
                {"claim": "Revenue", "quote": "$10M", "element_type": "body",
                 "confidence": "high", "pass": 1, "validated": True},
            ],
        )
        output = _format_slide(slide_num=1, text=None, analysis=analysis)
        assert "[unverified]" not in output
