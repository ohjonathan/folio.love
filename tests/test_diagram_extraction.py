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
    _SUPPORTED_DIAGRAM_TYPES,
    _select_pass_c_images,
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

    def test_all_nine_actions(self):
        """All valid mutation actions including change_direction and regroup."""
        graph = self._base_graph()
        mutations = [
            {"action": "add_node", "data": {"label": "Cache", "kind": "service"}},
            {"action": "remove_node", "target_id": "db"},
            {"action": "relabel_node", "target_id": "web", "data": {"label": "API"}},
            {"action": "rebox_node", "target_id": "web", "data": {"bbox": [1, 1, 2, 2]}},
            {"action": "add_edge", "data": {"source_id": "web", "target_id": "cache", "label": "get"}},
            {"action": "relabel_edge", "target_id": "web_cache", "data": {"label": "set"}},
            {"action": "change_direction", "target_id": "web_cache", "data": {"direction": "reverse"}},
            {"action": "regroup", "target_id": "web", "data": {"group_id": "vpc"}},
            {"action": "remove_edge", "target_id": "web_cache"},
        ]
        result, acc = _apply_mutations(graph, mutations)
        assert acc["applied"] == 9

    def test_ghost_edge_rejected(self):
        """S-F1: add_edge referencing non-existent nodes is rejected."""
        graph = self._base_graph()
        mutations = [{"action": "add_edge", "data": {
            "source_id": "nonexistent_src", "target_id": "web", "label": "ghost"}}]
        result, acc = _apply_mutations(graph, mutations)
        assert len(result["edges"]) == 1  # only original edge
        assert acc["skipped_invalid_id"] == 1

    def test_change_direction(self):
        """S-F1: change_direction updates edge direction."""
        graph = self._base_graph()
        graph["edges"][0]["direction"] = "forward"
        mutations = [{"action": "change_direction", "target_id": "web_db",
                       "data": {"direction": "bidirectional"}}]
        result, acc = _apply_mutations(graph, mutations)
        assert result["edges"][0]["direction"] == "bidirectional"
        assert acc["applied"] == 1

    def test_regroup(self):
        """S-F1: regroup moves node to different group."""
        graph = self._base_graph()
        mutations = [{"action": "regroup", "target_id": "web",
                       "data": {"group_id": "vpc"}}]
        result, acc = _apply_mutations(graph, mutations)
        node = next(n for n in result["nodes"] if n["id"] == "web")
        assert node["group_id"] == "vpc"
        assert acc["applied"] == 1


# ---------------------------------------------------------------------------
# Sanity check (B3: accounting-based)
# ---------------------------------------------------------------------------


class TestSanityCheck:
    def test_under_threshold(self):
        """Small mutations below 40% ratio → safe."""
        orig = {"nodes": [{"id": f"n{i}", "label": f"L{i}"} for i in range(10)],
                "edges": [{"id": f"e{i}"} for i in range(5)]}
        mutated = dict(orig)
        accounting = {"applied": 2, "by_action": {"relabel_node": 2}}
        triggered, reason = _sanity_check(orig, mutated, accounting)
        assert triggered is False

    def test_over_mutation_ratio(self):
        """B3: Total mutations > 40% of elements → triggered."""
        orig = {"nodes": [{"id": f"n{i}", "label": f"L{i}"} for i in range(5)],
                "edges": [{"id": f"e{i}"} for i in range(5)]}
        # 10 elements total, 5 mutations = 50% > 40%
        accounting = {"applied": 5, "by_action": {"relabel_node": 3, "add_edge": 2}}
        triggered, reason = _sanity_check(orig, orig, accounting)
        assert triggered is True
        assert "50%" in reason

    def test_action_dominance(self):
        """B3: Single action > 50% of elements → triggered (via dominance or ratio)."""
        orig = {"nodes": [{"id": f"n{i}", "label": f"L{i}"} for i in range(4)],
                "edges": [{"id": f"e{i}"} for i in range(4)]}
        # 8 elements, relabel_edge=5 → triggers either via ratio (62%) or dominance (62%)
        accounting = {"applied": 5, "by_action": {"relabel_edge": 5}}
        triggered, reason = _sanity_check(orig, orig, accounting)
        assert triggered is True
        # Either "exceeds" (ratio) or "dominates" (dominance) — both are valid

    def test_mass_relabeling(self):
        """B3: >50% of surviving nodes relabeled → triggered."""
        orig = {"nodes": [{"id": f"n{i}", "label": f"L{i}"} for i in range(10)], "edges": []}
        mutated = {"nodes": [{"id": f"n{i}", "label": f"NEW{i}"} for i in range(10)], "edges": []}
        accounting = {"applied": 1, "by_action": {"relabel_node": 1}}  # low ratio
        triggered, reason = _sanity_check(orig, mutated, accounting)
        assert triggered is True
        assert "relabeled" in reason

    def test_empty_original(self):
        """Empty graph has 0 elements → no ratio, safe."""
        orig = {"nodes": [], "edges": []}
        mutated = {"nodes": [{"id": "a"}] * 5, "edges": []}
        accounting = {"applied": 5, "by_action": {"add_node": 5}}
        triggered, _ = _sanity_check(orig, mutated, accounting)
        assert triggered is False

    def test_edge_label_mutations_detected(self):
        """B3 repro: mutating all edge labels should trigger action dominance."""
        orig = {"nodes": [{"id": "n1", "label": "A"}],
                "edges": [{"id": f"e{i}"} for i in range(5)]}
        # 6 elements, relabel_edge=5 → 83% dominance
        accounting = {"applied": 5, "by_action": {"relabel_edge": 5}}
        triggered, reason = _sanity_check(orig, orig, accounting)
        assert triggered is True


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


