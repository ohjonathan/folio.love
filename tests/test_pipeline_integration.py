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
from folio.pipeline.images import ImageResult
from folio.pipeline.normalize import NormalizationResult
from folio.pipeline.text import SlideText
from folio.output.frontmatter import _compute_grounding_summary


@pytest.fixture(autouse=True)
def _mock_inspect_pages():
    """Auto-mock inspect_pages for pipeline integration tests."""
    class _DefaultProfileDict(dict):
        def __missing__(self, key):
            profile = MagicMock(classification="text")
            self[key] = profile
            return profile
    with patch("folio.pipeline.inspect.inspect_pages", return_value=_DefaultProfileDict()):
        yield


def _mock_anthropic_response(text: str):
    """Create a mock Anthropic API response."""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    mock_response.stop_reason = "end_turn"
    # Token usage must be real ints for RateLimiter.record_usage comparison
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    return mock_response


MOCK_PASS1_RESPONSES = {
    1: json.dumps({
        "slide_type": "title",
        "framework": "none",
        "visual_description": "Title slide with company name and quarter indicator.",
        "key_data": "Q1 2026",
        "main_insight": "Opening slide for quarterly market review.",
        "evidence": [
            {"claim": "Quarter identification", "quote": "Q1 2026 Review",
             "element_type": "body", "confidence": "high"},
        ],
    }),
    2: json.dumps({
        "slide_type": "data",
        "framework": "tam-sam-som",
        "visual_description": "Revenue metrics with TAM/SAM/SOM breakdown and growth projections.",
        "key_data": "TAM $4.2B, SAM $1.2B, SOM $300M, CAGR 12%, Revenue $10M",
        "main_insight": "Strong market opportunity with clear path to 5% market share.",
        "evidence": [
            {"claim": "Market sizing", "quote": "TAM $4.2B",
             "element_type": "body", "confidence": "high"},
            {"claim": "Growth projection", "quote": "CAGR 12% projected through 2028",
             "element_type": "body", "confidence": "high"},
            {"claim": "Revenue figure", "quote": "Revenue $10M in FY2025",
             "element_type": "body", "confidence": "high"},
        ],
    }),
    3: json.dumps({
        "slide_type": "next-steps",
        "framework": "none",
        "visual_description": "Simple text slide with action items.",
        "key_data": "",
        "main_insight": "Follow-up actions for client engagement.",
        "evidence": [
            {"claim": "Action item", "quote": "Follow up with client on timeline",
             "element_type": "body", "confidence": "medium"},
        ],
    }),
}

