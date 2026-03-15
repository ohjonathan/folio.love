"""Tests for PR 4: diagram extraction pipeline logic.

Covers JSON parsing, normalization, bbox anchoring, mutations, sanity checks,
claim verification, completeness sweep, and confidence scoring.
"""

import json
import math
import pytest

from folio.pipeline.diagram_extraction import (
    _extract_diagram_json,
    _normalize_pass_a,
    _to_snake_case,
    _anchor_bboxes,
    _apply_mutations,
    _sanity_check,
    _generate_claims,
    _apply_verdicts,
    _should_sweep,
    _merge_sweep_results,
    _compute_diagram_confidence,
    _build_text_inventory,
    _update_inherited_fields,
)
from folio.pipeline.analysis import DiagramAnalysis


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------


class TestExtractDiagramJson:
    def test_clean_json(self):
        raw = '{"diagram_type": "flowchart", "nodes": []}'
        result = _extract_diagram_json(raw)
        assert result == {"diagram_type": "flowchart", "nodes": []}

    def test_markdown_fenced(self):
        raw = '```json\n{"diagram_type": "architecture"}\n```'
        result = _extract_diagram_json(raw)
        assert result == {"diagram_type": "architecture"}

    def test_preamble_then_json(self):
        raw = 'Here is the extracted structure:\n{"nodes": [{"id": "a"}]}'
        result = _extract_diagram_json(raw)
        assert result == {"nodes": [{"id": "a"}]}

    def test_malformed_json(self):
        raw = "{not valid json"
        result = _extract_diagram_json(raw)
        assert result is None

    def test_empty_string(self):
        assert _extract_diagram_json("") is None
        assert _extract_diagram_json("   ") is None
        assert _extract_diagram_json(None) is None

    def test_trailing_text(self):
        raw = '{"nodes": []}\nHope this helps!'
        result = _extract_diagram_json(raw)
        assert result == {"nodes": []}

    def test_array_extracts_inner_dict(self):
        """Array wrapper: function extracts the inner dict via brace finder."""
        raw = '[{"id": "a"}]'
        result = _extract_diagram_json(raw)
        assert result == {"id": "a"}


# ---------------------------------------------------------------------------
# ID normalization
# ---------------------------------------------------------------------------


class TestToSnakeCase:
    def test_basic(self):
        assert _to_snake_case("Web Server") == "web_server"

    def test_with_hyphens(self):
        assert _to_snake_case("load-balancer") == "load_balancer"

    def test_special_chars(self):
        assert _to_snake_case("API Gateway (v2)") == "api_gateway_v2"

    def test_empty(self):
        assert _to_snake_case("") == "node"


# ---------------------------------------------------------------------------
# Pass A normalization
# ---------------------------------------------------------------------------