# ---------------------------------------------------------------------------
# Regression: v1 type gate (proposal L62)
# ---------------------------------------------------------------------------


class TestSupportedDiagramTypes:
    """Regression tests for v1 type gate narrowing."""

    def test_architecture_supported(self):
        assert "architecture" in _SUPPORTED_DIAGRAM_TYPES

    def test_data_flow_supported(self):
        assert "data-flow" in _SUPPORTED_DIAGRAM_TYPES

    def test_only_two_types_supported(self):
        """v1 is strictly architecture + data-flow per proposal L62."""
        assert len(_SUPPORTED_DIAGRAM_TYPES) == 2

    @pytest.mark.parametrize("unsupported", [
        "flowchart", "sequence", "class", "entity-relationship",
        "network", "org-chart", "mindmap", "gantt", "timeline",
        "unknown", "state-machine", "deployment",
    ])
    def test_other_types_abstain(self, unsupported):
        """All non-v1 diagram types must NOT be in the supported set."""
        assert unsupported not in _SUPPORTED_DIAGRAM_TYPES


# ---------------------------------------------------------------------------
# Regression: per-batch highlight bbox selection
# ---------------------------------------------------------------------------


class TestPerBatchHighlights:
    """Regression tests for per-batch claim-relevant bbox extraction."""

    def test_node_claim_extracts_related_bbox(self):
        """Node claims should provide the node's related_bbox for highlighting."""
        graph = {
            "nodes": [
                {"id": "web", "label": "Web", "kind": "service",
                 "bbox": [10, 20, 100, 80], "confidence": 0.9},
            ],
            "edges": [],
        }
        claims = _generate_claims(graph)
        node_claims = [c for c in claims if c["claim_id"].startswith("node_exists_")]
        assert len(node_claims) == 1
        assert node_claims[0]["related_bbox"] == [10, 20, 100, 80]

    def test_edge_claim_bbox_lookup(self):
        """Edge claims should enable source+target bbox lookup."""
        graph = {
            "nodes": [
                {"id": "web", "label": "Web", "bbox": [10, 20, 100, 80]},
                {"id": "db", "label": "DB", "bbox": [200, 200, 300, 280]},
            ],
            "edges": [
                {"id": "web_db", "source_id": "web", "target_id": "db", "label": "SQL"},
            ],
        }
        claims = _generate_claims(graph)
        edge_claims = [c for c in claims if c["claim_id"].startswith("edge_exists_")]
        assert len(edge_claims) == 1
        # Edge claim should reference web_db
        assert edge_claims[0]["claim_id"] == "edge_exists_web_db"
        # Verify source+target bboxes are retrievable from node bbox map
        node_bbox_map = {n["id"]: tuple(n["bbox"]) for n in graph["nodes"] if n.get("bbox")}
        edge = graph["edges"][0]
        src_bbox = node_bbox_map.get(edge["source_id"])
        tgt_bbox = node_bbox_map.get(edge["target_id"])
        assert src_bbox == (10, 20, 100, 80)
        assert tgt_bbox == (200, 200, 300, 280)