MOCK_PASS2_RESPONSE = json.dumps({
    "slide_type_reassessment": "unchanged",
    "framework_reassessment": "unchanged",
    "evidence": [
        {"claim": "Revenue growth rate", "quote": "projected $15M in FY2026",
         "element_type": "body", "confidence": "high"},
        {"claim": "Expansion strategy", "quote": "enterprise expansion, product-led growth",
         "element_type": "body", "confidence": "medium"},
        {"claim": "International timeline", "quote": "international markets opening Q3 2026",
         "element_type": "body", "confidence": "high"},
    ],
})


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
                results, _, _ = analyze_slides(
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
                pass1_results, _, _ = analyze_slides(
                    image_paths,
                    model="test-model",
                    slide_texts=slide_texts,
                )

                pass1_evidence_count = sum(
                    len(a.evidence) for a in pass1_results.values()
                )

                # Pass 2
                pass2_results, _, _ = analyze_slides_deep(
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
            source_type="deck",
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


class TestAPIPayloadIncludesText:
    """Test that API payloads include extracted text context."""

    @staticmethod
    def _make_unique_png(index: int) -> bytes:
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            + bytes([index]) * 16
            + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass1_payload_includes_extracted_text(self):
        """Pass-1 API call should include EXTRACTED SLIDE TEXT in prompt."""
        import tempfile
        from folio.pipeline.analysis import analyze_slides

        captured_prompts = []

        def mock_create(**kwargs):
            for msg in kwargs.get("messages", []):
                for content in msg.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "text":
                        captured_prompts.append(content["text"])
            return _mock_anthropic_response(MOCK_PASS1_RESPONSES[1])

        mock_client = MagicMock()
        mock_client.messages.create = mock_create

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            img = tmpdir_path / "slide-001.png"
            img.write_bytes(self._make_unique_png(100))

            slide_texts = {
                1: SlideText(slide_num=1, full_text="Market Analysis Q1 2026", elements=[]),
            }

            with patch("anthropic.Anthropic", return_value=mock_client):
                analyze_slides([img], model="test", slide_texts=slide_texts)

        assert len(captured_prompts) >= 1
        assert "EXTRACTED SLIDE TEXT" in captured_prompts[0]
        assert "Market Analysis Q1 2026" in captured_prompts[0]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass1_without_text_degrades_gracefully(self):
        """Pass-1 without text should include 'No extracted text' note."""
        import tempfile
        from folio.pipeline.analysis import analyze_slides

        captured_prompts = []

        def mock_create(**kwargs):
            for msg in kwargs.get("messages", []):
                for content in msg.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "text":
                        captured_prompts.append(content["text"])
            return _mock_anthropic_response(MOCK_PASS1_RESPONSES[1])

        mock_client = MagicMock()
        mock_client.messages.create = mock_create

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            img = tmpdir_path / "slide-001.png"
            img.write_bytes(self._make_unique_png(101))

            with patch("anthropic.Anthropic", return_value=mock_client):
                analyze_slides([img], model="test", slide_texts=None)

        assert len(captured_prompts) >= 1
        assert "No extracted text available" in captured_prompts[0]


class TestUnvalidatedFrontmatter:
    """Test that unvalidated analyses are excluded from frontmatter aggregation."""

    def test_unvalidated_only_slide_excluded(self):
        """Slide with evidence where ALL items are unvalidated should be excluded."""
        from folio.output.frontmatter import _collect_unique

        analyses = {
            1: SlideAnalysis(
                slide_type="data",
                framework="tam-sam-som",
                evidence=[
                    {"claim": "A", "confidence": "high", "validated": False},
                    {"claim": "B", "confidence": "medium", "validated": False},
                ],
            ),
            2: SlideAnalysis(
                slide_type="framework",
                framework="scr",
                evidence=[
                    {"claim": "C", "confidence": "high", "validated": True},
                ],
            ),
        }
        frameworks = _collect_unique(analyses, "framework", exclude={"none", "pending"})
        slide_types = _collect_unique(analyses, "slide_type", exclude={"unknown", "pending"})
        # Slide 1 excluded (all unvalidated), slide 2 included
        assert "tam-sam-som" not in frameworks
        assert "scr" in frameworks
        assert "data" not in slide_types
        assert "framework" in slide_types

    def test_no_evidence_slide_still_included(self):
        """Slide with no evidence (no grounding attempted) should still be included."""
        from folio.output.frontmatter import _collect_unique

        analyses = {
            1: SlideAnalysis(slide_type="title", framework="none", evidence=[]),
        }
        slide_types = _collect_unique(analyses, "slide_type", exclude={"unknown", "pending"})
        assert "title" in slide_types

    def test_mixed_validation_included(self):
        """Slide with at least one validated evidence item should be included."""
        from folio.output.frontmatter import _collect_unique

        analyses = {
            1: SlideAnalysis(
                slide_type="data",
                framework="tam-sam-som",
                evidence=[
                    {"claim": "A", "confidence": "high", "validated": True},
                    {"claim": "B", "confidence": "medium", "validated": False},
                ],
            ),
        }
        frameworks = _collect_unique(analyses, "framework", exclude={"none", "pending"})
        assert "tam-sam-som" in frameworks


class TestFrontmatterSchemaFix:
    """Test frontmatter schema corrections."""

    def test_status_is_active(self):
        """Status should be 'active', not 'current'."""
        import yaml
        from folio.output.frontmatter import generate
        from folio.tracking.versions import VersionInfo, ChangeSet

        analyses = {1: SlideAnalysis(slide_type="title")}
        version_info = VersionInfo(
            version=1, timestamp="2026-01-01T00:00:00Z",
            source_hash="abc123", source_path="deck.pptx",
            note=None, slide_count=1, changes=ChangeSet(added=[1]),
        )
        fm = generate(
            title="Test", deck_id="test_id",
            source_relative_path="deck.pptx", source_hash="abc123",
            source_type="deck",
            version_info=version_info, analyses=analyses,
        )
        parsed = yaml.safe_load(fm.strip("---").strip())
        assert parsed["status"] == "active"

    def test_created_preserved_on_reconversion(self):
        """On reconversion, 'id' and 'created' should be preserved from existing frontmatter."""
        import yaml
        from folio.output.frontmatter import generate
        from folio.tracking.versions import VersionInfo, ChangeSet

        analyses = {1: SlideAnalysis(slide_type="title")}
        version_info = VersionInfo(
            version=2, timestamp="2026-03-02T00:00:00Z",
            source_hash="def456", source_path="deck.pptx",
            note=None, slide_count=1, changes=ChangeSet(modified=[1]),
        )
        existing_fm = {
            "id": "original_id_123",
            "created": "2025-01-15T10:00:00Z",
        }
        fm = generate(
            title="Test", deck_id="new_id_456",
            source_relative_path="deck.pptx", source_hash="def456",
            source_type="deck",
            version_info=version_info, analyses=analyses,
            existing_frontmatter=existing_fm,
        )
        parsed = yaml.safe_load(fm.strip("---").strip())
        assert parsed["id"] == "original_id_123"
        assert parsed["created"] == "2025-01-15T10:00:00Z"

    def test_first_conversion_generates_new_values(self):
        """First conversion (no existing frontmatter) should generate fresh values."""
        import yaml
        from folio.output.frontmatter import generate
        from folio.tracking.versions import VersionInfo, ChangeSet

        analyses = {1: SlideAnalysis(slide_type="title")}
        version_info = VersionInfo(
            version=1, timestamp="2026-01-01T00:00:00Z",
            source_hash="abc123", source_path="deck.pptx",
            note=None, slide_count=1, changes=ChangeSet(added=[1]),
        )
        fm = generate(
            title="Test", deck_id="fresh_id",
            source_relative_path="deck.pptx", source_hash="abc123",
            source_type="deck",
            version_info=version_info, analyses=analyses,
        )
        parsed = yaml.safe_load(fm.strip("---").strip())
        assert parsed["id"] == "fresh_id"
        assert "created" in parsed


class TestEndToEndConverter:
    """End-to-end converter tests with all pipeline stages mocked."""

    @staticmethod
    def _make_unique_png(index: int) -> bytes:
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            + bytes([index]) * 16
            + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

    def _setup_mocks(self, tmpdir: Path, slide_count: int = 3):
        """Create fake source, images, and slide texts."""
        source = tmpdir / "test_deck.pptx"
        source.write_bytes(b"fake pptx content")

        image_paths = []
        image_results = []
        for i in range(1, slide_count + 1):
            img = tmpdir / f"slide-{i:03d}.png"
            img.write_bytes(self._make_unique_png(i + 200))
            image_paths.append(img)
            image_results.append(ImageResult(
                path=img, slide_num=i, width=200, height=200,
            ))

        slide_texts = {}
        for i in range(1, slide_count + 1):
            slide_texts[i] = SlideText(
                slide_num=i,
                full_text=f"Slide {i} text content",
                elements=[{"type": "body", "text": f"Slide {i} text content"}],
            )

        return source, image_paths, image_results, slide_texts

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_convert_pass1(self):
        """Full pass-1 conversion with mocked pipeline stages."""
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source, image_paths, image_results, slide_texts = self._setup_mocks(tmpdir_path)

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            # Create mock response
            mock_client = MagicMock()
            call_idx = [0]

            def mock_create(**kwargs):
                call_idx[0] += 1
                idx = min(call_idx[0], 3)
                return _mock_anthropic_response(MOCK_PASS1_RESPONSES[idx])

            mock_client.messages.create = mock_create

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=source, renderer_used="powerpoint")), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch("anthropic.Anthropic", return_value=mock_client):

                converter = FolioConverter(config)
                result = converter.convert(
                    source_path=source,
                    target=target_dir,
                    passes=1,
                )

            assert result.slide_count == 3
            assert result.output_path.exists()

            # Verify markdown content
            content = result.output_path.read_text()
            assert content.startswith("---")
            # Parse frontmatter
            end = content.index("---", 3)
            fm = yaml.safe_load(content[3:end])
            assert fm["status"] == "active"
            assert fm["slide_count"] == 3

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_convert_pass2(self):
        """Full pass-2 conversion adds evidence on dense slides."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source, image_paths, image_results, slide_texts = self._setup_mocks(tmpdir_path)

            # Make slide 2 high density text
            slide_texts[2] = SlideText(
                slide_num=2,
                full_text="TAM $4.2B, SAM $1.2B, SOM $300M. CAGR 12%. " + " ".join(["word"] * 200),
                elements=[],
            )

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            mock_client = MagicMock()
            call_idx = [0]

            def mock_create(**kwargs):
                call_idx[0] += 1
                prompt_text = ""
                for msg in kwargs.get("messages", []):
                    for content in msg.get("content", []):
                        if isinstance(content, dict) and content.get("type") == "text":
                            prompt_text = content.get("text", "")
                if "prior_analysis" in prompt_text.lower():
                    return _mock_anthropic_response(MOCK_PASS2_RESPONSE)
                idx = min(call_idx[0], 3)
                return _mock_anthropic_response(MOCK_PASS1_RESPONSES[idx])

            mock_client.messages.create = mock_create

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=source, renderer_used="powerpoint")), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch("anthropic.Anthropic", return_value=mock_client):

                converter = FolioConverter(config)
                result = converter.convert(
                    source_path=source,
                    target=target_dir,
                    passes=2,
                )

            assert result.slide_count == 3
            assert result.output_path.exists()


class TestCLI:
    """Test CLI argument validation using click's test runner."""

    def test_convert_passes_1_accepted(self):
        from click.testing import CliRunner
        from folio.cli import cli

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(b"fake")
            f.flush()
            # Just test that --passes 1 is accepted (will fail at conversion, but CLI arg is valid)
            result = runner.invoke(cli, ["convert", f.name, "--passes", "1"])
            # Should NOT fail with "Invalid value for '--passes'"
            assert "Invalid value for '--passes'" not in (result.output or "")

    def test_convert_passes_2_accepted(self):
        from click.testing import CliRunner
        from folio.cli import cli

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(b"fake")
            f.flush()
            result = runner.invoke(cli, ["convert", f.name, "--passes", "2"])
            assert "Invalid value for '--passes'" not in (result.output or "")

    def test_convert_passes_0_rejected(self):
        from click.testing import CliRunner
        from folio.cli import cli

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(b"fake")
            f.flush()
            result = runner.invoke(cli, ["convert", f.name, "--passes", "0"])
            assert result.exit_code != 0

    def test_convert_passes_3_rejected(self):
        from click.testing import CliRunner
        from folio.cli import cli

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(b"fake")
            f.flush()
            result = runner.invoke(cli, ["convert", f.name, "--passes", "3"])
            assert result.exit_code != 0