class TestNormalizePassA:
    def test_basic_normalization(self):
        raw = {
            "diagram_type": "Architecture",
            "nodes": [
                {"id": "node1", "label": "Web Server", "kind": "service",
                 "bbox": [10, 20, 100, 80], "confidence": 0.95},
                {"id": "node2", "label": "Database", "kind": "database",
                 "bbox": [200, 200, 300, 280], "confidence": 0.9},
            ],
            "edges": [
                {"source_id": "node1", "target_id": "node2",
                 "label": "SQL", "direction": "forward", "confidence": 0.85},
            ],
            "groups": [],
        }
        result = _normalize_pass_a(raw)
        assert result["diagram_type"] == "architecture"
        assert len(result["nodes"]) == 2
        # Check snake_case IDs
        assert result["nodes"][0]["id"] == "web_server"
        assert result["nodes"][1]["id"] == "database"
        # Check edge references updated
        assert result["edges"][0]["source_id"] == "web_server"
        assert result["edges"][0]["target_id"] == "database"

    def test_unsupported_diagram(self):
        raw = {
            "diagram_type": "unknown",
            "unsupported_reason": "This is a data table, not a diagram",
            "nodes": [],
        }
        result = _normalize_pass_a(raw)
        assert result["unsupported_reason"] == "This is a data table, not a diagram"
        assert result["nodes"] == []

    def test_duplicate_labels_get_suffixed(self):
        raw = {
            "diagram_type": "flowchart",
            "nodes": [
                {"id": "n1", "label": "Process", "kind": "process"},
                {"id": "n2", "label": "Process", "kind": "process"},
            ],
            "edges": [],
            "groups": [],
        }
        result = _normalize_pass_a(raw)
        ids = {n["id"] for n in result["nodes"]}
        assert len(ids) == 2
        assert "process" in ids
        assert "process_2" in ids

    def test_empty_label_nodes_skipped(self):
        raw = {
            "diagram_type": "flowchart",
            "nodes": [
                {"id": "n1", "label": "", "kind": "other"},
                {"id": "n2", "label": "Valid", "kind": "other"},
            ],
            "edges": [],
            "groups": [],
        }
        result = _normalize_pass_a(raw)
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["label"] == "Valid"

    def test_bbox_validation(self):
        raw = {
            "diagram_type": "flowchart",
            "nodes": [
                {"id": "n1", "label": "A", "bbox": [0, 0, float("nan"), 10]},
                {"id": "n2", "label": "B", "bbox": [0, 0, 100, 100]},
            ],
            "edges": [],
            "groups": [],
        }
        result = _normalize_pass_a(raw)
        # NaN bbox should not be present
        assert "bbox" not in result["nodes"][0]
        assert result["nodes"][1]["bbox"] == [0, 0, 100, 100]

    def test_group_normalization(self):
        raw = {
            "diagram_type": "architecture",
            "nodes": [
                {"id": "n1", "label": "Web", "kind": "service", "group_id": "g1"},
            ],
            "edges": [],
            "groups": [
                {"id": "g1", "name": "VPC", "contains": ["n1"]},
            ],
        }
        result = _normalize_pass_a(raw)
        assert result["groups"][0]["id"] == "vpc"
        assert result["groups"][0]["contains"] == ["web"]
        assert result["nodes"][0]["group_id"] == "vpc"


# ---------------------------------------------------------------------------
# Bbox anchoring
# ---------------------------------------------------------------------------


class TestAnchorBboxes:
    def test_exact_match(self):
        nodes = [{"id": "web", "label": "Web Server", "bbox": [0, 0, 50, 50]}]
        bounded = [{"text": "Web Server", "bbox_pixel": (10, 20, 200, 60)}]
        result = _anchor_bboxes(nodes, bounded)
        assert result[0]["bbox"] == [10, 20, 200, 60]

    def test_fuzzy_match(self):
        nodes = [{"id": "web", "label": "Web Server v2", "bbox": [0, 0, 50, 50]}]
        bounded = [{"text": "Web Server", "bbox_pixel": (15, 25, 210, 65)}]
        result = _anchor_bboxes(nodes, bounded)
        # 2/3 word overlap < 0.80 threshold → no anchor
        assert result[0]["bbox"] == [0, 0, 50, 50]

    def test_no_bounded_texts(self):
        nodes = [{"id": "n1", "label": "Node", "bbox": [0, 0, 50, 50]}]
        result = _anchor_bboxes(nodes, [])
        assert result[0]["bbox"] == [0, 0, 50, 50]

    def test_single_word_exact(self):
        nodes = [{"id": "db", "label": "Database", "bbox": [0, 0, 50, 50]}]
        bounded = [{"text": "Database", "bbox_pixel": (100, 100, 300, 150)}]
        result = _anchor_bboxes(nodes, bounded)
        assert result[0]["bbox"] == [100, 100, 300, 150]


# ---------------------------------------------------------------------------
# Pass B mutations
# ---------------------------------------------------------------------------


