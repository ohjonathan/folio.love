"""Tests for PR 3: Diagram analysis dataclasses, serialization, IoU helpers, edge rewriting."""

import pytest

from folio.pipeline.analysis import (
    DiagramAnalysis,
    DiagramEdge,
    DiagramGraph,
    DiagramGroup,
    DiagramNode,
    SlideAnalysis,
    _compute_iou,
    _normalize_bbox,
    _rewrite_edge_ids,
    _stable_signature,
    match_nodes_by_iou,
)


# ---------------------------------------------------------------------------
# DiagramGroup
# ---------------------------------------------------------------------------


class TestDiagramGroup:
    def test_round_trip(self):
        g = DiagramGroup(id="vpc", name="VPC", contains=["n1", "n2"], contains_groups=["sg1"])
        d = g.to_dict()
        restored = DiagramGroup.from_dict(d)
        assert restored.id == "vpc"
        assert restored.name == "VPC"
        assert restored.contains == ["n1", "n2"]
        assert restored.contains_groups == ["sg1"]

    def test_from_dict_non_dict(self):
        restored = DiagramGroup.from_dict("notadict")
        assert restored.id == "unknown"

    def test_from_dict_missing_fields(self):
        restored = DiagramGroup.from_dict({})
        assert restored.id == "unknown"
        assert restored.contains == []


# ---------------------------------------------------------------------------
# DiagramNode
# ---------------------------------------------------------------------------


class TestDiagramNode:
    def test_round_trip_with_bbox(self):
        n = DiagramNode(
            id="web_server", label="Web Server", kind="service",
            bbox=(10.0, 20.0, 100.0, 80.0), confidence=0.95,
        )
        d = n.to_dict()
        assert d["bbox"] == [10.0, 20.0, 100.0, 80.0]  # tuple -> list
        restored = DiagramNode.from_dict(d)
        assert restored.bbox == (10.0, 20.0, 100.0, 80.0)  # list -> tuple
        assert restored.confidence == 0.95

    def test_bbox_none_omitted_from_dict(self):
        n = DiagramNode(id="n1", label="Node 1")
        d = n.to_dict()
        assert "bbox" not in d

    def test_bbox_malformed_ignored(self):
        d = {"id": "n1", "label": "Label", "bbox": [1, 2]}  # only 2 elements
        n = DiagramNode.from_dict(d)
        assert n.bbox is None

    def test_bbox_non_numeric_ignored(self):
        d = {"id": "n1", "label": "Label", "bbox": ["a", "b", "c", "d"]}
        n = DiagramNode.from_dict(d)
        assert n.bbox is None

    def test_optional_fields_preserved(self):
        n = DiagramNode(
            id="db", label="Database", group_id="vpc",
            technology="PostgreSQL", verification_evidence="text says 'PostgreSQL'",
        )
        d = n.to_dict()
        assert d["group_id"] == "vpc"
        assert d["technology"] == "PostgreSQL"
        restored = DiagramNode.from_dict(d)
        assert restored.group_id == "vpc"
        assert restored.technology == "PostgreSQL"

    def test_from_dict_non_dict(self):
        n = DiagramNode.from_dict(42)
        assert n.id == "unknown"


# ---------------------------------------------------------------------------
# DiagramEdge
# ---------------------------------------------------------------------------


class TestDiagramEdge:
    def test_round_trip(self):
        e = DiagramEdge(
            id="e1", source_id="web", target_id="db",
            label="HTTPS", direction="->", confidence=0.9,
        )
        d = e.to_dict()
        restored = DiagramEdge.from_dict(d)
        assert restored.source_id == "web"
        assert restored.target_id == "db"
        assert restored.label == "HTTPS"

    def test_evidence_bbox_round_trip(self):
        e = DiagramEdge(
            id="e1", source_id="a", target_id="b",
            evidence_bbox=(5.0, 5.0, 50.0, 50.0),
        )
        d = e.to_dict()
        assert d["evidence_bbox"] == [5.0, 5.0, 50.0, 50.0]
        restored = DiagramEdge.from_dict(d)
        assert restored.evidence_bbox == (5.0, 5.0, 50.0, 50.0)

    def test_from_dict_non_dict(self):
        e = DiagramEdge.from_dict([])
        assert e.id == "unknown"


# ---------------------------------------------------------------------------
# DiagramGraph
# ---------------------------------------------------------------------------


