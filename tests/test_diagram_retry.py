"""Tests for issue #76: slide-scoped diagram retries and stronger extraction."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import yaml
from PIL import Image as PILImage

from folio.config import FolioConfig
from folio.converter import (
    FolioConverter,
    _recompute_diagram_review_flags,
    _replace_leading_frontmatter,
)
from folio.output.diagram_notes import (
    build_note_basename,
    collect_diagram_retry_candidates,
    discover_retry_candidates,
    format_retry_candidate_summary,
    _build_structured_inventory,
)
from folio.pipeline.analysis import (
    DiagramAnalysis,
    DiagramGraph,
    DiagramGroup,
    DiagramNode,
)


# ---------------------------------------------------------------------------
# Sidecar / candidate discovery
# ---------------------------------------------------------------------------


def _profile(classification="diagram"):
    prof = MagicMock()
    prof.classification = classification
    return prof


def _write_sidecar(deck_dir, deck_slug, created_date, page, **fm_extra):
    basename = build_note_basename(created_date, deck_slug, page)
    fm = {"type": "diagram", "review_required": False, "_extraction_metadata": {}}
    fm.update(fm_extra)
    content = f"---\n{yaml.dump(fm, sort_keys=False)}---\n\n# Note\n"
    (deck_dir / f"{basename}.md").write_text(content)


class TestDiscoverRetryCandidates:
    def test_failed_mode_finds_provider_failures(self, tmp_path):
        page_profiles = {2: _profile(), 3: _profile(), 4: _profile()}
        _write_sidecar(tmp_path, "deck", "20260604", 2,
                       review_required=True,
                       _extraction_metadata={"pass_a_parse_outcome": "provider_failure"})
        _write_sidecar(tmp_path, "deck", "20260604", 3,
                       _extraction_metadata={"pass_a_parse_outcome": "success"})
        _write_sidecar(tmp_path, "deck", "20260604", 4, review_required=True)

        candidates = discover_retry_candidates(
            tmp_path, "deck", "20260604", page_profiles, mode="failed"
        )
        assert candidates == {2: "provider_failure"}

    def test_review_required_mode(self, tmp_path):
        page_profiles = {2: _profile(), 4: _profile()}
        _write_sidecar(tmp_path, "deck", "20260604", 2,
                       _extraction_metadata={"pass_a_parse_outcome": "provider_failure"},
                       review_required=True)
        _write_sidecar(tmp_path, "deck", "20260604", 4, review_required=True)

        candidates = discover_retry_candidates(
            tmp_path, "deck", "20260604", page_profiles, mode="review_required"
        )
        assert candidates == {2: "review_required", 4: "review_required"}

    def test_frozen_notes_are_skipped(self, tmp_path):
        page_profiles = {2: _profile()}
        _write_sidecar(tmp_path, "deck", "20260604", 2,
                       review_required=True, folio_freeze=True,
                       _extraction_metadata={"pass_a_parse_outcome": "provider_failure"})
        assert discover_retry_candidates(
            tmp_path, "deck", "20260604", page_profiles, mode="failed"
        ) == {}


class TestCollectAndFormatCandidates:
    def test_collect_from_in_memory_analyses(self):
        analyses = {
            1: DiagramAnalysis(diagram_type="architecture"),  # clean
            2: DiagramAnalysis(
                diagram_type="process",
                _extraction_metadata={"pass_a_parse_outcome": "provider_failure"},
                review_required=True,
            ),
            3: DiagramAnalysis(diagram_type="concept-map", review_required=True),
        }
        assert collect_diagram_retry_candidates(analyses) == [
            (2, "provider_failure"),
            (3, "review_required"),
        ]

    def test_format_summary_provider_failure_suggests_failed_flag(self):
        summary = format_retry_candidate_summary(
            [(35, "provider_failure"), (36, "provider_failure")],
            source_name="deck.pptx",
        )
        assert "Diagram retry candidates:" in summary
        assert "- slide 35: provider_failure" in summary
        assert "Run: folio convert deck.pptx --retry-failed-diagrams" in summary

    def test_format_summary_review_required_only(self):
        summary = format_retry_candidate_summary(
            [(7, "review_required")], source_name="deck.pptx"
        )
        assert "--retry-review-required-diagrams" in summary

    def test_format_summary_empty_is_none(self):
        assert format_retry_candidate_summary([], source_name="deck.pptx") is None


# ---------------------------------------------------------------------------
# Deck frontmatter flag recomputation
# ---------------------------------------------------------------------------


class TestRecomputeDiagramReviewFlags:
    def test_clears_resolved_flag_for_retried_slide(self):
        existing = ["diagram_review_required_slide_2", "unvalidated_claim_slide_5"]
        retried = {2: DiagramAnalysis(diagram_type="process")}  # now clean
        result = _recompute_diagram_review_flags(existing, retried)
        assert result == ["unvalidated_claim_slide_5"]

    def test_readds_flags_when_still_flagged(self):
        existing = ["diagram_abstained_slide_2"]
        retried = {2: DiagramAnalysis(
            diagram_type="process",
            review_required=True,
            review_questions=["needs eyes"],
        )}
        result = _recompute_diagram_review_flags(existing, retried)
        assert "diagram_review_required_slide_2" in result
        assert "diagram_open_questions_slide_2" in result
        assert "diagram_abstained_slide_2" not in result

    def test_preserves_non_target_diagram_flags(self):
        existing = ["diagram_abstained_slide_9", "text_validation_unavailable_slide_2"]
        retried = {2: DiagramAnalysis(diagram_type="process")}
        result = _recompute_diagram_review_flags(existing, retried)
        assert "diagram_abstained_slide_9" in result
        assert "text_validation_unavailable_slide_2" in result


class TestReplaceLeadingFrontmatter:
    def test_preserves_body_exactly(self):
        content = "---\nid: x\nreview_status: flagged\n---\n\n# Title\n\nBody line.\n"
        new = _replace_leading_frontmatter(content, {"id": "x", "review_status": "clean"})
        assert "review_status: clean" in new
        assert new.endswith("# Title\n\nBody line.\n")
        assert "flagged" not in new


# ---------------------------------------------------------------------------
# Structured inventory rendering (concept-map / process)
# ---------------------------------------------------------------------------


class TestStructuredInventory:
    def test_inventory_surfaces_stages_decisions_callouts_zones(self):
        graph = DiagramGraph(
            nodes=[
                DiagramNode(id="s1", label="Intake", kind="process"),
                DiagramNode(id="d1", label="Approved?", kind="decision"),
                DiagramNode(id="c1", label="SLA: 24h", kind="note"),
            ],
            groups=[DiagramGroup(id="g1", name="Operations", contains=["s1", "d1"])],
        )
        lines = _build_structured_inventory(graph)
        body = "\n".join(lines)
        assert "## Structured Inventory" in body
        assert "Zones / Lanes" in body and "Operations (2 components)" in body
        assert "Stages" in body and "- Intake" in body
        assert "Decisions" in body and "- Approved?" in body
        assert "Callouts" in body and "- SLA: 24h" in body

    def test_inventory_empty_for_pure_architecture_graph(self):
        graph = DiagramGraph(nodes=[
            DiagramNode(id="a", label="API", kind="service"),
            DiagramNode(id="b", label="DB", kind="database"),
        ])
        assert _build_structured_inventory(graph) == []

    def test_inventory_empty_for_none_graph(self):
        assert _build_structured_inventory(None) == []


# ---------------------------------------------------------------------------
# analyze_diagram_pages: payload-reduction fallback + cache persistence
# ---------------------------------------------------------------------------


def _diagram_mocks(tmp_path, call_responses, *, escalation="simple"):
    from folio.pipeline.images import ImageResult
    from folio.pipeline.text import SlideText
    from folio.llm.types import ProviderOutput, TokenUsage

    img_path = tmp_path / "slide-001.png"
    PILImage.new("RGB", (300, 300), "white").save(img_path)

    pass1_results = {1: DiagramAnalysis(slide_type="data", diagram_type="architecture")}
    prof = MagicMock()
    prof.classification = "diagram"
    prof.crop_box = (0.0, 0.0, 612.0, 792.0)
    prof.escalation_level = escalation
    prof.render_dpi = 150
    prof.rotation = 0
    prof.vector_count = 0
    prof.char_count = 0
    prof.bounded_texts = []
    page_profiles = {1: prof}
    image_results = [ImageResult(path=img_path, slide_num=1, width=300, height=300)]
    slide_texts = {1: SlideText(slide_num=1, full_text="Node A to Node B", elements=[])}

    call_idx = [0]

    def mock_call_llm(*args, **kwargs):
        idx = call_idx[0]
        call_idx[0] += 1
        raw_text, truncated = call_responses[idx] if idx < len(call_responses) else ("", False)
        out = ProviderOutput(
            raw_text=raw_text, truncated=truncated,
            provider_name="anthropic", model_name="test",
            usage=TokenUsage(input_tokens=100, output_tokens=200, total_tokens=300),
        )
        return out, out.usage

    return pass1_results, page_profiles, image_results, slide_texts, mock_call_llm, call_idx


_VALID_PASS_A = json.dumps({
    "diagram_type": "architecture",
    "nodes": [{"id": "n1", "label": "Start", "confidence": 0.9},
              {"id": "n2", "label": "End", "confidence": 0.9}],
    "edges": [{"source": "n1", "target": "n2", "label": "next", "confidence": 0.9}],
})


class TestPayloadReductionFallback:
    def test_reduced_payload_retry_recovers_from_provider_failure(self, tmp_path):
        from folio.pipeline.diagram_extraction import analyze_diagram_pages
        # Dense → tiled (5 images); first (tiled) call returns nothing, the
        # reduced single-image retry returns valid JSON.
        pass1, profiles, imgs, texts, mock_llm, call_idx = _diagram_mocks(
            tmp_path, [("", False), (_VALID_PASS_A, False)], escalation="dense",
        )
        mock_img = PILImage.new("RGB", (300, 300), "white")
        with patch("folio.pipeline.diagram_extraction._get_provider_and_client",
                   return_value=(MagicMock(), MagicMock())), \
             patch("folio.pipeline.diagram_extraction._call_llm", side_effect=mock_llm), \
             patch("folio.pipeline.diagram_extraction._load_page_image", return_value=mock_img):
            results, stats, meta = analyze_diagram_pages(
                pass1_results=pass1, page_profiles=profiles, image_results=imgs,
                slide_texts=texts, cache_dir=tmp_path, force_miss=True,
                slide_numbers=[1], diagram_max_tokens=8192,
            )
        analysis = results[1]
        assert call_idx[0] >= 2  # tiled failure + reduced retry
        assert analysis._extraction_metadata.get("pass_a_payload_reduction_succeeded") is True
        assert analysis._extraction_metadata.get("pass_a_parse_outcome") == "success"

    def test_persistent_failure_marks_provider_failure_with_reduction_flag(self, tmp_path):
        from folio.pipeline.diagram_extraction import analyze_diagram_pages
        pass1, profiles, imgs, texts, mock_llm, call_idx = _diagram_mocks(
            tmp_path, [("", False), ("", False)], escalation="dense",
        )
        mock_img = PILImage.new("RGB", (300, 300), "white")
        with patch("folio.pipeline.diagram_extraction._get_provider_and_client",
                   return_value=(MagicMock(), MagicMock())), \
             patch("folio.pipeline.diagram_extraction._call_llm", side_effect=mock_llm), \
             patch("folio.pipeline.diagram_extraction._load_page_image", return_value=mock_img):
            results, stats, meta = analyze_diagram_pages(
                pass1_results=pass1, page_profiles=profiles, image_results=imgs,
                slide_texts=texts, cache_dir=tmp_path, force_miss=True,
                slide_numbers=[1], diagram_max_tokens=8192,
            )
        m = results[1]._extraction_metadata
        assert m["pass_a_parse_outcome"] == "provider_failure"
        assert m["pass_a_payload_reduction_attempted"] is True
        assert results[1].review_required is True


class TestCachePersistence:
    def test_successful_force_miss_run_persists_final_cache(self, tmp_path):
        # Issue #76: a --no-cache (force_miss) run must still persist successful
        # diagram work so later surgical retries are cheap.
        from folio.pipeline.diagram_extraction import analyze_diagram_pages
        pass1, profiles, imgs, texts, mock_llm, call_idx = _diagram_mocks(
            tmp_path, [(_VALID_PASS_A, False)], escalation="simple",
        )
        mock_img = PILImage.new("RGB", (300, 300), "white")
        with patch("folio.pipeline.diagram_extraction._get_provider_and_client",
                   return_value=(MagicMock(), MagicMock())), \
             patch("folio.pipeline.diagram_extraction._call_llm", side_effect=mock_llm), \
             patch("folio.pipeline.diagram_extraction._load_page_image", return_value=mock_img):
            results, stats, meta = analyze_diagram_pages(
                pass1_results=pass1, page_profiles=profiles, image_results=imgs,
                slide_texts=texts, cache_dir=tmp_path, force_miss=True,
                slide_numbers=[1], diagram_max_tokens=8192,
            )
        assert not results[1].abstained
        assert (tmp_path / ".analysis_cache_diagram_final.json").exists()


# ---------------------------------------------------------------------------
# convert_diagrams() orchestration + deck flag refresh + registry
# ---------------------------------------------------------------------------


class TestRefreshDeckDiagramFlags:
    def test_updates_frontmatter_and_registry(self, tmp_path):
        from folio.tracking import registry
        library = tmp_path / "library"
        deck_dir = library / "evidence" / "deck"
        deck_dir.mkdir(parents=True)
        deck_md = deck_dir / "deck.md"
        deck_md.write_text(
            "---\nid: deck-1\nreview_status: flagged\n"
            "review_flags:\n- diagram_review_required_slide_2\n"
            "- unvalidated_claim_slide_5\n---\n\n# Deck\n\nBody preserved.\n"
        )
        registry_path = library / "registry.json"
        registry.upsert_entry(registry_path, registry.RegistryEntry(
            id="deck-1", title="Deck", markdown_path="evidence/deck/deck.md",
            deck_dir="evidence/deck", review_status="flagged",
            review_flags=["diagram_review_required_slide_2", "unvalidated_claim_slide_5"],
        ))

        config = FolioConfig(library_root=library)
        converter = FolioConverter(config)
        # Slide 2 retried successfully → now clean.
        converter._refresh_deck_diagram_flags(deck_md, {2: DiagramAnalysis(diagram_type="process")})

        fm = yaml.safe_load(deck_md.read_text().split("---")[1])
        assert "diagram_review_required_slide_2" not in fm["review_flags"]
        assert "unvalidated_claim_slide_5" in fm["review_flags"]
        assert deck_md.read_text().endswith("Body preserved.\n")

        data = registry.load_registry(registry_path)
        assert "diagram_review_required_slide_2" not in data["decks"]["deck-1"]["review_flags"]


class TestConvertDiagramsOrchestration:
    def _patch_stages(self, monkeypatch, converter, page_profiles, retried_analyses):
        import folio.converter as conv
        norm = MagicMock()
        norm.pdf_path = MagicMock()
        norm.renderer_used = "powerpoint"
        monkeypatch.setattr(conv.normalize, "to_pdf", lambda *a, **k: norm)
        monkeypatch.setattr(conv.inspect, "inspect_pages", lambda *a, **k: page_profiles)
        from folio.pipeline.images import ImageResult
        monkeypatch.setattr(
            conv.images, "extract_with_metadata",
            lambda *a, **k: [ImageResult(path=MagicMock(), slide_num=p, width=10, height=10)
                             for p in page_profiles],
        )
        from folio.pipeline.text import SlideText
        monkeypatch.setattr(
            conv.text, "extract_structured",
            lambda *a, **k: {p: SlideText(slide_num=p, full_text="x", elements=[])
                             for p in page_profiles},
        )
        recon = MagicMock()
        recon.slide_texts = {p: SlideText(slide_num=p, full_text="x", elements=[])
                             for p in page_profiles}
        monkeypatch.setattr(conv.text, "reconcile_slide_count", lambda *a, **k: recon)
        monkeypatch.setattr(converter, "_infer_from_source_root", lambda *a, **k: (None, None))
        monkeypatch.setattr(converter, "_run_profile_preflight", lambda *a, **k: None)

        def fake_analyze(**kwargs):
            nums = kwargs["slide_numbers"]
            out = {n: retried_analyses[n] for n in nums}
            return out, MagicMock(), MagicMock()
        monkeypatch.setattr("folio.pipeline.diagram_extraction.analyze_diagram_pages", fake_analyze)
        monkeypatch.setattr("folio.output.diagram_rendering.render_diagram_analyses", lambda a: a)

    def test_retry_failed_targets_provider_failure_slide(self, tmp_path, monkeypatch):
        library = tmp_path / "library"
        deck_dir = library / "evidence" / "deck"
        deck_dir.mkdir(parents=True)
        deck_md = deck_dir / "deck.md"
        deck_md.write_text(
            "---\nid: deck-1\ncreated: '2026-06-04'\nreview_status: flagged\n"
            "review_flags:\n- diagram_review_required_slide_2\n---\n\n# Deck\n\nBody.\n"
        )
        _write_sidecar(deck_dir, "deck", "20260604", 2, review_required=True,
                       _extraction_metadata={"pass_a_parse_outcome": "provider_failure"})
        source = tmp_path / "deck.pptx"
        source.write_bytes(b"fake-pptx")

        config = FolioConfig(library_root=library)
        converter = FolioConverter(config)
        monkeypatch.setattr(converter, "_resolve_target", lambda *a, **k: deck_dir)

        emit_calls = {}

        def fake_emit(**kwargs):
            emit_calls.update(kwargs)
            return {}
        monkeypatch.setattr("folio.output.diagram_notes.emit_diagram_notes", fake_emit)

        page_profiles = {2: _profile("diagram")}
        retried = {2: DiagramAnalysis(diagram_type="process")}  # now clean
        self._patch_stages(monkeypatch, converter, page_profiles, retried)

        result = converter.convert_diagrams(source, retry_failed=True)

        assert result.retried_slides == [2]
        assert result.remaining_candidates == []
        # emit_diagram_notes was called with only the retried analysis
        assert set(emit_calls["analyses"].keys()) == {2}
        # Deck frontmatter flag cleared, body preserved.
        text_after = deck_md.read_text()
        assert "diagram_review_required_slide_2" not in text_after
        assert text_after.rstrip().endswith("Body.")

    def test_slides_scopes_retry_to_named_slides(self, tmp_path, monkeypatch):
        # Review fix: `--slides 35 --retry-failed-diagrams` must touch ONLY slide
        # 35 even when slide 36 also failed.
        library = tmp_path / "library"
        deck_dir = library / "evidence" / "deck"
        deck_dir.mkdir(parents=True)
        deck_md = deck_dir / "deck.md"
        deck_md.write_text(
            "---\nid: deck-1\ncreated: '2026-06-04'\nreview_status: flagged\n"
            "review_flags: []\n---\n\n# Deck\n\nBody.\n"
        )
        for page in (35, 36):
            _write_sidecar(deck_dir, "deck", "20260604", page, review_required=True,
                           _extraction_metadata={"pass_a_parse_outcome": "provider_failure"})
        source = tmp_path / "deck.pptx"
        source.write_bytes(b"fake-pptx")

        config = FolioConfig(library_root=library)
        converter = FolioConverter(config)
        monkeypatch.setattr(converter, "_resolve_target", lambda *a, **k: deck_dir)

        emit_calls = {}

        def fake_emit(**kwargs):
            emit_calls.update(kwargs)
            return {}
        monkeypatch.setattr("folio.output.diagram_notes.emit_diagram_notes", fake_emit)

        page_profiles = {35: _profile("diagram"), 36: _profile("diagram")}
        retried = {35: DiagramAnalysis(diagram_type="process"),
                   36: DiagramAnalysis(diagram_type="process")}
        self._patch_stages(monkeypatch, converter, page_profiles, retried)

        result = converter.convert_diagrams(source, slides=[35], retry_failed=True)

        assert result.retried_slides == [35]
        assert set(emit_calls["analyses"].keys()) == {35}


# ---------------------------------------------------------------------------
# CLI flag parsing + dispatch
# ---------------------------------------------------------------------------


class TestConvertCliDiagramFlags:
    def _runner(self):
        from click.testing import CliRunner
        return CliRunner()

    def test_slides_without_diagram_flag_errors(self, tmp_path):
        from folio.cli import cli
        src = tmp_path / "deck.pptx"
        src.write_bytes(b"x")
        result = self._runner().invoke(cli, ["convert", str(src), "--slides", "1,2"])
        assert result.exit_code == 1
        assert "--slides requires" in result.output

    def test_invalid_slides_value_errors(self, tmp_path):
        from folio.cli import cli
        src = tmp_path / "deck.pptx"
        src.write_bytes(b"x")
        result = self._runner().invoke(
            cli, ["convert", str(src), "--diagrams-only", "--slides", "abc"]
        )
        assert result.exit_code == 1
        assert "comma-separated integers" in result.output

    @patch("folio.cli.FolioConverter")
    def test_retry_failed_dispatches_to_convert_diagrams(self, mock_cls, tmp_path):
        from folio.cli import cli
        from folio.converter import DiagramRetryResult
        src = tmp_path / "deck.pptx"
        src.write_bytes(b"x")
        mock_conv = MagicMock()
        mock_conv.convert_diagrams.return_value = DiagramRetryResult(
            output_path=tmp_path / "deck.md", retried_slides=[35, 36],
            refreshed_notes=2, remaining_candidates=[(36, "provider_failure")],
        )
        mock_cls.return_value = mock_conv
        result = self._runner().invoke(cli, ["convert", str(src), "--retry-failed-diagrams"])
        assert result.exit_code == 0
        mock_conv.convert_diagrams.assert_called_once()
        assert mock_conv.convert_diagrams.call_args.kwargs["retry_failed"] is True
        assert "diagram retry" in result.output
        assert "Retried slides: 35, 36" in result.output
        assert "--retry-failed-diagrams" in result.output  # summary for remaining

    @patch("folio.cli.FolioConverter")
    def test_normal_convert_prints_retry_candidate_summary(self, mock_cls, tmp_path):
        from folio.cli import cli
        from folio.converter import ConversionResult
        from folio.tracking.versions import ChangeSet
        src = tmp_path / "deck.pptx"
        src.write_bytes(b"x")
        mock_conv = MagicMock()
        mock_conv.convert.return_value = ConversionResult(
            output_path=tmp_path / "deck.md", slide_count=48, version=1,
            changes=ChangeSet(), deck_id="d1", renderer_used="powerpoint",
            diagram_retry_candidates=[(35, "provider_failure")],
        )
        mock_cls.return_value = mock_conv
        result = self._runner().invoke(cli, ["convert", str(src)])
        assert result.exit_code == 0
        assert "Diagram retry candidates:" in result.output
        assert "- slide 35: provider_failure" in result.output