# ---------------------------------------------------------------------------
# Regression: _select_pass_c_images with highlights
# ---------------------------------------------------------------------------


class TestSelectPassCImages:
    """Regression: Pass C images use highlight_regions."""

    def _mock_profile(self):
        class FakeProfile:
            escalation_level = "medium"
        return FakeProfile()

    def test_without_bboxes_returns_plain(self):
        """No bboxes → plain global image (no highlights)."""
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        parts = _select_pass_c_images(img, self._mock_profile(), node_bboxes=None)
        assert len(parts) == 1
        assert parts[0].role == "global"

    def test_with_bboxes_returns_highlighted(self):
        """With bboxes → image has highlight overlays (different bytes)."""
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        plain = _select_pass_c_images(img, self._mock_profile(), node_bboxes=None)
        highlighted = _select_pass_c_images(
            img, self._mock_profile(),
            node_bboxes=[(10, 10, 50, 50), (100, 100, 150, 150)],
        )
        assert len(highlighted) == 1
        # Highlighted image should differ from plain (overlay changes pixels)
        assert highlighted[0].image_data != plain[0].image_data

    def test_single_image_returned(self):
        """Pass C always returns exactly 1 global ImagePart."""
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        parts = _select_pass_c_images(
            img, self._mock_profile(),
            node_bboxes=[(10, 10, 50, 50)],
        )
        assert len(parts) == 1
        assert parts[0].role == "global"
        assert parts[0].media_type == "image/png"

# ---------------------------------------------------------------------------
# Stage 1: Pass A token hardening & zero-text confidence
# ---------------------------------------------------------------------------


class TestDiagramConfidenceTextValidation:
    """Stage 1 tests for _compute_diagram_confidence text_validation_unavailable."""

    def test_text_validation_unavailable_skips_text_poor_penalty(self):
        """When source text is unavailable, text-poor penalty is skipped."""
        graph = {
            "nodes": [{"id": "n1", "confidence": 0.9}],
            "edges": [],
        }
        # word_count=5 → normally text-poor (0.8x penalty)
        score_normal, r_normal = _compute_diagram_confidence(graph, word_count=5)
        score_unavail, r_unavail = _compute_diagram_confidence(
            graph, word_count=5, text_validation_unavailable=True,
        )
        assert "Text-poor" in r_normal
        assert "Text validation unavailable" in r_unavail
        assert score_unavail > score_normal

    def test_text_validation_unavailable_does_not_inflate_beyond_quality(self):
        """Unavailable text bypasses penalty but doesn't inflate beyond graph quality."""
        graph = {
            "nodes": [{"id": "n1", "confidence": 0.5}],  # low quality
            "edges": [],
        }
        score_unavail, _ = _compute_diagram_confidence(
            graph, word_count=5, text_validation_unavailable=True,
        )
        score_rich, _ = _compute_diagram_confidence(
            graph, word_count=50,
        )
        # Both should give similar scores — unavailable treated same as text-rich
        assert abs(score_unavail - score_rich) < 0.05

    def test_text_validation_unavailable_false_preserves_penalty(self):
        """When text_validation_unavailable=False, text-poor penalty still applies."""
        graph = {
            "nodes": [{"id": "n1", "confidence": 0.9}],
            "edges": [],
        }
        score, reasoning = _compute_diagram_confidence(
            graph, word_count=5, text_validation_unavailable=False,
        )
        assert "Text-poor" in reasoning

    def test_unavailable_reasoning_string_per_spec(self):
        """§6.3: reasoning must state 'validation unavailable' and 'penalty bypassed'."""
        graph = {
            "nodes": [{"id": "n1", "confidence": 0.9}],
            "edges": [],
        }
        _, reasoning = _compute_diagram_confidence(
            graph, word_count=5, text_validation_unavailable=True,
        )
        assert "Text validation unavailable" in reasoning
        assert "penalty bypassed" in reasoning