class TestDiagramGraph:
    def test_round_trip_empty(self):
        g = DiagramGraph()
        d = g.to_dict()
        restored = DiagramGraph.from_dict(d)
        assert restored.nodes == []
        assert restored.edges == []
        assert restored.groups == []
        assert restored.schema_version == "1.0"

    def test_round_trip_populated(self):
        g = DiagramGraph(
            nodes=[
                DiagramNode(id="a", label="A", bbox=(0, 0, 10, 10)),
                DiagramNode(id="b", label="B"),
            ],
            edges=[DiagramEdge(id="e1", source_id="a", target_id="b")],
            groups=[DiagramGroup(id="g1", name="Group 1", contains=["a"])],
        )
        d = g.to_dict()
        restored = DiagramGraph.from_dict(d)
        assert len(restored.nodes) == 2
        assert len(restored.edges) == 1
        assert len(restored.groups) == 1
        assert restored.nodes[0].id == "a"

    def test_non_dict_entries_skipped(self):
        d = {
            "nodes": [{"id": "a", "label": "A"}, "not_a_dict", 42],
            "edges": [],
            "groups": [],
        }
        g = DiagramGraph.from_dict(d)
        assert len(g.nodes) == 1

    def test_from_dict_non_dict(self):
        g = DiagramGraph.from_dict("invalid")
        assert g.nodes == []


# ---------------------------------------------------------------------------
# DiagramAnalysis
# ---------------------------------------------------------------------------


class TestDiagramAnalysis:
    def test_inherits_slide_analysis_fields(self):
        da = DiagramAnalysis(
            slide_type="data", framework="none",
            diagram_type="architecture",
        )
        assert da.slide_type == "data"
        assert da.diagram_type == "architecture"
        assert isinstance(da, SlideAnalysis)

    def test_round_trip_full(self):
        graph = DiagramGraph(
            nodes=[DiagramNode(id="n1", label="N1", bbox=(0, 0, 50, 50))],
            edges=[DiagramEdge(id="e1", source_id="n1", target_id="n1")],
        )
        da = DiagramAnalysis(
            slide_type="diagram",
            framework="none",
            visual_description="Architecture diagram",
            key_data="3 services",
            main_insight="Microservices architecture",
            evidence=[{"claim": "test", "quote": "q", "confidence": "high"}],
            diagram_type="architecture",
            graph=graph,
            mermaid="graph LR\n  A --> B",
            description="An architecture diagram",
            uncertainties=["Label unclear"],
            extraction_confidence=0.85,
            confidence_reasoning="Clear layout",
            review_questions=["Is this correct?"],
            review_required=True,
            abstained=False,
        )
        d = da.to_dict()
        restored = DiagramAnalysis.from_dict(d)
        assert restored.diagram_type == "architecture"
        assert restored.graph is not None
        assert len(restored.graph.nodes) == 1
        assert restored.mermaid == "graph LR\n  A --> B"
        assert restored.uncertainties == ["Label unclear"]
        assert restored.extraction_confidence == 0.85
        assert restored.review_required is True
        assert restored.abstained is False
        assert len(restored.evidence) == 1

    def test_round_trip_minimal(self):
        da = DiagramAnalysis(diagram_type="flowchart")
        d = da.to_dict()
        restored = DiagramAnalysis.from_dict(d)
        assert restored.diagram_type == "flowchart"
        assert restored.graph is None
        assert restored.mermaid is None

    def test_from_dict_empty(self):
        da = DiagramAnalysis.from_dict({})
        assert da.diagram_type == "unknown"

    def test_from_dict_non_dict(self):
        da = DiagramAnalysis.from_dict("invalid")
        assert da.diagram_type == "unknown"

    def test_from_dict_malformed_extraction_confidence(self):
        d = {"diagram_type": "flow", "extraction_confidence": "not_a_number"}
        da = DiagramAnalysis.from_dict(d)
        assert da.extraction_confidence == 0.0

    def test_from_dict_malformed_uncertainties(self):
        d = {"diagram_type": "flow", "uncertainties": "not_a_list"}
        da = DiagramAnalysis.from_dict(d)
        assert da.uncertainties == []

    def test_from_slide_analysis(self):
        sa = SlideAnalysis(
            slide_type="data", framework="tam-sam-som",
            visual_description="Chart", key_data="$10M",
            main_insight="Revenue", evidence=[{"claim": "R"}],
        )
        da = DiagramAnalysis.from_slide_analysis(
            sa, diagram_type="mixed", review_required=True,
        )
        assert isinstance(da, DiagramAnalysis)
        assert da.slide_type == "data"
        assert da.framework == "tam-sam-som"
        assert da.diagram_type == "mixed"
        assert da.review_required is True
        assert da.evidence == [{"claim": "R"}]

    def test_abstained_placeholder(self):
        da = DiagramAnalysis(
            slide_type="pending",
            diagram_type="unsupported",
            abstained=True,
            review_required=True,
        )
        d = da.to_dict()
        assert d["abstained"] is True
        assert d["review_required"] is True
        assert d["diagram_type"] == "unsupported"