class TestTruncatedResponseIntegration:
    """Integration tests proving max_tokens responses fail safe through the real calling path."""

    @staticmethod
    def _make_unique_png(index: int) -> bytes:
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            + bytes([index]) * 16
            + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_max_tokens_pass1_returns_pending(self):
        """A pass-1 response with stop_reason='max_tokens' must return SlideAnalysis.pending()."""
        from folio.pipeline.analysis import analyze_slides

        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Slide Type: data\nFramework: none"
        mock_response.content = [mock_content]
        mock_response.stop_reason = "max_tokens"

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=mock_response)

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "slide-001.png"
            img.write_bytes(self._make_unique_png(200))

            with patch("anthropic.Anthropic", return_value=mock_client):
                results, _, _ = analyze_slides([img], model="test")

        assert results[1].slide_type == "pending"
        assert results[1].framework == "pending"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_max_tokens_pass2_returns_empty(self):
        """A pass-2 response with stop_reason='max_tokens' must return no evidence."""
        from folio.pipeline.analysis import analyze_slides_deep, SlideAnalysis

        # Set up pass-1 results with a high-density slide
        pass1_results = {
            1: SlideAnalysis(
                slide_type="data",
                framework="tam-sam-som",
                key_data="TAM $4.2B, SAM $1.2B, SOM $300M, CAGR 12%",
                evidence=[
                    {"claim": "TAM", "quote": "TAM $4.2B", "confidence": "high", "validated": True, "pass": 1},
                    {"claim": "Growth", "quote": "CAGR 12%", "confidence": "high", "validated": True, "pass": 1},
                    {"claim": "SAM", "quote": "SAM $1.2B", "confidence": "high", "validated": True, "pass": 1},
                ],
            ),
        }
        slide_texts = {
            1: SlideText(
                slide_num=1,
                full_text="TAM $4.2B, SAM $1.2B, SOM $300M. CAGR 12%. " + " ".join(["word"] * 200),
                elements=[],
            ),
        }

        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Evidence:\n- Claim: partial"
        mock_response.content = [mock_content]
        mock_response.stop_reason = "max_tokens"

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=mock_response)

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "slide-001.png"
            img.write_bytes(self._make_unique_png(201))

            with patch("anthropic.Anthropic", return_value=mock_client):
                results, _, _ = analyze_slides_deep(
                    pass1_results=pass1_results,
                    slide_texts=slide_texts,
                    image_paths=[img],
                    model="test",
                    density_threshold=2.0,
                )

        # Pass-2 evidence should NOT have been merged (max_tokens rejected)
        slide1_passes = set(ev.get("pass", 1) for ev in results[1].evidence)
        assert 2 not in slide1_passes