# ---------------------------------------------------------------------------
# Stage 1 R-1: Orchestrator-level Pass A truncation retry tests
# ---------------------------------------------------------------------------


class TestPassARetryOrchestrator:
    """R-1: Orchestrator-level tests for analyze_diagram_pages retry logic."""

    @staticmethod
    def _make_valid_pass_a_json():
        """Valid Pass A JSON response that will parse successfully."""
        return json.dumps({
            "diagram_type": "architecture",
            "nodes": [
                {"id": "n1", "label": "Start", "confidence": 0.9},
                {"id": "n2", "label": "End", "confidence": 0.9},
            ],
            "edges": [
                {"source": "n1", "target": "n2", "label": "next", "confidence": 0.9},
            ],
        })

    @staticmethod
    def _make_truncated_json():
        """Truncated JSON that won't parse."""
        return '{"diagram_type": "architecture", "nodes": [{"id": "n1", "lab'

    def _setup_mocks(self, tmp_path, call_responses):
        """Create minimal mocks for analyze_diagram_pages.

        call_responses: list of (raw_text, truncated) tuples for _call_llm.
        """
        from unittest.mock import patch, MagicMock
        from folio.pipeline.analysis import DiagramAnalysis
        from folio.pipeline.images import ImageResult
        from folio.pipeline.text import SlideText
        from folio.llm.types import ProviderOutput, TokenUsage

        # Create a fake image
        img_path = tmp_path / "slide-001.png"
        img_path.write_bytes(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

        pass1_results = {
            1: DiagramAnalysis(
                slide_type="data", diagram_type="architecture",
            ),
        }

        # Mock page profile
        mock_profile = MagicMock()
        mock_profile.classification = "diagram"
        mock_profile.crop_box = (0.0, 0.0, 612.0, 792.0)
        mock_profile.escalation_level = "simple"
        mock_profile.render_dpi = 150
        mock_profile.rotation = 0
        mock_profile.vector_count = 0
        mock_profile.char_count = 0
        mock_profile.bounded_texts = []
        page_profiles = {1: mock_profile}

        image_results = [
            ImageResult(path=img_path, slide_num=1, width=200, height=200),
        ]
        slide_texts = {
            1: SlideText(slide_num=1, full_text="Node A connects to Node B", elements=[]),
        }

        # Build _call_llm responses
        call_idx = [0]

        def mock_call_llm(*args, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx < len(call_responses):
                raw_text, truncated = call_responses[idx]
            else:
                raw_text, truncated = ("", False)
            output = ProviderOutput(
                raw_text=raw_text, truncated=truncated,
                provider_name="anthropic", model_name="test",
                usage=TokenUsage(input_tokens=100, output_tokens=200, total_tokens=300),
            )
            return output, output.usage

        return (
            pass1_results, page_profiles, image_results, slide_texts,
            mock_call_llm, call_idx,
        )

    def test_retry_fires_on_truncation_and_succeeds(self, tmp_path):
        """Truncated Pass A → retry with doubled budget → success."""
        from unittest.mock import patch, MagicMock
        from folio.pipeline.diagram_extraction import analyze_diagram_pages
        from PIL import Image as PILImage

        valid_json = self._make_valid_pass_a_json()
        truncated_json = self._make_truncated_json()

        (pass1, profiles, imgs, texts, mock_llm, call_idx) = self._setup_mocks(
            tmp_path,
            [
                (truncated_json, True),   # Pass A: truncated
                (valid_json, False),       # Retry: succeeds
            ],
        )

        mock_img = PILImage.new("RGB", (200, 200), "white")

        with patch("folio.pipeline.diagram_extraction._get_provider_and_client",
                    return_value=(MagicMock(), MagicMock())), \
             patch("folio.pipeline.diagram_extraction._call_llm", side_effect=mock_llm), \
             patch("folio.pipeline.diagram_extraction._load_page_image", return_value=mock_img), \
             patch("folio.pipeline.diagram_extraction.diagram_cache") as mock_cache:
            mock_cache.load_stage_cache.return_value = {}
            mock_cache.check_entry.return_value = None

            results, stats, meta = analyze_diagram_pages(
                pass1_results=pass1,
                page_profiles=profiles,
                image_results=imgs,
                slide_texts=texts,
                cache_dir=tmp_path,
                force_miss=True,
                slide_numbers=[1],
                diagram_max_tokens=8192,
            )

        # Retry should have fired: 2 _call_llm calls (Pass A + retry)
        assert call_idx[0] >= 2
        analysis = results[1]
        meta = analysis._extraction_metadata
        assert meta["pass_a_escalation_retry_attempted"] is True
        assert meta["pass_a_escalation_retry_succeeded"] is True
        assert meta["pass_a_requested_max_tokens"] == 8192

    def test_retry_skipped_at_max_budget(self, tmp_path):
        """When diagram_max_tokens=32768, retry skipped (B-3 guard)."""
        from unittest.mock import patch, MagicMock
        from folio.pipeline.diagram_extraction import analyze_diagram_pages
        from PIL import Image as PILImage

        truncated_json = self._make_truncated_json()

        (pass1, profiles, imgs, texts, mock_llm, call_idx) = self._setup_mocks(
            tmp_path,
            [
                (truncated_json, True),   # Pass A: truncated
                # No retry should fire
            ],
        )

        mock_img = PILImage.new("RGB", (200, 200), "white")

        with patch("folio.pipeline.diagram_extraction._get_provider_and_client",
                    return_value=(MagicMock(), MagicMock())), \
             patch("folio.pipeline.diagram_extraction._call_llm", side_effect=mock_llm), \
             patch("folio.pipeline.diagram_extraction._load_page_image", return_value=mock_img), \
             patch("folio.pipeline.diagram_extraction.diagram_cache") as mock_cache:
            mock_cache.load_stage_cache.return_value = {}
            mock_cache.check_entry.return_value = None

            results, stats, meta = analyze_diagram_pages(
                pass1_results=pass1,
                page_profiles=profiles,
                image_results=imgs,
                slide_texts=texts,
                cache_dir=tmp_path,
                force_miss=True,
                slide_numbers=[1],
                diagram_max_tokens=32768,  # Already at cap
            )

        # Only 1 _call_llm call (Pass A only, no retry)
        assert call_idx[0] == 1
        analysis = results[1]
        meta_dict = analysis._extraction_metadata
        assert meta_dict["pass_a_escalation_retry_attempted"] is False
        assert meta_dict["pass_a_parse_outcome"] == "truncated_invalid_json"

    def test_retry_fires_but_still_truncated(self, tmp_path):
        """Retry fires but second response is also truncated → recorded as failed."""
        from unittest.mock import patch, MagicMock
        from folio.pipeline.diagram_extraction import analyze_diagram_pages
        from PIL import Image as PILImage

        truncated_json = self._make_truncated_json()

        (pass1, profiles, imgs, texts, mock_llm, call_idx) = self._setup_mocks(
            tmp_path,
            [
                (truncated_json, True),    # Pass A: truncated
                (truncated_json, True),    # Retry: also truncated
            ],
        )

        mock_img = PILImage.new("RGB", (200, 200), "white")

        with patch("folio.pipeline.diagram_extraction._get_provider_and_client",
                    return_value=(MagicMock(), MagicMock())), \
             patch("folio.pipeline.diagram_extraction._call_llm", side_effect=mock_llm), \
             patch("folio.pipeline.diagram_extraction._load_page_image", return_value=mock_img), \
             patch("folio.pipeline.diagram_extraction.diagram_cache") as mock_cache:
            mock_cache.load_stage_cache.return_value = {}
            mock_cache.check_entry.return_value = None

            results, stats, meta = analyze_diagram_pages(
                pass1_results=pass1,
                page_profiles=profiles,
                image_results=imgs,
                slide_texts=texts,
                cache_dir=tmp_path,
                force_miss=True,
                slide_numbers=[1],
                diagram_max_tokens=8192,
            )

        assert call_idx[0] >= 2
        analysis = results[1]
        meta_dict = analysis._extraction_metadata
        assert meta_dict["pass_a_escalation_retry_attempted"] is True
        assert meta_dict["pass_a_escalation_retry_succeeded"] is False
        assert meta_dict["pass_a_parse_outcome"] == "truncated_invalid_json"
        assert analysis.review_required is True