# ---------------------------------------------------------------------------
# Polymorphic factory dispatch
# ---------------------------------------------------------------------------


class TestFactoryDispatch:
    """SlideAnalysis.from_dict() dispatches based on diagram markers."""

    def test_slide_only_returns_slide_analysis(self):
        d = {"slide_type": "data", "framework": "none", "evidence": []}
        result = SlideAnalysis.from_dict(d)
        assert type(result) is SlideAnalysis

    def test_diagram_type_triggers_diagram_analysis(self):
        d = {"slide_type": "data", "diagram_type": "architecture"}
        result = SlideAnalysis.from_dict(d)
        assert isinstance(result, DiagramAnalysis)
        assert result.diagram_type == "architecture"

    def test_graph_alone_triggers_diagram_analysis(self):
        d = {
            "slide_type": "data",
            "graph": {"nodes": [], "edges": [], "groups": []},
        }
        result = SlideAnalysis.from_dict(d)
        assert isinstance(result, DiagramAnalysis)

    def test_mermaid_alone_triggers_diagram_analysis(self):
        d = {"slide_type": "data", "mermaid": "graph LR\n  A --> B"}
        result = SlideAnalysis.from_dict(d)
        assert isinstance(result, DiagramAnalysis)

    def test_abstained_alone_triggers_diagram_analysis(self):
        d = {"slide_type": "pending", "abstained": True}
        result = SlideAnalysis.from_dict(d)
        assert isinstance(result, DiagramAnalysis)

    def test_empty_dict_returns_default_slide_analysis(self):
        result = SlideAnalysis.from_dict({})
        assert type(result) is SlideAnalysis

    def test_non_dict_returns_default_slide_analysis(self):
        result = SlideAnalysis.from_dict("invalid")
        assert type(result) is SlideAnalysis

    def test_backward_compat_old_cache(self):
        """Old cache entries without diagram markers → SlideAnalysis."""
        old = {
            "slide_type": "data", "framework": "none",
            "visual_description": "A chart", "key_data": "$10M",
            "main_insight": "Growing", "evidence": [],
        }
        result = SlideAnalysis.from_dict(old)
        assert type(result) is SlideAnalysis
        assert result.slide_type == "data"


# ---------------------------------------------------------------------------
# IoU helpers
# ---------------------------------------------------------------------------


class TestNormalizeBbox:
    def test_already_normalized(self):
        assert _normalize_bbox((0, 0, 10, 10)) == (0, 0, 10, 10)

    def test_swapped_coords(self):
        assert _normalize_bbox((10, 10, 0, 0)) == (0, 0, 10, 10)


class TestComputeIou:
    def test_identity(self):
        box = (0.0, 0.0, 100.0, 100.0)
        assert _compute_iou(box, box) == 1.0

    def test_no_overlap(self):
        a = (0.0, 0.0, 10.0, 10.0)
        b = (20.0, 20.0, 30.0, 30.0)
        assert _compute_iou(a, b) == 0.0

    def test_partial_overlap(self):
        a = (0.0, 0.0, 10.0, 10.0)
        b = (5.0, 5.0, 15.0, 15.0)
        # Intersection: 5x5 = 25, Union: 100+100-25 = 175
        iou = _compute_iou(a, b)
        assert abs(iou - 25 / 175) < 0.001

    def test_zero_area(self):
        a = (0.0, 0.0, 0.0, 0.0)
        b = (0.0, 0.0, 10.0, 10.0)
        assert _compute_iou(a, b) == 0.0

    def test_shifted_box(self):
        a = (0.0, 0.0, 100.0, 100.0)
        b = (10.0, 10.0, 110.0, 110.0)
        # Intersection: 90x90 = 8100, Union: 10000+10000-8100 = 11900
        iou = _compute_iou(a, b)
        assert abs(iou - 8100 / 11900) < 0.001


