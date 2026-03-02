"""Tests for source grounding: evidence parsing, validation, backward compat."""

import pytest

from folio.pipeline.analysis import (
    SlideAnalysis,
    _parse_analysis,
    _parse_evidence,
    _validate_evidence,
    _compute_density_score,
    _deduplicate_evidence,
)
from folio.pipeline.text import SlideText


class TestParseAnalysis:
    """Test parsing of grounded LLM response format."""

    def test_parse_full_grounded_response(self):
        raw = """Slide Type: framework
Framework: scr
Visual Description: A structured presentation showing the SCR framework applied to market entry strategy.
Key Data: TAM $4.2B, CAGR 12%, Market share target 5%
Main Insight: The SCR framework reveals a clear market opportunity worth pursuing.
Evidence:
- Claim: Framework detection
  Quote: "SCR structure applied to market entry"
  Element: body
  Confidence: high
- Claim: Market sizing
  Quote: "TAM $4.2B"
  Element: body
  Confidence: high
- Claim: Growth rate
  Quote: "CAGR 12%"
  Element: body
  Confidence: medium"""

        analysis = _parse_analysis(raw)
        assert analysis.slide_type == "framework"
        assert analysis.framework == "scr"
        assert "TAM $4.2B" in analysis.key_data
        assert len(analysis.evidence) == 3
        assert analysis.evidence[0]["claim"] == "Framework detection"
        assert analysis.evidence[0]["confidence"] == "high"
        assert analysis.evidence[1]["quote"] == "TAM $4.2B"
        assert analysis.evidence[2]["confidence"] == "medium"

    def test_parse_response_without_evidence(self):
        raw = """Slide Type: title
Framework: none
Visual Description: A simple title slide with company logo.
Key Data: None
Main Insight: Opening slide for the presentation."""

        analysis = _parse_analysis(raw)
        assert analysis.slide_type == "title"
        assert analysis.framework == "none"
        assert analysis.evidence == []

    def test_parse_single_evidence_item(self):
        raw = """Slide Type: data
Framework: none
Visual Description: Chart showing revenue growth.
Key Data: Revenue $10M
Main Insight: Revenue is growing.
Evidence:
- Claim: Revenue figure
  Quote: "Revenue $10M"
  Element: title
  Confidence: high"""

        analysis = _parse_analysis(raw)
        assert len(analysis.evidence) == 1
        assert analysis.evidence[0]["element_type"] == "title"

    def test_evidence_defaults(self):
        """Evidence with missing fields gets sensible defaults."""
        raw = """Slide Type: data
Framework: none
Visual Description: Chart.
Key Data: None
Main Insight: Data slide.
Evidence:
- Claim: Some claim"""

        analysis = _parse_analysis(raw)
        assert len(analysis.evidence) == 1
        ev = analysis.evidence[0]
        assert ev["claim"] == "Some claim"
        assert ev["element_type"] == "body"
        assert ev["confidence"] == "medium"
        assert ev["validated"] is False


class TestParseEvidence:
    """Test the evidence parsing state machine."""

    def test_empty_text(self):
        assert _parse_evidence("No evidence section here") == []

    def test_multiple_items(self):
        text = """Evidence:
- Claim: First claim
  Quote: "first quote"
  Element: title
  Confidence: high
- Claim: Second claim
  Quote: "second quote"
  Element: body
  Confidence: low"""

        items = _parse_evidence(text)
        assert len(items) == 2
        assert items[0]["claim"] == "First claim"
        assert items[0]["quote"] == "first quote"
        assert items[1]["claim"] == "Second claim"
        assert items[1]["confidence"] == "low"

    def test_normalizes_confidence(self):
        text = """Evidence:
- Claim: Test
  Quote: "test"
  Element: body
  Confidence: VERY_HIGH"""

        items = _parse_evidence(text)
        assert items[0]["confidence"] == "medium"  # invalid → default

    def test_normalizes_element_type(self):
        text = """Evidence:
- Claim: Test
  Quote: "test"
  Element: chart
  Confidence: high"""

        items = _parse_evidence(text)
        assert items[0]["element_type"] == "body"  # invalid → default