class TestApplyMutations:
    def _base_graph(self):
        return {
            "diagram_type": "architecture",
            "nodes": [
                {"id": "web", "label": "Web", "kind": "service", "bbox": [0, 0, 50, 50]},
                {"id": "db", "label": "DB", "kind": "database", "bbox": [100, 100, 200, 200]},
            ],
            "edges": [
                {"id": "web_db", "source_id": "web", "target_id": "db", "label": "SQL"},
            ],
            "groups": [],
        }

    def test_add_node(self):
        graph = self._base_graph()
        mutations = [
            {"action": "add_node", "data": {
                "label": "Cache", "kind": "service", "bbox": [50, 50, 80, 80]}},
        ]
        result, acc = _apply_mutations(graph, mutations)
        assert len(result["nodes"]) == 3
        assert acc["applied"] == 1

    def test_remove_node(self):
        graph = self._base_graph()
        mutations = [{"action": "remove_node", "target_id": "web"}]
        result, acc = _apply_mutations(graph, mutations)
        assert len(result["nodes"]) == 1
        # Edge referencing removed node should be gone
        assert len(result["edges"]) == 0
        assert acc["applied"] == 1

    def test_relabel_node(self):
        graph = self._base_graph()
        mutations = [{"action": "relabel_node", "target_id": "web",
                       "data": {"label": "API Server"}}]
        result, acc = _apply_mutations(graph, mutations)
        node = next(n for n in result["nodes"] if n["id"] == "web")
        assert node["label"] == "API Server"

    def test_rebox_node(self):
        graph = self._base_graph()
        mutations = [{"action": "rebox_node", "target_id": "web",
                       "data": {"bbox": [5, 5, 55, 55]}}]
        result, acc = _apply_mutations(graph, mutations)
        node = next(n for n in result["nodes"] if n["id"] == "web")
        assert node["bbox"] == [5, 5, 55, 55]

    def test_add_edge(self):
        graph = self._base_graph()
        mutations = [{"action": "add_edge", "data": {
            "source_id": "db", "target_id": "web", "label": "response"}}]
        result, acc = _apply_mutations(graph, mutations)
        assert len(result["edges"]) == 2

    def test_remove_edge(self):
        graph = self._base_graph()
        mutations = [{"action": "remove_edge", "target_id": "web_db"}]
        result, acc = _apply_mutations(graph, mutations)
        assert len(result["edges"]) == 0

    def test_relabel_edge(self):
        graph = self._base_graph()
        mutations = [{"action": "relabel_edge", "target_id": "web_db",
                       "data": {"label": "HTTPS"}}]
        result, acc = _apply_mutations(graph, mutations)
        assert result["edges"][0]["label"] == "HTTPS"

    def test_invalid_id_skipped(self):
        graph = self._base_graph()
        mutations = [{"action": "remove_node", "target_id": "nonexistent"}]
        result, acc = _apply_mutations(graph, mutations)
        assert len(result["nodes"]) == 2
        assert acc["skipped_invalid_id"] == 1

    def test_unknown_action_skipped(self):
        graph = self._base_graph()
        mutations = [{"action": "destroy_everything", "target_id": "web"}]
        result, acc = _apply_mutations(graph, mutations)
        assert len(result["nodes"]) == 2
        assert acc["skipped_unknown_action"] == 1

    def test_all_seven_actions(self):
        graph = self._base_graph()
        mutations = [
            {"action": "add_node", "data": {"label": "Cache", "kind": "service"}},
            {"action": "remove_node", "target_id": "db"},
            {"action": "relabel_node", "target_id": "web", "data": {"label": "API"}},
            {"action": "rebox_node", "target_id": "web", "data": {"bbox": [1, 1, 2, 2]}},
            {"action": "add_edge", "data": {"source_id": "web", "target_id": "cache", "label": "get"}},
            {"action": "relabel_edge", "target_id": "web_cache", "data": {"label": "set"}},
            {"action": "remove_edge", "target_id": "web_cache"},
        ]
        result, acc = _apply_mutations(graph, mutations)
        assert acc["applied"] == 7