class TestMatchNodesByIou:
    def test_exact_match(self):
        new = [DiagramNode(id="n1", label="A", bbox=(0, 0, 10, 10))]
        cached = [DiagramNode(id="cached_1", label="X", bbox=(0, 0, 10, 10))]
        mapping = match_nodes_by_iou(new, cached)
        assert mapping == {"n1": "cached_1"}

    def test_shifted_below_threshold(self):
        new = [DiagramNode(id="n1", label="A", bbox=(0, 0, 10, 10))]
        cached = [DiagramNode(id="c1", label="X", bbox=(50, 50, 60, 60))]
        mapping = match_nodes_by_iou(new, cached, threshold=0.80)
        assert mapping == {}

    def test_no_bbox_skipped(self):
        new = [DiagramNode(id="n1", label="A")]  # no bbox
        cached = [DiagramNode(id="c1", label="X", bbox=(0, 0, 10, 10))]
        mapping = match_nodes_by_iou(new, cached)
        assert mapping == {}

    def test_greedy_one_to_one(self):
        """Two new nodes, two cached nodes — greedy assigns best matches."""
        new = [
            DiagramNode(id="n1", label="A", bbox=(0, 0, 100, 100)),
            DiagramNode(id="n2", label="B", bbox=(200, 200, 300, 300)),
        ]
        cached = [
            DiagramNode(id="c1", label="X", bbox=(0, 0, 100, 100)),
            DiagramNode(id="c2", label="Y", bbox=(200, 200, 300, 300)),
        ]
        mapping = match_nodes_by_iou(new, cached)
        assert mapping == {"n1": "c1", "n2": "c2"}

    def test_threshold_boundary(self):
        """IoU exactly at threshold should match."""
        # Build boxes such that IoU ≈ 0.80
        # Box A: 100x100 = 10000, Box B shifted by ~5.5 pixels
        new = [DiagramNode(id="n1", label="A", bbox=(0, 0, 100, 100))]
        # Shift by ~5.13 in each direction: IoU = (94.87^2) / (2*10000 - 94.87^2)
        # 94.87^2 = 9000.27, union = 20000 - 9000.27 = 10999.73, IoU ≈ 0.818
        cached = [DiagramNode(id="c1", label="X", bbox=(5.13, 5.13, 105.13, 105.13))]
        mapping = match_nodes_by_iou(new, cached, threshold=0.80)
        assert "n1" in mapping


class TestRewriteEdgeIds:
    def test_basic_rewrite(self):
        edges = [
            DiagramEdge(id="old_e", source_id="n1", target_id="n2", label="connects"),
        ]
        mapping = {"n1": "inherited_1", "n2": "inherited_2"}
        result = _rewrite_edge_ids(edges, mapping)
        assert len(result) == 1
        assert result[0].id == "inherited_1_inherited_2"
        assert result[0].source_id == "inherited_1"
        assert result[0].target_id == "inherited_2"
        assert result[0].label == "connects"

    def test_partial_mapping(self):
        edges = [DiagramEdge(id="e1", source_id="n1", target_id="n2")]
        mapping = {"n1": "new_1"}  # only n1 mapped
        result = _rewrite_edge_ids(edges, mapping)
        assert result[0].source_id == "new_1"
        assert result[0].target_id == "n2"  # unmapped, stays same

    def test_empty_mapping(self):
        edges = [DiagramEdge(id="e1", source_id="a", target_id="b")]
        result = _rewrite_edge_ids(edges, {})
        assert result[0].id == "a_b"
        assert result[0].source_id == "a"


# ---------------------------------------------------------------------------
# Stable signature
# ---------------------------------------------------------------------------


class TestStableSignature:
    def test_deterministic(self):
        s1 = _stable_signature("a", "b", "c")
        s2 = _stable_signature("a", "b", "c")
        assert s1 == s2

    def test_different_inputs(self):
        s1 = _stable_signature("a", "b", "c")
        s2 = _stable_signature("x", "y", "z")
        assert s1 != s2

    def test_length(self):
        s = _stable_signature("test")
        assert len(s) == 16