class TestValidateEvidence:
    """Test evidence validation against slide text."""

    def test_exact_substring_match(self):
        slide_text = SlideText(
            slide_num=1,
            full_text="TAM $4.2B with CAGR of 12% projected growth",
            elements=[],
        )
        evidence = [
            {"claim": "Market sizing", "quote": "TAM $4.2B", "confidence": "high", "validated": False},
        ]
        _validate_evidence(evidence, slide_text)
        assert evidence[0]["validated"] is True

    def test_case_insensitive_match(self):
        slide_text = SlideText(
            slide_num=1,
            full_text="The Total Addressable Market is large",
            elements=[],
        )
        evidence = [
            {"claim": "TAM ref", "quote": "total addressable market", "confidence": "high", "validated": False},
        ]
        _validate_evidence(evidence, slide_text)
        assert evidence[0]["validated"] is True

    def test_no_match(self):
        slide_text = SlideText(
            slide_num=1,
            full_text="Revenue grew 15% year over year",
            elements=[],
        )
        evidence = [
            {"claim": "Cost reduction", "quote": "costs decreased by 20%", "confidence": "high", "validated": False},
        ]
        _validate_evidence(evidence, slide_text)
        assert evidence[0]["validated"] is False

    def test_word_overlap_match(self):
        """80%+ word overlap should validate even without exact substring."""
        slide_text = SlideText(
            slide_num=1,
            full_text="The market opportunity is approximately $4.2 billion in total",
            elements=[],
        )
        evidence = [
            {"claim": "Market size", "quote": "market opportunity approximately $4.2 billion total",
             "confidence": "high", "validated": False},
        ]
        _validate_evidence(evidence, slide_text)
        assert evidence[0]["validated"] is True

    def test_empty_quote(self):
        slide_text = SlideText(slide_num=1, full_text="Some text", elements=[])
        evidence = [{"claim": "Test", "quote": "", "confidence": "high", "validated": False}]
        _validate_evidence(evidence, slide_text)
        assert evidence[0]["validated"] is False


class TestSlideAnalysisBackwardCompat:
    """Test backward compatibility with old cache format."""

    def test_from_dict_without_evidence(self):
        """Old cache entries have no evidence field."""
        old_cache = {
            "slide_type": "data",
            "framework": "none",
            "visual_description": "A chart",
            "key_data": "Revenue $10M",
            "main_insight": "Growing revenue",
        }
        analysis = SlideAnalysis.from_dict(old_cache)
        assert analysis.evidence == []
        assert analysis.slide_type == "data"

    def test_to_dict_includes_evidence(self):
        analysis = SlideAnalysis(
            slide_type="framework",
            framework="scr",
            evidence=[{"claim": "Test", "quote": "test", "confidence": "high"}],
        )
        d = analysis.to_dict()
        assert "evidence" in d
        assert len(d["evidence"]) == 1

    def test_round_trip(self):
        original = SlideAnalysis(
            slide_type="data",
            framework="none",
            visual_description="Chart",
            key_data="$10M",
            main_insight="Growth",
            evidence=[
                {"claim": "Revenue", "quote": "$10M", "element_type": "body",
                 "confidence": "high", "validated": True, "pass": 1},
            ],
        )
        d = original.to_dict()
        restored = SlideAnalysis.from_dict(d)
        assert restored.slide_type == original.slide_type
        assert len(restored.evidence) == 1
        assert restored.evidence[0]["validated"] is True