class TestBatchBehavior:
    """Test batch observability, restart resilience, and PDF mitigation path."""

    def test_preemptive_restart_at_cadence(self, tmp_path):
        """PowerPoint should be restarted after every N=15 PPTX conversions."""
        from click.testing import CliRunner
        from folio.cli import cli, _RESTART_CADENCE

        # Create 16 fake PPTX files
        for i in range(16):
            (tmp_path / f"deck_{i:02d}.pptx").write_bytes(b"fake")

        restart_calls = []

        def mock_restart():
            restart_calls.append(1)

        mock_result = MagicMock()
        mock_result.slide_count = 1
        mock_result.version = 1
        mock_result.changes = MagicMock(has_changes=False)
        mock_result.output_path = tmp_path / "out.md"
        mock_result.deck_id = "test"
        mock_result.cache_stats = None

        with patch("folio.cli._restart_powerpoint", side_effect=mock_restart), \
             patch("folio.converter.FolioConverter.convert", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(cli, ["batch", str(tmp_path), "--pattern", "*.pptx"])

        # Restart should have been called once (after 15th conversion)
        assert len(restart_calls) == 1

    def test_retry_once_on_9074(self, tmp_path):
        """Unexpected -9074 should trigger restart + retry once."""
        from click.testing import CliRunner
        from folio.cli import cli
        from folio.pipeline.normalize import NormalizationError

        (tmp_path / "deck.pptx").write_bytes(b"fake")

        restart_calls = []
        call_count = [0]

        def mock_restart():
            restart_calls.append(1)

        mock_result = MagicMock()
        mock_result.slide_count = 1
        mock_result.version = 1
        mock_result.changes = MagicMock(has_changes=False)
        mock_result.output_path = tmp_path / "out.md"
        mock_result.deck_id = "test"
        mock_result.cache_stats = None

        def mock_convert(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise NormalizationError("PowerPoint conversion failed: error number -9074")
            return mock_result

        with patch("folio.cli._restart_powerpoint", side_effect=mock_restart), \
             patch("folio.converter.FolioConverter.convert", side_effect=mock_convert):
            runner = CliRunner()
            result = runner.invoke(cli, ["batch", str(tmp_path), "--pattern", "*.pptx"])

        assert len(restart_calls) == 1  # One restart for retry
        assert call_count[0] == 2  # First call + retry
        assert "retry succeeded" in result.output

    def test_retry_failure_records_as_failed(self, tmp_path):
        """If retry also fails, the file should be recorded as failed."""
        from click.testing import CliRunner
        from folio.cli import cli
        from folio.pipeline.normalize import NormalizationError

        (tmp_path / "deck.pptx").write_bytes(b"fake")

        def mock_convert(**kwargs):
            raise NormalizationError("PowerPoint conversion failed: error number -9074")

        with patch("folio.cli._restart_powerpoint"), \
             patch("folio.converter.FolioConverter.convert", side_effect=mock_convert):
            runner = CliRunner()
            result = runner.invoke(cli, ["batch", str(tmp_path), "--pattern", "*.pptx"])

        assert "retry failed" in result.output
        assert "1 failed" in result.output

    def test_no_restart_for_pdf_batch(self, tmp_path):
        """PDF-only batches should NOT trigger PowerPoint restart."""
        from click.testing import CliRunner
        from folio.cli import cli

        for i in range(20):
            (tmp_path / f"doc_{i:02d}.pdf").write_bytes(b"fake")

        restart_calls = []

        def mock_restart():
            restart_calls.append(1)

        mock_result = MagicMock()
        mock_result.slide_count = 1
        mock_result.version = 1
        mock_result.changes = MagicMock(has_changes=False)
        mock_result.output_path = tmp_path / "out.md"
        mock_result.deck_id = "test"
        mock_result.cache_stats = None

        with patch("folio.cli._restart_powerpoint", side_effect=mock_restart), \
             patch("folio.converter.FolioConverter.convert", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(cli, ["batch", str(tmp_path), "--pattern", "*.pdf"])

        assert len(restart_calls) == 0  # No restarts for PDF
        assert "PDF mitigation" in result.output

    def test_outcome_summary_buckets(self, tmp_path):
        """Outcome summary should only use allowed buckets."""
        from click.testing import CliRunner
        from folio.cli import cli, _classify_outcome
        from folio.pipeline.normalize import NormalizationError

        # Timeout branch
        assert _classify_outcome(NormalizationError("timed out after 60s")) == "timeout"
        assert _classify_outcome(NormalizationError("PowerPoint Timed Out")) == "timeout"

        # AppleScript error codes (require "error" prefix per M4 fix)
        assert _classify_outcome(NormalizationError("error -9074")) == "applescript_-9074"
        assert _classify_outcome(NormalizationError("error number -1712")) == "applescript_-1712"
        assert _classify_outcome(NormalizationError("error -1728")) == "applescript_-1728"
        assert _classify_outcome(NormalizationError("AppleScript error -9074 blah")) == "applescript_-9074"

        # Non-AppleScript negative numbers should NOT match (M4 tightening)
        assert _classify_outcome(NormalizationError("exit code -1 failed")) == "unknown"
        assert _classify_outcome(NormalizationError("offset -5000 bytes")) == "unknown"

        # Unknown fallback
        assert _classify_outcome(NormalizationError("something unknown")) == "unknown"
        assert _classify_outcome(RuntimeError("generic error")) == "unknown"

    def test_no_dedicated_session_skips_restart(self, tmp_path):
        """--no-dedicated-session disables restart automation."""
        from click.testing import CliRunner
        from folio.cli import cli

        for i in range(20):
            (tmp_path / f"deck_{i:02d}.pptx").write_bytes(b"fake")

        restart_calls = []

        def mock_restart():
            restart_calls.append(1)

        mock_result = MagicMock()
        mock_result.slide_count = 1
        mock_result.version = 1
        mock_result.changes = MagicMock(has_changes=False)
        mock_result.output_path = tmp_path / "out.md"
        mock_result.deck_id = "test"
        mock_result.cache_stats = None

        with patch("folio.cli._restart_powerpoint", side_effect=mock_restart), \
             patch("folio.converter.FolioConverter.convert", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "batch", str(tmp_path), "--pattern", "*.pptx",
                "--no-dedicated-session"
            ])

        assert len(restart_calls) == 0  # No restarts when disabled

    def test_pdf_mitigation_help_text(self, tmp_path):
        """Batch help should mention PDF mitigation path."""
        from click.testing import CliRunner
        from folio.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", "--help"])

        assert "*.pdf" in result.output
        assert "NOT Tier 1" in result.output or "not Tier 1" in result.output

    def test_failure_tip_mentions_pdf_export(self, tmp_path):
        """When PPTX conversions fail, the tip should mention manual PDF export."""
        from click.testing import CliRunner
        from folio.cli import cli
        from folio.pipeline.normalize import NormalizationError

        (tmp_path / "deck.pptx").write_bytes(b"fake")

        def mock_convert(**kwargs):
            raise NormalizationError("unknown error")

        with patch("folio.cli._restart_powerpoint"), \
             patch("folio.converter.FolioConverter.convert", side_effect=mock_convert):
            runner = CliRunner()
            result = runner.invoke(cli, ["batch", str(tmp_path), "--pattern", "*.pptx"])

        assert "folio batch" in result.output
        assert "*.pdf" in result.output


# --- PR 6: Diagram transclusion in _format_slide ---


class TestFormatSlideDiagram:
    """Test _format_slide() diagram transclusion paths."""

    def test_pure_diagram_transclusion(self):
        """Pure diagram: suppress Analysis, add transclusion block."""
        from folio.output.markdown import _format_slide
        from folio.output.diagram_notes import DiagramNoteRef
        from folio.pipeline.analysis import DiagramAnalysis

        analysis = DiagramAnalysis(
            slide_type="pending", diagram_type="architecture",
        )
        ref = DiagramNoteRef(
            basename="20260314-deck-diagram-p007",
            path=Path("/tmp/note.md"),
            has_diagram_section=True,
            has_components_section=True,
        )
        output = _format_slide(
            slide_num=7, text=None, analysis=analysis,
            classification="diagram", diagram_note_ref=ref,
        )
        assert "### Analysis" not in output
        assert "![[20260314-deck-diagram-p007#Diagram]]" in output
        assert "![[20260314-deck-diagram-p007#Components]]" in output
        assert "*Full details: [[20260314-deck-diagram-p007]]*" in output

    def test_mixed_slide_preserves_analysis_and_adds_transclusion(self):
        """Mixed: keep consulting analysis, append diagram transclusion."""
        from folio.output.markdown import _format_slide
        from folio.output.diagram_notes import DiagramNoteRef
        from folio.pipeline.analysis import DiagramAnalysis

        analysis = DiagramAnalysis(
            slide_type="data", framework="tam-sam-som",
            visual_description="Revenue chart", key_data="$10M",
            main_insight="Growing revenue",
            diagram_type="data-flow",
        )
        ref = DiagramNoteRef(
            basename="20260314-deck-diagram-p003",
            path=Path("/tmp/note.md"),
            has_diagram_section=True,
            has_components_section=True,
        )
        output = _format_slide(
            slide_num=3, text=None, analysis=analysis,
            classification="mixed", diagram_note_ref=ref,
        )
        assert "### Analysis" in output
        assert "**Slide Type:** data" in output
        assert "![[20260314-deck-diagram-p003#Diagram]]" in output
        assert "*Full details: [[20260314-deck-diagram-p003]]*" in output

    def test_graphless_abstained_full_details_only(self):
        """Graphless abstained: image + full-details link only."""
        from folio.output.markdown import _format_slide
        from folio.output.diagram_notes import DiagramNoteRef
        from folio.pipeline.analysis import DiagramAnalysis

        analysis = DiagramAnalysis(
            slide_type="pending", diagram_type="unknown", abstained=True,
        )
        ref = DiagramNoteRef(
            basename="20260314-deck-diagram-p005",
            path=Path("/tmp/note.md"),
            has_diagram_section=False,
            has_components_section=False,
        )
        output = _format_slide(
            slide_num=5, text=None, analysis=analysis,
            classification="diagram", diagram_note_ref=ref,
        )
        assert "### Analysis" not in output
        assert "![[" not in output or "#Diagram" not in output
        assert "*Full details: [[20260314-deck-diagram-p005]]*" in output