# ---------------------------------------------------------------------------
# Sanity check
# ---------------------------------------------------------------------------


class TestSanityCheck:
    def test_under_threshold(self):
        orig = {"nodes": [{"id": "a"}] * 10, "edges": [{"id": "e"}] * 5}
        mutated = {"nodes": [{"id": "a"}] * 11, "edges": [{"id": "e"}] * 6}
        assert _sanity_check(orig, mutated) is False

    def test_over_node_threshold(self):
        orig = {"nodes": [{"id": "a"}] * 10, "edges": []}
        mutated = {"nodes": [{"id": "a"}] * 14, "edges": []}  # 40% increase
        assert _sanity_check(orig, mutated) is True

    def test_over_edge_threshold(self):
        orig = {"nodes": [], "edges": [{"id": "e"}] * 10}
        mutated = {"nodes": [], "edges": [{"id": "e"}] * 15}  # 50% increase
        assert _sanity_check(orig, mutated) is True

    def test_empty_original(self):
        orig = {"nodes": [], "edges": []}
        mutated = {"nodes": [{"id": "a"}] * 5, "edges": []}
        assert _sanity_check(orig, mutated) is False


# ---------------------------------------------------------------------------
# Claim generation and verification
# ---------------------------------------------------------------------------


class TestGenerateClaims:
    def test_node_claims(self):
        graph = {
            "nodes": [
                {"id": "web", "label": "Web", "kind": "service", "bbox": [0, 0, 50, 50]},
            ],
            "edges": [],
        }
        claims = _generate_claims(graph)
        assert len(claims) >= 1
        assert claims[0]["claim_id"] == "node_exists_web"

    def test_edge_claims(self):
        graph = {
            "nodes": [
                {"id": "a", "label": "A", "kind": "service"},
                {"id": "b", "label": "B", "kind": "service"},
            ],
            "edges": [
                {"id": "a_b", "source_id": "a", "target_id": "b", "label": "calls"},
            ],
        }
        claims = _generate_claims(graph)
        edge_claims = [c for c in claims if c["type"] == "edge_existence"]
        assert len(edge_claims) == 1

    def test_technology_claim(self):
        graph = {
            "nodes": [
                {"id": "db", "label": "DB", "kind": "database", "technology": "PostgreSQL"},
            ],
            "edges": [],
        }
        claims = _generate_claims(graph)
        tech_claims = [c for c in claims if c["type"] == "node_attribute"]
        assert len(tech_claims) == 1
        assert "PostgreSQL" in tech_claims[0]["text"]


class TestApplyVerdicts:
    def test_refuted_removes_node(self):
        """S6: Refuted nodes are pruned, not just penalized."""
        graph = {
            "nodes": [{"id": "web", "label": "Web", "confidence": 0.9}],
            "edges": [],
        }
        verdicts = [{"claim_id": "node_exists_web", "verdict": "refuted", "correction": "API"}]
        result = _apply_verdicts(graph, verdicts)
        assert len(result["nodes"]) == 0

    def test_refuted_removes_orphaned_edges(self):
        """S6: Edges referencing refuted nodes are also pruned."""
        graph = {
            "nodes": [
                {"id": "web", "label": "Web", "confidence": 0.9},
                {"id": "db", "label": "DB", "confidence": 0.9},
            ],
            "edges": [
                {"id": "web_db", "source_id": "web", "target_id": "db", "confidence": 0.8},
            ],
        }
        verdicts = [{"claim_id": "node_exists_web", "verdict": "refuted"}]
        result = _apply_verdicts(graph, verdicts)
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["id"] == "db"
        assert len(result["edges"]) == 0  # orphaned

    def test_uncertain_slightly_lowers(self):
        graph = {
            "nodes": [{"id": "web", "label": "Web", "confidence": 0.9}],
            "edges": [],
        }
        verdicts = [{"claim_id": "node_exists_web", "verdict": "uncertain", "correction": None}]
        result = _apply_verdicts(graph, verdicts)
        assert result["nodes"][0]["confidence"] == pytest.approx(0.72)

    def test_confirmed_unchanged(self):
        graph = {
            "nodes": [{"id": "web", "label": "Web", "confidence": 0.9}],
            "edges": [],
        }
        verdicts = [{"claim_id": "node_exists_web", "verdict": "confirmed", "correction": None}]
        result = _apply_verdicts(graph, verdicts)
        assert result["nodes"][0]["confidence"] == 0.9