class TestDensityScoring:
    """Test density scoring for second pass selection."""

    def test_low_density_slide(self):
        """Simple title slide should score low."""
        analysis = SlideAnalysis(slide_type="title", framework="none", evidence=[])
        text = SlideText(slide_num=1, full_text="Company Overview", elements=[])
        score = _compute_density_score(analysis, text)
        assert score < 2.0  # Below threshold

    def test_high_density_data_slide(self):
        """Data slide with framework, long text, and evidence should score high."""
        evidence = [
            {"claim": "Revenue", "quote": "Revenue $10M", "confidence": "high"},
            {"claim": "Growth", "quote": "CAGR 15%", "confidence": "high"},
            {"claim": "Market", "quote": "TAM $4.2B", "confidence": "high"},
        ]
        analysis = SlideAnalysis(
            slide_type="data",
            framework="tam-sam-som",
            evidence=evidence,
        )
        long_text = " ".join(["word"] * 200) + ", item1, item2, item3, item4, item5"
        text = SlideText(slide_num=1, full_text=long_text, elements=[])
        score = _compute_density_score(analysis, text)
        assert score >= 2.0  # Above threshold

    def test_medium_density_framework_slide(self):
        """Framework slide with moderate text should be near threshold."""
        evidence = [
            {"claim": "Framework", "quote": "SCR applied", "confidence": "high"},
        ]
        analysis = SlideAnalysis(
            slide_type="framework",
            framework="scr",
            evidence=evidence,
        )
        # 100 words, between 75 and 150
        text = SlideText(
            slide_num=1,
            full_text=" ".join(["word"] * 100),
            elements=[],
        )
        score = _compute_density_score(analysis, text)
        # framework=1.0 + evidence(1*0.3) + words(0.5) + data-heavy(0.5) = 2.3
        assert score >= 2.0

    def test_word_count_thresholds(self):
        """Test the word count scoring thresholds."""
        analysis = SlideAnalysis(slide_type="narrative")

        short = SlideText(slide_num=1, full_text=" ".join(["w"] * 30), elements=[])
        medium = SlideText(slide_num=1, full_text=" ".join(["w"] * 100), elements=[])
        long = SlideText(slide_num=1, full_text=" ".join(["w"] * 200), elements=[])

        score_short = _compute_density_score(analysis, short)
        score_medium = _compute_density_score(analysis, medium)
        score_long = _compute_density_score(analysis, long)

        assert score_medium > score_short
        assert score_long > score_medium

    def test_comma_count_capped(self):
        """Comma scoring should cap at 1.0."""
        analysis = SlideAnalysis(slide_type="narrative")
        # 20 commas → 20 * 0.2 = 4.0 → capped at 1.0
        text = SlideText(
            slide_num=1,
            full_text=", ".join(["item"] * 21),
            elements=[],
        )
        score = _compute_density_score(analysis, text)
        # Comma contribution should be exactly 1.0 (capped)
        assert score <= 3.0  # words + commas + nothing else


class TestDeduplicateEvidence:
    """Test evidence deduplication across passes."""

    def test_no_overlap(self):
        existing = [
            {"claim": "Revenue", "quote": "revenue ten million", "confidence": "high", "pass": 1},
        ]
        new = [
            {"claim": "Growth", "quote": "cagr fifteen percent", "confidence": "high", "pass": 2},
        ]
        merged = _deduplicate_evidence(existing, new)
        assert len(merged) == 2

    def test_duplicate_keeps_higher_confidence(self):
        existing = [
            {"claim": "Revenue", "quote": "revenue ten million dollars annually growth",
             "confidence": "medium", "pass": 1},
        ]
        new = [
            {"claim": "Revenue detail", "quote": "revenue ten million dollars annually growth",
             "confidence": "high", "pass": 2},
        ]
        merged = _deduplicate_evidence(existing, new)
        assert len(merged) == 1
        assert merged[0]["confidence"] == "high"  # Higher confidence kept

    def test_duplicate_keeps_existing_if_same_confidence(self):
        existing = [
            {"claim": "Revenue", "quote": "revenue ten million", "confidence": "high", "pass": 1},
        ]
        new = [
            {"claim": "Revenue dup", "quote": "revenue ten million", "confidence": "high", "pass": 2},
        ]
        merged = _deduplicate_evidence(existing, new)
        assert len(merged) == 1
        assert merged[0]["pass"] == 1  # Original kept

    def test_partial_overlap_not_deduplicated(self):
        """Items with <85% overlap should both be kept."""
        existing = [
            {"claim": "A", "quote": "the market is growing fast in all regions", "confidence": "high", "pass": 1},
        ]
        new = [
            {"claim": "B", "quote": "competition is increasing rapidly worldwide", "confidence": "high", "pass": 2},
        ]
        merged = _deduplicate_evidence(existing, new)
        assert len(merged) == 2

    def test_pass2_doesnt_overwrite_slide_type(self):
        """Pass 2 evidence merges in but doesn't change slide_type/framework."""
        analysis = SlideAnalysis(
            slide_type="data",
            framework="tam-sam-som",
            evidence=[
                {"claim": "TAM", "quote": "TAM $4.2B", "confidence": "high", "pass": 1},
            ],
        )
        new_evidence = [
            {"claim": "Growth", "quote": "CAGR 15%", "confidence": "high", "pass": 2},
        ]
        merged = _deduplicate_evidence(analysis.evidence, new_evidence)
        analysis.evidence = merged

        assert analysis.slide_type == "data"  # Unchanged
        assert analysis.framework == "tam-sam-som"  # Unchanged
        assert len(analysis.evidence) == 2  # Both kept