# ---------------------------------------------------------------------------
# Completeness sweep
# ---------------------------------------------------------------------------


class TestShouldSweep:
    def test_many_nodes(self):
        """S4: Threshold is ≥25 nodes."""
        graph = {"nodes": [{"id": f"n{i}"} for i in range(26)]}
        assert _should_sweep(graph, word_count=50) is True

    def test_many_words(self):
        """S4: Threshold is ≥150 words."""
        graph = {"nodes": [{"id": "n1"}]}
        assert _should_sweep(graph, word_count=150) is True

    def test_below_thresholds(self):
        graph = {"nodes": [{"id": "n1"}]}
        assert _should_sweep(graph, word_count=30) is False

    def test_under_node_threshold(self):
        """S4: 10 nodes is below the 25 threshold."""
        graph = {"nodes": [{"id": f"n{i}"} for i in range(10)]}
        assert _should_sweep(graph, word_count=50) is False


class TestMergeSweepResults:
    def test_new_nodes_added(self):
        graph = {
            "diagram_type": "architecture",
            "nodes": [{"id": "web", "label": "Web"}],
            "edges": [],
            "groups": [],
        }
        sweep = {
            "found_nodes": [{"label": "Cache", "kind": "service", "confidence": 0.8}],
            "found_edges": [],
        }
        result = _merge_sweep_results(graph, sweep)
        assert len(result["nodes"]) == 2

    def test_duplicate_node_not_added(self):
        graph = {
            "diagram_type": "architecture",
            "nodes": [{"id": "web", "label": "Web"}],
            "edges": [],
            "groups": [],
        }
        sweep = {
            "found_nodes": [{"label": "Web", "kind": "service"}],
            "found_edges": [],
        }
        result = _merge_sweep_results(graph, sweep)
        assert len(result["nodes"]) == 1


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class TestDiagramConfidence:
    def test_text_rich(self):
        graph = {
            "nodes": [{"id": "n1", "confidence": 0.9}],
            "edges": [{"id": "e1", "confidence": 0.8}],
        }
        score, reasoning = _compute_diagram_confidence(graph, word_count=50)
        assert 0.70 <= score <= 1.0
        assert "Text-rich" in reasoning

    def test_text_poor(self):
        graph = {
            "nodes": [{"id": "n1", "confidence": 0.9}],
            "edges": [],
        }
        score, reasoning = _compute_diagram_confidence(graph, word_count=10)
        assert score < 0.9  # 0.8x penalty
        assert "Text-poor" in reasoning

    def test_text_rich_threshold_at_20(self):
        """m2: Text-rich threshold is >=20, not >=30."""
        graph = {
            "nodes": [{"id": "n1", "confidence": 0.9}],
            "edges": [],
        }
        score20, r20 = _compute_diagram_confidence(graph, word_count=20)
        score19, r19 = _compute_diagram_confidence(graph, word_count=19)
        assert "Text-rich" in r20
        assert "Text-poor" in r19

    def test_floor_at_010(self):
        graph = {
            "nodes": [{"id": "n1", "confidence": 0.1}],
            "edges": [],
        }
        score, _ = _compute_diagram_confidence(
            graph, word_count=5, sanity_triggered=True,
        )
        assert score >= 0.10

    def test_no_nodes(self):
        graph = {"nodes": [], "edges": []}
        score, reasoning = _compute_diagram_confidence(graph, word_count=50)
        assert score == 0.10
        assert "No nodes" in reasoning

    def test_bonuses_applied(self):
        graph = {
            "nodes": [{"id": "n1", "confidence": 0.8}],
            "edges": [],
        }
        score_base, _ = _compute_diagram_confidence(graph, word_count=50)
        score_bonus, _ = _compute_diagram_confidence(
            graph, word_count=50, pass_c_run=True, sweep_run=True,
        )
        assert score_bonus > score_base

    def test_sanity_penalty(self):
        graph = {
            "nodes": [{"id": "n1", "confidence": 0.8}],
            "edges": [],
        }
        score_normal, _ = _compute_diagram_confidence(graph, word_count=50)
        score_sanity, _ = _compute_diagram_confidence(
            graph, word_count=50, sanity_triggered=True,
        )
        assert score_sanity < score_normal


# ---------------------------------------------------------------------------
# Text inventory
# ---------------------------------------------------------------------------


class TestBuildTextInventory:
    def test_basic(self):
        texts = [
            {"text": "Hello World", "bbox_pixel": (10, 20, 100, 40)},
            {"text": "Goodbye", "bbox_pixel": (10, 50, 100, 70)},
        ]
        inv = _build_text_inventory(texts, 1000, 1000)
        assert 'TEXT: "Hello World"' in inv
        assert 'TEXT: "Goodbye"' in inv

    def test_empty(self):
        assert _build_text_inventory([], 100, 100) == "(no text detected)"

    def test_sorted_top_to_bottom(self):
        texts = [
            {"text": "Bottom", "bbox_pixel": (10, 200, 100, 220)},
            {"text": "Top", "bbox_pixel": (10, 10, 100, 30)},
        ]
        inv = _build_text_inventory(texts, 1000, 1000)
        lines = inv.strip().split("\n")
        assert "Top" in lines[0]
        assert "Bottom" in lines[1]


# ---------------------------------------------------------------------------
# Inherited field update
# ---------------------------------------------------------------------------


class TestUpdateInheritedFields:
    def test_pure_diagram_overwrites(self):
        da = DiagramAnalysis(slide_type="diagram", visual_description="Old desc")
        graph = {
            "diagram_type": "architecture",
            "nodes": [{"id": "web", "label": "Web Server"}],
            "edges": [],
        }
        result = _update_inherited_fields(da, graph, is_mixed=False)
        assert "Architecture" in result.visual_description
        assert "Old desc" not in result.visual_description

    def test_mixed_appends(self):
        da = DiagramAnalysis(slide_type="data", visual_description="Chart data")
        graph = {
            "diagram_type": "flowchart",
            "nodes": [{"id": "start", "label": "Start"}],
            "edges": [],
        }
        result = _update_inherited_fields(da, graph, is_mixed=True)
        assert "Chart data" in result.visual_description
        assert "Flowchart" in result.visual_description


# ---------------------------------------------------------------------------
# _extraction_metadata round-trip
# ---------------------------------------------------------------------------


class TestExtractionMetadata:
    def test_round_trip(self):
        da = DiagramAnalysis(
            diagram_type="architecture",
            _extraction_metadata={"pass_a_model": "claude-3", "total_usage": {"tokens": 1000}},
        )
        d = da.to_dict()
        assert d["_extraction_metadata"]["pass_a_model"] == "claude-3"
        restored = DiagramAnalysis.from_dict(d)
        assert restored._extraction_metadata["pass_a_model"] == "claude-3"

    def test_missing_metadata_defaults_to_empty(self):
        d = {"diagram_type": "flowchart"}
        da = DiagramAnalysis.from_dict(d)
        assert da._extraction_metadata == {}

    def test_non_dict_metadata_defaults_to_empty(self):
        d = {"diagram_type": "flowchart", "_extraction_metadata": "bad"}
        da = DiagramAnalysis.from_dict(d)
        assert da._extraction_metadata == {}

    def test_empty_metadata_not_serialized(self):
        da = DiagramAnalysis(diagram_type="flowchart")
        d = da.to_dict()
        assert "_extraction_metadata" not in d
