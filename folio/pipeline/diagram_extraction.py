"""PR 4: Diagram extraction pipeline — Passes A, B, C + completeness sweep.

Owns prompt strings, JSON parsing, normalization, bbox anchoring,
mutations, claim verification, completeness sweep, confidence scoring,
and the top-level ``analyze_diagram_pages`` orchestrator.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from PIL import Image

from ..llm.runtime import RateLimiter, execute_with_retry
from ..llm.types import (
    ImagePart,
    ProviderInput,
    ProviderOutput,
    ProviderRuntimeSettings,
    StageLLMMetadata,
    TokenUsage,
)
from .analysis import (
    CacheStats,
    DiagramAnalysis,
    DiagramEdge,
    DiagramGraph,
    DiagramGroup,
    DiagramNode,
    SlideAnalysis,
    _hash_image,
    match_nodes_by_iou,
    _rewrite_edge_ids,
)
from . import diagram_cache
from .image_strategy import prepare_images, highlight_regions

if TYPE_CHECKING:
    from .inspect import PageProfile
    from .images import ImageResult
    from .text import SlideText

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt strings (inline, per spec §8)
# ---------------------------------------------------------------------------

DIAGRAM_EXTRACTION_PROMPT = """\
You are a precise diagram structure extractor.

Given a slide image containing a diagram, extract its complete graph structure.

TEXT INVENTORY (already extracted from the page — use for matching labels):
$text_inventory

Return a SINGLE JSON object with this exact structure:

{
  "diagram_type": "<architecture|flowchart|sequence|class|entity-relationship|network|org-chart|mindmap|concept-map|state-machine|deployment|venn|gantt|timeline|swimlane|data-flow|hierarchy|process|comparison|matrix|mixed|unknown>",
  "unsupported_reason": null,
  "nodes": [
    {
      "id": "<snake_case_id>",
      "label": "<exact text from diagram>",
      "kind": "<service|database|queue|user|external|process|decision|start|end|note|container|other>",
      "bbox": [x0, y0, x1, y1],
      "group_id": "<parent group id or null>",
      "technology": "<technology label if visible, else null>",
      "confidence": 0.95
    }
  ],
  "edges": [
    {
      "id": "<source_target>",
      "source_id": "<node id>",
      "target_id": "<node id>",
      "label": "<edge label or empty string>",
      "direction": "<forward|reverse|bidirectional|none>",
      "evidence_bbox": [x0, y0, x1, y1],
      "confidence": 0.9
    }
  ],
  "groups": [
    {
      "id": "<snake_case_id>",
      "name": "<group label>",
      "contains": ["<node_id>", ...],
      "contains_groups": ["<group_id>", ...]
    }
  ]
}

Rules:
1. Use ONLY text from the TEXT INVENTORY for labels.
2. bbox coordinates must be pixel-space [x0, y0, x1, y1] from the image.
3. Node IDs must be snake_case derived from label: "Web Server" → "web_server".
4. Edge IDs use format "source_target".
5. Set "unsupported_reason" to a string if the diagram type cannot be \
represented as a node-edge graph (e.g., pure data tables, photos, decorative art).
6. Include ALL visible elements — do not skip peripheral nodes.
7. Return ONLY the JSON object, no markdown fences, no prose."""


DIAGRAM_MUTATION_PROMPT = """\
You are a visual critic for diagram extraction accuracy.

ORIGINAL IMAGE is shown. Below is the previously extracted graph structure.

TEXT INVENTORY:
$text_inventory

CURRENT GRAPH:
```json
$current_graph
```

Compare the extracted graph against the actual image and issue mutations \
to fix any discrepancies:

Return a SINGLE JSON object:

{
  "mutations": [
    {
      "action": "<add_node|remove_node|relabel_node|rebox_node|add_edge|remove_edge|relabel_edge>",
      "target_id": "<existing node/edge ID>",
      "data": { ... }
    }
  ],
  "reasoning": "<brief explanation of changes>"
}

Action schemas:
- add_node: data = {id, label, kind, bbox, group_id?, technology?, confidence}
- remove_node: target_id only
- relabel_node: target_id + data = {label}
- rebox_node: target_id + data = {bbox: [x0,y0,x1,y1]}
- add_edge: data = {id, source_id, target_id, label, direction, evidence_bbox?, confidence}
- remove_edge: target_id only
- relabel_edge: target_id + data = {label}

Rules:
1. Use ONLY text from the TEXT INVENTORY for labels.
2. Do NOT redesign the graph — only fix extraction errors.
3. If the graph is already accurate, return {"mutations": [], "reasoning": "Graph matches image"}.
4. Return ONLY the JSON object."""


DIAGRAM_CLAIM_VERIFICATION_PROMPT = """\
You are verifying specific claims about a diagram against the actual image.

For each claim below, verify whether it is CORRECT by examining the image.

CLAIMS:
$claims_json

For each claim, respond with a verdict:
- "confirmed": the claim is accurate per the image
- "refuted": the claim is inaccurate
- "uncertain": cannot determine from the image

Return a SINGLE JSON object:

{
  "verdicts": [
    {
      "claim_id": "<claim ID>",
      "verdict": "<confirmed|refuted|uncertain>",
      "correction": "<if refuted, what should it be — else null>"
    }
  ]
}

Rules:
1. Examine the image carefully for each claim.
2. Return ONLY the JSON object."""


DIAGRAM_COMPLETENESS_PROMPT = """\
You are checking for missing diagram elements in a specific region.

The full diagram has already been extracted. This is a focused check on \
one region to find any MISSED elements.

REGION: $region_description
EXISTING NODES IN THIS REGION: $existing_nodes

TEXT INVENTORY (nearby text):
$region_text_inventory

Look for:
1. Nodes not yet captured
2. Edges between existing nodes not yet captured
3. Labels on existing edges that were missed

Return a SINGLE JSON object:

{
  "found_nodes": [
    {"id": "<snake_case>", "label": "<text>", "kind": "<kind>", \
"bbox": [x0,y0,x1,y1], "confidence": 0.8}
  ],
  "found_edges": [
    {"id": "<src_tgt>", "source_id": "<id>", "target_id": "<id>", \
"label": "<text>", "direction": "<dir>", "confidence": 0.8}
  ],
  "assessment": "<complete|incomplete — brief reason>"
}

Return ONLY the JSON object."""


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------

def _extract_diagram_json(raw_text: str) -> dict | None:
    """Parse diagram JSON from LLM response.

    Handles: clean JSON, markdown-fenced, preamble+JSON, trailing text.
    Returns None on failure.
    """
    if not raw_text or not raw_text.strip():
        return None

    text = raw_text.strip()

    # Attempt 1: direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, TypeError):
        pass

    # Attempt 2: strip markdown code fences
    if text.startswith("```"):
        newline_pos = text.find("\n")
        if newline_pos != -1:
            inner = text[newline_pos + 1:]
            if inner.rstrip().endswith("```"):
                inner = inner.rstrip()[:-3].rstrip()
                try:
                    result = json.loads(inner)
                    if isinstance(result, dict):
                        return result
                except (json.JSONDecodeError, TypeError):
                    pass

    # Attempt 3: find first { ... last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        try:
            result = json.loads(candidate)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, TypeError):
            pass

    return None


# ---------------------------------------------------------------------------
# Text inventory builder
# ---------------------------------------------------------------------------

def _build_text_inventory(
    bounded_texts: list[dict],
    page_width: float,
    page_height: float,
) -> str:
    """Build a text inventory string from bounded text elements.

    Each entry: TEXT: "<text>" @ bbox [x0, y0, x1, y1] px
    Sorted top-to-bottom, left-to-right.
    """
    if not bounded_texts:
        return "(no text detected)"

    # Sort: top-to-bottom (y0), then left-to-right (x0)
    entries = []
    for bt in bounded_texts:
        text = bt.get("text", "").strip()
        bbox = bt.get("bbox_pixel")
        if not text or bbox is None:
            continue
        entries.append((bbox[1], bbox[0], text, bbox))

    entries.sort()

    lines = []
    for _, _, text, bbox in entries:
        lines.append(
            f'TEXT: "{text}" @ bbox [{bbox[0]:.0f}, {bbox[1]:.0f}, '
            f'{bbox[2]:.0f}, {bbox[3]:.0f}] px'
        )

    return "\n".join(lines) if lines else "(no text detected)"


# ---------------------------------------------------------------------------
# ID normalization
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"[^a-z0-9_]")


def _to_snake_case(label: str) -> str:
    """Convert a label to snake_case ID."""
    s = label.lower().strip()
    s = s.replace(" ", "_").replace("-", "_")
    s = _ID_RE.sub("", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "node"


def _normalize_pass_a(data: dict) -> dict:
    """Normalize Pass A JSON: renumber node/group/edge IDs.

    Ensures snake_case IDs, deduplication, and consistent references.
    """
    # Check for unsupported diagram
    unsupported = data.get("unsupported_reason")
    if unsupported and isinstance(unsupported, str):
        return {
            "diagram_type": data.get("diagram_type", "unknown"),
            "unsupported_reason": unsupported,
            "nodes": [],
            "edges": [],
            "groups": [],
        }

    diagram_type = str(data.get("diagram_type", "unknown")).lower().strip()

    # Normalize nodes
    raw_nodes = data.get("nodes", [])
    if not isinstance(raw_nodes, list):
        raw_nodes = []

    nodes = []
    seen_ids: set[str] = set()
    old_to_new: dict[str, str] = {}

    for raw in raw_nodes:
        if not isinstance(raw, dict):
            continue
        old_id = str(raw.get("id", ""))
        label = str(raw.get("label", "")).strip()
        if not label:
            continue

        new_id = _to_snake_case(label)
        if new_id in seen_ids:
            counter = 2
            while f"{new_id}_{counter}" in seen_ids:
                counter += 1
            new_id = f"{new_id}_{counter}"

        seen_ids.add(new_id)
        if old_id:
            old_to_new[old_id] = new_id

        node = {
            "id": new_id,
            "label": label,
            "kind": str(raw.get("kind", "other")).lower().strip(),
        }

        # Optional bbox
        bbox_raw = raw.get("bbox")
        if isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) == 4:
            try:
                bbox = [float(v) for v in bbox_raw]
                if all(math.isfinite(v) for v in bbox):
                    node["bbox"] = bbox
            except (TypeError, ValueError):
                pass

        for opt in ("group_id", "technology"):
            val = raw.get(opt)
            if val is not None:
                node[opt] = str(val)

        try:
            node["confidence"] = float(raw.get("confidence", 0.9))
        except (TypeError, ValueError):
            node["confidence"] = 0.9

        nodes.append(node)

    # Normalize groups
    raw_groups = data.get("groups", [])
    if not isinstance(raw_groups, list):
        raw_groups = []

    groups = []
    group_old_to_new: dict[str, str] = {}
    seen_group_ids: set[str] = set()

    for raw in raw_groups:
        if not isinstance(raw, dict):
            continue
        old_gid = str(raw.get("id", ""))
        name = str(raw.get("name", "")).strip()
        if not name:
            continue

        new_gid = _to_snake_case(name)
        if new_gid in seen_group_ids:
            counter = 2
            while f"{new_gid}_{counter}" in seen_group_ids:
                counter += 1
            new_gid = f"{new_gid}_{counter}"

        seen_group_ids.add(new_gid)
        if old_gid:
            group_old_to_new[old_gid] = new_gid

        contains = [
            old_to_new.get(str(c), str(c))
            for c in (raw.get("contains") or [])
            if str(c)
        ]
        contains_groups = [str(c) for c in (raw.get("contains_groups") or [])]

        groups.append({
            "id": new_gid,
            "name": name,
            "contains": contains,
            "contains_groups": contains_groups,
        })

    # Fix group cross-refs
    for group in groups:
        group["contains_groups"] = [
            group_old_to_new.get(gid, gid)
            for gid in group["contains_groups"]
        ]

    # Fix node group_id refs
    for node in nodes:
        if "group_id" in node and node["group_id"]:
            node["group_id"] = group_old_to_new.get(
                node["group_id"], node["group_id"]
            )

    # Normalize edges
    raw_edges = data.get("edges", [])
    if not isinstance(raw_edges, list):
        raw_edges = []

    edges = []
    for raw in raw_edges:
        if not isinstance(raw, dict):
            continue
        source_id = old_to_new.get(
            str(raw.get("source_id", "")),
            str(raw.get("source_id", "")),
        )
        target_id = old_to_new.get(
            str(raw.get("target_id", "")),
            str(raw.get("target_id", "")),
        )
        if not source_id or not target_id:
            continue

        edge = {
            "source_id": source_id,
            "target_id": target_id,
            "label": str(raw.get("label", "")),
            "direction": str(raw.get("direction", "forward")).lower(),
        }

        # Evidence bbox
        ebbox = raw.get("evidence_bbox")
        if isinstance(ebbox, (list, tuple)) and len(ebbox) == 4:
            try:
                ebbox_f = [float(v) for v in ebbox]
                if all(math.isfinite(v) for v in ebbox_f):
                    edge["evidence_bbox"] = ebbox_f
            except (TypeError, ValueError):
                pass

        try:
            edge["confidence"] = float(raw.get("confidence", 0.9))
        except (TypeError, ValueError):
            edge["confidence"] = 0.9

        edges.append(edge)

    # Assign edge IDs (source_target format with dedup)
    edge_pair_counts: dict[str, int] = {}
    for edge in edges:
        pair = f"{edge['source_id']}_{edge['target_id']}"
        count = edge_pair_counts.get(pair, 0)
        edge["id"] = pair if count == 0 else f"{pair}_{count}"
        edge_pair_counts[pair] = count + 1

    return {
        "diagram_type": diagram_type,
        "unsupported_reason": None,
        "nodes": nodes,
        "edges": edges,
        "groups": groups,
    }


# ---------------------------------------------------------------------------
# Bbox anchoring
# ---------------------------------------------------------------------------

def _anchor_bboxes(
    nodes: list[dict],
    bounded_texts: list[dict],
) -> list[dict]:
    """Anchor node bboxes to real text positions from bounded_texts.

    For each node, searches bounded_texts for the closest label match.
    If found with >=80% word overlap, adopts the bounded_text's bbox.

    Returns a new list of node dicts (m1: does not mutate input).
    """
    if not bounded_texts:
        return [dict(n) for n in nodes]

    result = []
    for node in nodes:
        node = dict(node)  # m1: copy to avoid mutating input
        label = node.get("label", "")
        if not label:
            result.append(node)
            continue

        best_overlap = 0.0
        best_bbox = None

        label_words = set(label.lower().split())
        if not label_words:
            result.append(node)
            continue

        for bt in bounded_texts:
            bt_text = bt.get("text", "").strip()
            bt_bbox = bt.get("bbox_pixel")
            if not bt_text or bt_bbox is None:
                continue

            bt_words = set(bt_text.lower().split())
            if not bt_words:
                continue

            overlap = len(label_words & bt_words) / max(
                len(label_words), len(bt_words)
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_bbox = bt_bbox

        if best_overlap >= 0.80 and best_bbox is not None:
            node["bbox"] = list(best_bbox)

        result.append(node)

    return result


# ---------------------------------------------------------------------------
# B1: Evidence-driven image selection
# ---------------------------------------------------------------------------

# B4: v1-supported diagram types — system architecture and data flow only
# Per proposal L62: "System architecture and data flow only. All other types abstain."
_SUPPORTED_DIAGRAM_TYPES = {"architecture", "data-flow"}


def _select_pass_a_images(
    page_img: Image.Image,
    profile: "PageProfile",
) -> tuple[ImagePart, ...]:
    """Select image parts for Pass A based on diagram complexity.

    Simple diagrams: global-only (1 ImagePart).
    Medium/dense diagrams: global + tiles (5 ImageParts).
    """
    escalation = getattr(profile, "escalation_level", "simple")
    if escalation == "simple":
        # Global-only for simple diagrams
        from .image_strategy import _resize_to_max_edge, _to_png_bytes, _MAX_LONG_EDGE
        global_img = _resize_to_max_edge(page_img, _MAX_LONG_EDGE)
        return (ImagePart(
            image_data=_to_png_bytes(global_img),
            role="global",
            media_type="image/png",
            detail="auto",
        ),)
    return tuple(prepare_images(page_img, profile))


def _select_pass_c_images(
    page_img: Image.Image,
    profile: "PageProfile",
    node_bboxes: list[tuple[float, float, float, float]] | None = None,
) -> tuple[ImagePart, ...]:
    """Select image parts for Pass C claim verification.

    Uses highlight_regions to overlay semi-transparent rectangles over
    detected node bboxes, giving the verifier spatial evidence context.
    Falls back to plain global image if no bboxes or overlay fails.
    """
    from .image_strategy import _resize_to_max_edge, _to_png_bytes, _MAX_LONG_EDGE
    escalation = getattr(profile, "escalation_level", "simple")
    detail = "high" if escalation in {"medium", "dense"} else "auto"

    # Overlay node highlights if bboxes available
    base_img = page_img
    if node_bboxes:
        try:
            base_img = highlight_regions(page_img, node_bboxes)
        except Exception:
            base_img = page_img  # fallback to plain image

    global_img = _resize_to_max_edge(base_img, _MAX_LONG_EDGE)
    return (ImagePart(
        image_data=_to_png_bytes(global_img),
        role="global",
        media_type="image/png",
        detail=detail,
    ),)


# ---------------------------------------------------------------------------
# Mutation application (Pass B)
# ---------------------------------------------------------------------------

_VALID_MUTATION_ACTIONS = {
    "add_node", "remove_node", "relabel_node", "rebox_node",
    "add_edge", "remove_edge", "relabel_edge",
    "change_direction", "regroup",
}


def _apply_mutations(
    graph_dict: dict,
    mutations: list[dict],
) -> tuple[dict, dict]:
    """Apply Pass B mutations to a graph dict.

    Returns (mutated_graph, accounting) where accounting tracks counts.
    Mutations with invalid IDs or unknown actions are skipped.
    """
    # S3: Deep copy to prevent in-place mutation of original graph
    nodes = [dict(n) for n in graph_dict.get("nodes", [])]
    edges = [dict(e) for e in graph_dict.get("edges", [])]
    groups = [dict(g) for g in graph_dict.get("groups", [])]

    node_ids = {n["id"] for n in nodes}
    edge_ids = {e["id"] for e in edges}

    accounting = {
        "applied": 0,
        "skipped_invalid_id": 0,
        "skipped_unknown_action": 0,
        "by_action": {},
    }

    for mutation in mutations:
        if not isinstance(mutation, dict):
            continue

        action = str(mutation.get("action", ""))
        target_id = str(mutation.get("target_id", ""))
        data = mutation.get("data") or {}
        if not isinstance(data, dict):
            data = {}

        if action not in _VALID_MUTATION_ACTIONS:
            accounting["skipped_unknown_action"] += 1
            continue

        if action == "add_node":
            node_data = dict(data)
            new_id = _to_snake_case(str(node_data.get("label", "")))
            if not new_id or new_id in node_ids:
                if new_id in node_ids:
                    counter = 2
                    while f"{new_id}_{counter}" in node_ids:
                        counter += 1
                    new_id = f"{new_id}_{counter}"
            node_data["id"] = new_id
            nodes.append(node_data)
            node_ids.add(new_id)
            accounting["applied"] += 1
            accounting["by_action"]["add_node"] = accounting["by_action"].get("add_node", 0) + 1

        elif action == "remove_node":
            if target_id not in node_ids:
                accounting["skipped_invalid_id"] += 1
                continue
            nodes = [n for n in nodes if n["id"] != target_id]
            node_ids.discard(target_id)
            # Also remove edges referencing this node (S5: update edge_ids)
            removed_edges = {
                e["id"] for e in edges
                if e.get("source_id") == target_id or e.get("target_id") == target_id
            }
            edges = [
                e for e in edges
                if e.get("source_id") != target_id and e.get("target_id") != target_id
            ]
            edge_ids -= removed_edges
            accounting["applied"] += 1
            accounting["by_action"]["remove_node"] = accounting["by_action"].get("remove_node", 0) + 1

        elif action == "relabel_node":
            if target_id not in node_ids:
                accounting["skipped_invalid_id"] += 1
                continue
            new_label = str(data.get("label", ""))
            if new_label:
                for n in nodes:
                    if n["id"] == target_id:
                        n["label"] = new_label
                        break
            accounting["applied"] += 1
            accounting["by_action"]["relabel_node"] = accounting["by_action"].get("relabel_node", 0) + 1

        elif action == "rebox_node":
            if target_id not in node_ids:
                accounting["skipped_invalid_id"] += 1
                continue
            bbox_raw = data.get("bbox")
            if isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) == 4:
                try:
                    bbox = [float(v) for v in bbox_raw]
                    if all(math.isfinite(v) for v in bbox):
                        for n in nodes:
                            if n["id"] == target_id:
                                n["bbox"] = bbox
                                break
                except (TypeError, ValueError):
                    pass
            accounting["applied"] += 1
            accounting["by_action"]["rebox_node"] = accounting["by_action"].get("rebox_node", 0) + 1

        elif action == "add_edge":
            edge_data = dict(data)
            source = edge_data.get("source_id", "")
            target = edge_data.get("target_id", "")
            # S-F1: Reject ghost edges — both endpoints must exist
            if source and target and source in node_ids and target in node_ids:
                eid = f"{source}_{target}"
                if eid in edge_ids:
                    counter = 1
                    while f"{eid}_{counter}" in edge_ids:
                        counter += 1
                    eid = f"{eid}_{counter}"
                edge_data["id"] = eid
                edges.append(edge_data)
                edge_ids.add(eid)
                accounting["applied"] += 1
                accounting["by_action"]["add_edge"] = accounting["by_action"].get("add_edge", 0) + 1
            else:
                accounting["skipped_invalid_id"] += 1

        elif action == "remove_edge":
            if target_id not in edge_ids:
                accounting["skipped_invalid_id"] += 1
                continue
            edges = [e for e in edges if e["id"] != target_id]
            edge_ids.discard(target_id)
            accounting["applied"] += 1
            accounting["by_action"]["remove_edge"] = accounting["by_action"].get("remove_edge", 0) + 1

        elif action == "relabel_edge":
            if target_id not in edge_ids:
                accounting["skipped_invalid_id"] += 1
                continue
            new_label = str(data.get("label", ""))
            if new_label:
                for e in edges:
                    if e["id"] == target_id:
                        e["label"] = new_label
                        break
            accounting["applied"] += 1
            accounting["by_action"]["relabel_edge"] = accounting["by_action"].get("relabel_edge", 0) + 1

        elif action == "change_direction":
            if target_id not in edge_ids:
                accounting["skipped_invalid_id"] += 1
                continue
            new_dir = str(data.get("direction", ""))
            if new_dir in {"forward", "reverse", "bidirectional", "none"}:
                for e in edges:
                    if e["id"] == target_id:
                        e["direction"] = new_dir
                        break
            accounting["applied"] += 1
            accounting["by_action"]["change_direction"] = accounting["by_action"].get("change_direction", 0) + 1

        elif action == "regroup":
            # Move node to a different group
            if target_id not in node_ids:
                accounting["skipped_invalid_id"] += 1
                continue
            new_group = data.get("group_id")
            for n in nodes:
                if n["id"] == target_id:
                    n["group_id"] = new_group
                    break
            accounting["applied"] += 1
            accounting["by_action"]["regroup"] = accounting["by_action"].get("regroup", 0) + 1

    return {
        "diagram_type": graph_dict.get("diagram_type", "unknown"),
        "nodes": nodes,
        "edges": edges,
        "groups": groups,
    }, accounting


# ---------------------------------------------------------------------------
# Sanity check (Pass B threshold)
# ---------------------------------------------------------------------------

def _sanity_check(
    original_graph: dict,
    mutated_graph: dict,
    accounting: dict,
    mutation_ratio_threshold: float = 0.40,
    action_dominance_threshold: float = 0.50,
) -> tuple[bool, str]:
    """Return (triggered, reason) if mutations exceed sanity thresholds.

    B3: Uses mutation accounting ratios, not graph-size deltas.
    Checks:
    1. Total mutation ratio: applied / (orig_nodes + orig_edges) > 40%
    2. Action dominance: any single action type > 50% of total elements
    3. Structural: >50% of surviving nodes relabeled
    """
    orig_nodes = len(original_graph.get("nodes", []))
    orig_edges = len(original_graph.get("edges", []))
    total_elements = orig_nodes + orig_edges

    applied = accounting.get("applied", 0) if accounting else 0

    # Check 1: Overall mutation ratio
    if total_elements > 0 and applied > 0:
        mutation_ratio = applied / total_elements
        if mutation_ratio > mutation_ratio_threshold:
            reason = (
                f"Mutation ratio {mutation_ratio:.0%} exceeds "
                f"{mutation_ratio_threshold:.0%} threshold "
                f"({applied} mutations on {total_elements} elements)"
            )
            logger.warning("Sanity check: %s", reason)
            return True, reason

    # Check 2: Single action dominance
    by_action = accounting.get("by_action", {}) if accounting else {}
    if total_elements > 0:
        for action_name, count in by_action.items():
            if count / total_elements > action_dominance_threshold:
                reason = (
                    f"Action '{action_name}' dominates: {count} of "
                    f"{total_elements} elements ({count/total_elements:.0%})"
                )
                logger.warning("Sanity check: %s", reason)
                return True, reason

    # Check 3: Structural delta — mass relabeling
    if orig_nodes > 0:
        orig_labels = {n.get("id"): n.get("label") for n in original_graph.get("nodes", [])}
        mut_labels = {n.get("id"): n.get("label") for n in mutated_graph.get("nodes", [])}
        common_ids = set(orig_labels) & set(mut_labels)
        if common_ids:
            relabeled = sum(
                1 for nid in common_ids
                if orig_labels[nid] != mut_labels[nid]
            )
            relabel_ratio = relabeled / len(common_ids)
            if relabel_ratio > 0.50:
                reason = (
                    f"{relabel_ratio:.0%} of nodes relabeled "
                    f"({relabeled}/{len(common_ids)})"
                )
                logger.warning("Sanity check: %s", reason)
                return True, reason

    return False, ""


# ---------------------------------------------------------------------------
# Claim generation and verification (Pass C)
# ---------------------------------------------------------------------------

def _generate_claims(graph_dict: dict) -> list[dict]:
    """Generate verifiable claims from the post-B graph.

    Each claim has: claim_id, text, type, related_bbox.
    """
    claims = []
    nodes = graph_dict.get("nodes", [])
    edges = graph_dict.get("edges", [])

    node_map = {n["id"]: n for n in nodes}

    for node in nodes:
        nid = node["id"]
        label = node.get("label", "")
        kind = node.get("kind", "other")
        bbox = node.get("bbox")

        claims.append({
            "claim_id": f"node_exists_{nid}",
            "text": f"Node '{label}' of kind '{kind}' exists in the diagram",
            "type": "node_existence",
            "related_bbox": bbox,
        })

        if node.get("technology"):
            claims.append({
                "claim_id": f"node_tech_{nid}",
                "text": f"Node '{label}' uses technology '{node['technology']}'",
                "type": "node_attribute",
                "related_bbox": bbox,
            })

    for edge in edges:
        eid = edge["id"]
        src = node_map.get(edge.get("source_id", ""), {})
        tgt = node_map.get(edge.get("target_id", ""), {})
        label = edge.get("label", "")

        claim_text = (
            f"Edge from '{src.get('label', '?')}' to '{tgt.get('label', '?')}'"
        )
        if label:
            claim_text += f" with label '{label}'"

        claims.append({
            "claim_id": f"edge_exists_{eid}",
            "text": claim_text,
            "type": "edge_existence",
            "related_bbox": edge.get("evidence_bbox"),
        })

    # S10: Group claims by entity so node existence + attributes stay together
    # This ensures a node's claims are in the same batch and aren't split
    node_claims_by_id: dict[str, list[dict]] = {}
    edge_claims_list: list[dict] = []

    for claim in claims:
        cid = claim.get("claim_id", "")
        if cid.startswith("node_exists_"):
            nid = cid[len("node_exists_"):]
            node_claims_by_id.setdefault(nid, []).insert(0, claim)
        elif cid.startswith("node_tech_"):
            nid = cid[len("node_tech_"):]
            node_claims_by_id.setdefault(nid, []).append(claim)
        else:
            edge_claims_list.append(claim)

    grouped: list[dict] = []
    for group in node_claims_by_id.values():
        grouped.extend(group)
    grouped.extend(edge_claims_list)

    return grouped


def _apply_verdicts(
    graph_dict: dict,
    verdicts: list[dict],
) -> dict:
    """Apply verification verdicts to node/edge confidence scores.

    - confirmed: confidence unchanged
    - refuted: node/edge REMOVED (S6: prune refuted elements)
    - uncertain: confidence *= 0.8
    """
    nodes = list(graph_dict.get("nodes", []))
    edges = list(graph_dict.get("edges", []))

    verdict_map = {v["claim_id"]: v for v in verdicts if isinstance(v, dict)}

    # S6: Collect refuted node IDs for pruning
    refuted_node_ids: set[str] = set()

    surviving_nodes = []
    for node in nodes:
        nid = node["id"]
        v = verdict_map.get(f"node_exists_{nid}")
        if v and v.get("verdict") == "refuted":
            refuted_node_ids.add(nid)
            continue  # S6: prune refuted node
        if v and v.get("verdict") == "uncertain":
            node["confidence"] = node.get("confidence", 0.9) * 0.8
        surviving_nodes.append(node)

    # S6: Prune edges referencing refuted nodes + refuted edges
    surviving_edges = []
    for edge in edges:
        eid = edge["id"]
        if edge.get("source_id") in refuted_node_ids:
            continue  # orphaned by refuted source
        if edge.get("target_id") in refuted_node_ids:
            continue  # orphaned by refuted target
        v = verdict_map.get(f"edge_exists_{eid}")
        if v and v.get("verdict") == "refuted":
            continue  # S6: prune refuted edge
        if v and v.get("verdict") == "uncertain":
            edge["confidence"] = edge.get("confidence", 0.9) * 0.8
        surviving_edges.append(edge)

    # M-NEW-1: Scrub refuted node IDs from groups.contains
    groups = list(graph_dict.get("groups", []))
    if refuted_node_ids:
        for group in groups:
            if "contains" in group:
                group["contains"] = [
                    nid for nid in group["contains"]
                    if nid not in refuted_node_ids
                ]

    return {
        "diagram_type": graph_dict.get("diagram_type", "unknown"),
        "nodes": surviving_nodes,
        "edges": surviving_edges,
        "groups": groups,
    }


# ---------------------------------------------------------------------------
# Completeness sweep
# ---------------------------------------------------------------------------

def _should_sweep(
    graph_dict: dict,
    word_count: int,
    node_threshold: int = 25,
    word_threshold: int = 150,
) -> bool:
    """Determine if a completeness sweep is warranted.

    S4: Only dense diagrams (>=25 nodes or >=150 words) trigger sweep,
    aligned with proposal thresholds.
    """
    num_nodes = len(graph_dict.get("nodes", []))
    return num_nodes >= node_threshold or word_count >= word_threshold


def _merge_sweep_results(
    graph_dict: dict,
    sweep_results: dict,
) -> dict:
    """Merge completeness sweep results into the graph.

    Adds new nodes and edges not already present.
    """
    nodes = list(graph_dict.get("nodes", []))
    edges = list(graph_dict.get("edges", []))
    groups = list(graph_dict.get("groups", []))

    existing_node_ids = {n["id"] for n in nodes}
    existing_edge_ids = {e["id"] for e in edges}

    for new_node in sweep_results.get("found_nodes", []):
        if not isinstance(new_node, dict):
            continue
        nid = _to_snake_case(str(new_node.get("label", "")))
        if nid and nid not in existing_node_ids:
            new_node["id"] = nid
            # S7: Force low confidence and review flag on sweep discoveries
            new_node["confidence"] = min(
                float(new_node.get("confidence", 0.5)), 0.5
            )
            new_node["sweep_discovered"] = True
            nodes.append(new_node)
            existing_node_ids.add(nid)

    for new_edge in sweep_results.get("found_edges", []):
        if not isinstance(new_edge, dict):
            continue
        src = new_edge.get("source_id", "")
        tgt = new_edge.get("target_id", "")
        eid = f"{src}_{tgt}"
        if eid not in existing_edge_ids:
            new_edge["id"] = eid
            # S-F2: Force low confidence on sweep-added edges
            new_edge["confidence"] = min(
                float(new_edge.get("confidence", 0.5)), 0.5
            )
            new_edge["sweep_discovered"] = True
            edges.append(new_edge)
            existing_edge_ids.add(eid)

    return {
        "diagram_type": graph_dict.get("diagram_type", "unknown"),
        "nodes": nodes,
        "edges": edges,
        "groups": groups,
    }


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def _compute_diagram_confidence(
    graph_dict: dict,
    word_count: int,
    pass_c_run: bool = False,
    sweep_run: bool = False,
    sanity_triggered: bool = False,
    text_validation_unavailable: bool = False,
) -> tuple[float, str]:
    """Compute extraction confidence score.

    Text-rich path (word_count >= 20):
        - Base from average node+edge confidence
        - Bbox coverage bonus (up to +0.05)
        - Uncertainty penalty (low-conf nodes)
        - Bonus for Pass C (+0.05)
        - Bonus for sweep (+0.03)
        - Penalty for sanity short-circuit (-0.15)

    Text-poor path (word_count < 20):
        - Base from average confidence * 0.8
        - Same bonuses/penalties

    Floor: 0.10 (never returns 0.0 for a real extraction).
    Cap: 1.0
    """
    nodes = graph_dict.get("nodes", [])
    edges = graph_dict.get("edges", [])

    if not nodes:
        return 0.10, "No nodes extracted"

    all_confidences = [n.get("confidence", 0.9) for n in nodes]
    all_confidences.extend(e.get("confidence", 0.9) for e in edges)

    avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.5

    # S8: Enhanced confidence scoring with text inventory coverage
    # and mutation magnitude
    # Stage 1: when source text is unavailable (scanned PDF), skip the
    # text-poor penalty — the diagram was extracted from vision alone and
    # the word_count metric is meaningless.
    text_rich = text_validation_unavailable or word_count >= 20
    base = avg_conf if text_rich else avg_conf * 0.8

    # S8: Text inventory coverage factor — nodes with text matches score higher
    nodes_with_bbox = sum(1 for n in nodes if n.get("bbox"))
    if nodes:
        coverage_ratio = nodes_with_bbox / len(nodes)
        coverage_bonus = coverage_ratio * 0.05  # up to +0.05
        base += coverage_bonus
    else:
        coverage_ratio = 0.0
        coverage_bonus = 0.0

    # S8: Uncertainty penalty — nodes with low confidence drag score down
    low_conf_nodes = sum(1 for n in nodes if n.get("confidence", 0.9) < 0.6)
    if nodes and low_conf_nodes > 0:
        uncertainty_penalty = (low_conf_nodes / len(nodes)) * 0.1
        base -= uncertainty_penalty
    else:
        uncertainty_penalty = 0.0

    reasons = []
    if text_validation_unavailable:
        reasons.append(
            f"Text validation unavailable (no source text, {word_count} words); "
            f"text-poor penalty bypassed"
        )
    elif text_rich:
        reasons.append(f"Text-rich ({word_count} words)")
    else:
        reasons.append(f"Text-poor ({word_count} words, 0.8x base)")

    if coverage_bonus > 0:
        reasons.append(f"Bbox coverage {coverage_ratio:.0%} (+{coverage_bonus:.3f})")
    if uncertainty_penalty > 0:
        reasons.append(f"{low_conf_nodes} low-conf nodes (-{uncertainty_penalty:.3f})")

    if pass_c_run:
        base += 0.05
        reasons.append("Pass C verified (+0.05)")
    if sweep_run:
        base += 0.03
        reasons.append("Sweep completed (+0.03)")
    if sanity_triggered:
        base -= 0.15
        reasons.append("Sanity short-circuit (-0.15)")

    score = max(0.10, min(1.0, base))
    reasoning = f"Score {score:.2f}: " + "; ".join(reasons)

    return score, reasoning


# ---------------------------------------------------------------------------
# Inherited field update
# ---------------------------------------------------------------------------

def _update_inherited_fields(
    analysis: DiagramAnalysis,
    graph_dict: dict,
    is_mixed: bool,
) -> DiagramAnalysis:
    """Update inherited SlideAnalysis fields from extraction results.

    Pure diagram pages: overwrite visual_description and key_data.
    Mixed pages: append to existing visual_description.
    """
    nodes = graph_dict.get("nodes", [])
    edges = graph_dict.get("edges", [])

    node_summary = ", ".join(n.get("label", "") for n in nodes[:5])
    if len(nodes) > 5:
        node_summary += f" (+{len(nodes) - 5} more)"

    diagram_desc = (
        f"{graph_dict.get('diagram_type', 'unknown').replace('-', ' ').title()} diagram "
        f"with {len(nodes)} nodes and {len(edges)} edges: {node_summary}"
    )

    if is_mixed:
        if analysis.visual_description:
            analysis.visual_description += f"\n\nDiagram extraction: {diagram_desc}"
        else:
            analysis.visual_description = diagram_desc
    else:
        analysis.visual_description = diagram_desc

    if not is_mixed:
        data_points = []
        for node in nodes:
            if node.get("technology"):
                data_points.append(f"{node['label']}: {node['technology']}")
        if data_points:
            analysis.key_data = "; ".join(data_points[:5])

    return analysis


# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------

def _get_provider_and_client(
    provider_name: str,
    api_key_env: str,
) -> tuple[Any, Any] | None:
    """Get a provider adapter and client. Returns None on failure."""
    try:
        from .analysis import get_provider
        provider = get_provider(provider_name)
        client = provider.create_client(api_key_env=api_key_env)
        return provider, client
    except Exception as e:
        logger.warning("Diagram provider '%s' unavailable: %s", provider_name, e)
        return None


def _call_llm(
    provider,
    client,
    model: str,
    prompt: str,
    image_parts: tuple[ImagePart, ...],
    settings: ProviderRuntimeSettings,
    limiter: RateLimiter,
    max_tokens: int = 4096,
) -> tuple[ProviderOutput | None, TokenUsage]:
    """Make a single LLM call with retry. Returns (output, usage)."""
    inp = ProviderInput(
        prompt=prompt,
        images=image_parts,
        max_tokens=max_tokens,
        temperature=0.0,
        require_store_false=settings.require_store_false,
    )
    try:
        output = execute_with_retry(provider, client, model, inp, settings, limiter)
        return output, output.usage
    except Exception as e:
        logger.warning("Diagram LLM call failed: %s", e)
        return None, TokenUsage()


# ---------------------------------------------------------------------------
# Build image parts from page image
# ---------------------------------------------------------------------------

def _load_page_image(image_result: "ImageResult") -> Image.Image | None:
    """Load a page image from an ImageResult."""
    try:
        return Image.open(image_result.path)
    except Exception as e:
        logger.warning("Failed to load image %s: %s", image_result.path, e)
        return None


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def analyze_diagram_pages(
    pass1_results: dict[int, SlideAnalysis],
    page_profiles: dict[int, "PageProfile"],
    image_results: list["ImageResult"],
    slide_texts: dict[int, "SlideText"],
    cache_dir: Path | None = None,
    force_miss: bool = False,
    provider_name: str = "anthropic",
    model: str = "claude-sonnet-4-20250514",
    api_key_env: str = "",
    all_provider_settings: dict[str, ProviderRuntimeSettings] | None = None,
    slide_numbers: list[int] | None = None,
    diagram_max_tokens: int = 16384,
) -> tuple[dict[int, SlideAnalysis], CacheStats, StageLLMMetadata]:
    """Run diagram extraction on diagram/mixed slides.

    Integrates Passes A, B, C, completeness sweep, confidence scoring,
    and inherited field updates.

    Args:
        pass1_results: Pass 1 analysis results (may include DiagramAnalysis).
        page_profiles: PageProfile per slide.
        image_results: Rendered image results per slide.
        slide_texts: Extracted text per slide.
        cache_dir: Cache directory (per deck).
        force_miss: Skip cache reads.
        provider_name: LLM provider name.
        model: LLM model name.
        api_key_env: API key env var.
        all_provider_settings: Per-provider runtime settings.
        slide_numbers: Which slides to process (diagram/mixed only).

    Returns:
        (updated_results, cache_stats, stage_metadata)
    """
    _all_settings = all_provider_settings or {}
    primary_settings = _all_settings.get(provider_name, ProviderRuntimeSettings())
    limiter = RateLimiter(
        rpm_limit=primary_settings.rate_limit_rpm,
        tpm_limit=primary_settings.rate_limit_tpm,
    )

    stage_meta = StageLLMMetadata(provider=provider_name, model=model)
    stats = CacheStats(pass_name="diagram")

    # Build image lookup
    image_by_slide: dict[int, "ImageResult"] = {}
    for ir in image_results:
        image_by_slide[ir.slide_num] = ir

    # Get provider + client
    provider_client = _get_provider_and_client(provider_name, api_key_env)
    if provider_client is None:
        # All diagram slides become pending
        for sn in (slide_numbers or []):
            if sn in pass1_results:
                da = pass1_results[sn]
                if isinstance(da, DiagramAnalysis):
                    da.review_required = True
        return pass1_results, stats, stage_meta

    provider, client = provider_client

    # Load caches (S-NEW-2/S1: removed dead pass_a_cache load)
    final_cache = {} if force_miss else diagram_cache.load_stage_cache(
        cache_dir, "final", provider_name, model, DIAGRAM_EXTRACTION_PROMPT
    )

    results = dict(pass1_results)

    for slide_num in sorted(slide_numbers or []):
        analysis = results.get(slide_num)
        if not isinstance(analysis, DiagramAnalysis):
            continue

        # Skip abstained slides
        if analysis.abstained:
            continue

        profile = page_profiles.get(slide_num)
        img_result = image_by_slide.get(slide_num)
        slide_text = slide_texts.get(slide_num)

        if profile is None or img_result is None:
            logger.warning("Slide %d: missing profile or image — skipping", slide_num)
            continue

        image_hash = _hash_image(img_result.path)
        is_mixed = profile.classification == "mixed"

        # Build text inventory and load page image BEFORE cache check
        # (needed for B2 dep hashes)
        bounded_texts = []
        if hasattr(profile, 'bounded_texts') and profile.bounded_texts:
            bounded_texts = [
                {"text": bt.text, "bbox_pixel": bt.pixel_bbox}
                for bt in profile.bounded_texts
                if bt.text and bt.pixel_bbox
            ]

        page_img = _load_page_image(img_result)
        if page_img is None:
            analysis.review_required = True
            results[slide_num] = analysis
            continue

        word_count = len((slide_text.full_text if slide_text else "").split())

        text_inventory = _build_text_inventory(
            bounded_texts,
            page_img.width,
            page_img.height,
        )

        # B2: Expanded dep hashes for cache invalidation
        text_inv_hash = diagram_cache.text_inventory_hash(text_inventory)
        profile_hash = diagram_cache.page_profile_hash(
            classification=profile.classification,
            escalation_level=getattr(profile, 'escalation_level', 'simple'),
            render_dpi=getattr(profile, 'render_dpi', 150),
            crop_box=getattr(profile, 'crop_box', (0.0, 0.0, 1.0, 1.0)),
            rotation=getattr(profile, 'rotation', 0),
            word_count=word_count,
            vector_count=getattr(profile, 'vector_count', 0),
            char_count=getattr(profile, 'char_count', 0),
            has_bounded_texts=bool(bounded_texts),
        )

        # Check final cache with expanded deps
        final_deps = {
            "_image_hash": image_hash,
            "_text_inventory_hash": text_inv_hash,
            "_profile_hash": profile_hash,
        }
        cached_final = diagram_cache.check_entry(final_cache, image_hash, final_deps)
        if cached_final is not None and not force_miss:
            stats.hits += 1
            results[slide_num] = DiagramAnalysis.from_dict(cached_final)
            logger.debug("Slide %d: using cached final diagram analysis", slide_num)
            page_img.close()
            continue

        stats.misses += 1
        logger.info("Diagram extraction slide %d...", slide_num)

        pass_a_images = _select_pass_a_images(page_img, profile)

        # --- Pass A: Extract ---
        pass_a_prompt = DIAGRAM_EXTRACTION_PROMPT.replace(
            "$text_inventory", text_inventory
        )

        # Stage 1: Use explicit token budget from config
        pass_a_requested_tokens = diagram_max_tokens
        pass_a_out, pass_a_usage = _call_llm(
            provider, client, model, pass_a_prompt,
            pass_a_images, primary_settings, limiter,
            max_tokens=pass_a_requested_tokens,
        )

        total_usage = pass_a_usage

        # Stage 1: Track Pass A metadata for diagnostics
        pass_a_truncated = pass_a_out.truncated if pass_a_out else False
        pass_a_raw_len = len(pass_a_out.raw_text) if pass_a_out and pass_a_out.raw_text else 0
        pass_a_escalation_attempted = False
        pass_a_escalation_succeeded = False
        pass_a_parse_outcome = "unknown"

        if pass_a_out is None or not pass_a_out.raw_text:
            pass_a_parse_outcome = "provider_failure"
            analysis.review_required = True
            analysis.review_questions = ["Pass A extraction failed (provider returned no output)"]
            analysis._extraction_metadata.update({
                "pass_a_requested_max_tokens": pass_a_requested_tokens,
                "pass_a_truncated": pass_a_truncated,
                "pass_a_raw_response_length": pass_a_raw_len,
                "pass_a_escalation_retry_attempted": False,
                "pass_a_escalation_retry_succeeded": False,
                "pass_a_parse_outcome": pass_a_parse_outcome,
            })
            results[slide_num] = analysis
            continue

        pass_a_raw = _extract_diagram_json(pass_a_out.raw_text)

        # Stage 1: Retry once on truncation with doubled budget capped at 32768
        if pass_a_raw is None and pass_a_truncated:
            escalated_tokens = min(pass_a_requested_tokens * 2, 32768)
            # B-3 fix: skip retry when budget can't actually increase
            if escalated_tokens > pass_a_requested_tokens:
                pass_a_escalation_attempted = True
                logger.info(
                    "Slide %d: Pass A truncated at %d tokens, retrying with %d",
                    slide_num, pass_a_requested_tokens, escalated_tokens,
                )
                retry_out, retry_usage = _call_llm(
                    provider, client, model, pass_a_prompt,
                    pass_a_images, primary_settings, limiter,
                    max_tokens=escalated_tokens,
                )
                total_usage = TokenUsage(
                    input_tokens=total_usage.input_tokens + retry_usage.input_tokens,
                    output_tokens=total_usage.output_tokens + retry_usage.output_tokens,
                    total_tokens=total_usage.total_tokens + retry_usage.total_tokens,
                )
                if retry_out and retry_out.raw_text:
                    pass_a_raw_len = len(retry_out.raw_text)
                    pass_a_truncated = retry_out.truncated
                    pass_a_raw = _extract_diagram_json(retry_out.raw_text)
                    if pass_a_raw is not None:
                        pass_a_escalation_succeeded = True
            else:
                logger.warning(
                    "Slide %d: Pass A truncated but already at max budget (%d); "
                    "skipping retry",
                    slide_num, pass_a_requested_tokens,
                )

        if pass_a_raw is None:
            pass_a_parse_outcome = "truncated_invalid_json" if pass_a_truncated else "invalid_json"
            analysis.review_required = True
            analysis.review_questions = [
                f"Pass A returned invalid JSON ({pass_a_parse_outcome})"
            ]
            analysis._extraction_metadata.update({
                "pass_a_requested_max_tokens": pass_a_requested_tokens,
                "pass_a_truncated": pass_a_truncated,
                "pass_a_raw_response_length": pass_a_raw_len,
                "pass_a_escalation_retry_attempted": pass_a_escalation_attempted,
                "pass_a_escalation_retry_succeeded": False,
                "pass_a_parse_outcome": pass_a_parse_outcome,
            })
            results[slide_num] = analysis
            continue

        pass_a_parse_outcome = "success"
        normalized = _normalize_pass_a(pass_a_raw)

        # Unsupported diagram detection
        if normalized.get("unsupported_reason"):
            analysis.abstained = True
            analysis.diagram_type = "unsupported"
            analysis.review_required = True
            analysis.description = normalized["unsupported_reason"]
            results[slide_num] = analysis
            continue

        # B4: Abstain on unsupported diagram types (allowlist, not denylist)
        diagram_type = normalized.get("diagram_type", "unknown")
        if diagram_type not in _SUPPORTED_DIAGRAM_TYPES:
            analysis.abstained = True
            analysis.diagram_type = diagram_type
            analysis.review_required = True
            analysis.review_questions = [
                f"Unsupported diagram type for v1 extraction: {diagram_type}"
            ]
            results[slide_num] = analysis
            continue

        # Anchor bboxes
        normalized["nodes"] = _anchor_bboxes(normalized["nodes"], bounded_texts)

        # --- Pass B: Mutate ---
        current_graph_json = json.dumps(normalized, indent=2)
        pass_b_prompt = DIAGRAM_MUTATION_PROMPT.replace(
            "$text_inventory", text_inventory
        ).replace("$current_graph", current_graph_json)

        pass_b_out, pass_b_usage = _call_llm(
            provider, client, model, pass_b_prompt,
            pass_a_images, primary_settings, limiter,
        )
        total_usage = TokenUsage(
            input_tokens=total_usage.input_tokens + pass_b_usage.input_tokens,
            output_tokens=total_usage.output_tokens + pass_b_usage.output_tokens,
            total_tokens=total_usage.total_tokens + pass_b_usage.total_tokens,
        )

        post_b_graph = normalized
        sanity_triggered = False
        mutation_accounting: dict = {}

        if pass_b_out and pass_b_out.raw_text:
            mutations_raw = _extract_diagram_json(pass_b_out.raw_text)
            if mutations_raw and isinstance(mutations_raw.get("mutations"), list):
                mutated, mutation_accounting = _apply_mutations(
                    normalized, mutations_raw["mutations"]
                )

                # B3: Sanity check using mutation accounting ratios
                sanity_triggered, sanity_reason = _sanity_check(
                    normalized, mutated, mutation_accounting
                )
                if sanity_triggered:
                    logger.warning("Slide %d: sanity triggered, abstaining", slide_num)
                    analysis.abstained = True
                    analysis.review_required = True
                    # B3: Store rejected mutation details in review_questions
                    analysis.review_questions = [
                        f"Sanity check triggered: {sanity_reason}",
                        f"Rejected mutations: {json.dumps(mutation_accounting.get('by_action', {}))}",
                    ]
                    post_b_graph = normalized
                else:
                    post_b_graph = mutated

        # --- Pass C: Claim verification (skip if sanity triggered) ---
        pass_c_attempted = False
        pass_c_verdicts_parsed = False
        claims = _generate_claims(post_b_graph)

        # Issue #4: Generate highlight-backed Pass C images using post-B node bboxes
        # Build node bbox lookup for per-batch highlights
        node_bbox_map: dict[str, tuple] = {}
        for n in post_b_graph.get("nodes", []):
            bbox = n.get("bbox")
            if bbox and len(bbox) == 4:
                node_bbox_map[n["id"]] = tuple(bbox)

        if claims and not sanity_triggered:
            pass_c_attempted = True
            # Batch claims (target 18 per batch)
            batch_size = 18
            all_verdicts = []

            # Build node map for edge claim bbox lookups
            node_map = {n["id"]: n for n in post_b_graph.get("nodes", [])}

            for batch_start in range(0, len(claims), batch_size):
                batch = claims[batch_start:batch_start + batch_size]
                claims_json = json.dumps(batch, indent=2)

                pass_c_prompt = DIAGRAM_CLAIM_VERIFICATION_PROMPT.replace(
                    "$claims_json", claims_json
                )

                # Per-batch highlights: only claim-relevant bboxes
                batch_bboxes = []
                for claim in batch:
                    cid = claim.get("claim_id", "")
                    # Node claims: highlight the node's bbox
                    if cid.startswith("node_exists_") or cid.startswith("node_tech_"):
                        rb = claim.get("related_bbox")
                        if rb and len(rb) == 4:
                            batch_bboxes.append(tuple(rb))
                    # Edge claims: highlight source + target bboxes
                    elif cid.startswith("edge_exists_"):
                        eid = cid[len("edge_exists_"):]
                        for edge in post_b_graph.get("edges", []):
                            if edge["id"] == eid:
                                src_id = edge.get("source_id", "")
                                tgt_id = edge.get("target_id", "")
                                if src_id in node_bbox_map:
                                    batch_bboxes.append(node_bbox_map[src_id])
                                if tgt_id in node_bbox_map:
                                    batch_bboxes.append(node_bbox_map[tgt_id])
                                break

                # Generate per-batch highlight images
                batch_images = _select_pass_c_images(
                    page_img, profile,
                    node_bboxes=batch_bboxes or None,
                )

                pass_c_out, pass_c_usage = _call_llm(
                    provider, client, model, pass_c_prompt,
                    batch_images, primary_settings, limiter,
                    max_tokens=2048,
                )
                total_usage = TokenUsage(
                    input_tokens=total_usage.input_tokens + pass_c_usage.input_tokens,
                    output_tokens=total_usage.output_tokens + pass_c_usage.output_tokens,
                    total_tokens=total_usage.total_tokens + pass_c_usage.total_tokens,
                )

                if pass_c_out and pass_c_out.raw_text:
                    verdicts_raw = _extract_diagram_json(pass_c_out.raw_text)
                    if verdicts_raw and isinstance(verdicts_raw.get("verdicts"), list):
                        all_verdicts.extend(verdicts_raw["verdicts"])
                        # B5: Only mark as parsed when verdicts actually extracted
                        pass_c_verdicts_parsed = True

            if all_verdicts:
                post_b_graph = _apply_verdicts(post_b_graph, all_verdicts)

        # Issue #1: If Pass C was attempted but produced no parseable verdicts,
        # flag for review — the verification step effectively failed
        if pass_c_attempted and not pass_c_verdicts_parsed:
            analysis.review_required = True
            if not analysis.review_questions:
                analysis.review_questions = []
            analysis.review_questions.append(
                "Pass C verification attempted but returned no parseable verdicts"
            )

        # --- Completeness sweep (B3: skip if sanity triggered) ---
        sweep_run = False
        if _should_sweep(post_b_graph, word_count) and not sanity_triggered:
            sweep_run = True
            # Use quadrant regions
            w, h = page_img.size
            quadrants = [
                ("top-left", 0, 0, w // 2, h // 2),
                ("top-right", w // 2, 0, w, h // 2),
                ("bottom-left", 0, h // 2, w // 2, h),
                ("bottom-right", w // 2, h // 2, w, h),
            ]

            for desc, qx0, qy0, qx1, qy1 in quadrants:
                # Find existing nodes in this quadrant
                existing_in_region = []
                for n in post_b_graph.get("nodes", []):
                    bbox = n.get("bbox")
                    if bbox and len(bbox) == 4:
                        cx = (bbox[0] + bbox[2]) / 2
                        cy = (bbox[1] + bbox[3]) / 2
                        if qx0 <= cx <= qx1 and qy0 <= cy <= qy1:
                            existing_in_region.append(n["id"])

                # Build region text inventory
                region_texts = []
                for bt in bounded_texts:
                    bp = bt.get("bbox_pixel")
                    if bp:
                        cx = (bp[0] + bp[2]) / 2
                        cy = (bp[1] + bp[3]) / 2
                        if qx0 <= cx <= qx1 and qy0 <= cy <= qy1:
                            region_texts.append(bt)

                region_inv = _build_text_inventory(region_texts, w, h)

                sweep_prompt = DIAGRAM_COMPLETENESS_PROMPT.replace(
                    "$region_description", desc
                ).replace(
                    "$existing_nodes", json.dumps(existing_in_region)
                ).replace(
                    "$region_text_inventory", region_inv
                )

                # Crop region image (m8: resize to max 2048px edge for provider limits)
                try:
                    region_img = page_img.crop((qx0, qy0, qx1, qy1))
                    max_edge = max(region_img.size)
                    if max_edge > 2048:
                        scale = 2048 / max_edge
                        new_w = int(region_img.width * scale)
                        new_h = int(region_img.height * scale)
                        region_img = region_img.resize(
                            (new_w, new_h), Image.LANCZOS
                        )
                    buf = io.BytesIO()
                    region_img.save(buf, format="PNG")
                    region_part = ImagePart(
                        image_data=buf.getvalue(),
                        role="region",
                        media_type="image/png",
                        detail="high",
                    )
                    sweep_images = (region_part,)
                except Exception:
                    sweep_images = pass_a_images  # fallback to global

                sweep_out, sweep_usage = _call_llm(
                    provider, client, model, sweep_prompt,
                    sweep_images, primary_settings, limiter,
                    max_tokens=2048,
                )
                total_usage = TokenUsage(
                    input_tokens=total_usage.input_tokens + sweep_usage.input_tokens,
                    output_tokens=total_usage.output_tokens + sweep_usage.output_tokens,
                    total_tokens=total_usage.total_tokens + sweep_usage.total_tokens,
                )

                if sweep_out and sweep_out.raw_text:
                    sweep_data = _extract_diagram_json(sweep_out.raw_text)
                    if sweep_data:
                        post_b_graph = _merge_sweep_results(post_b_graph, sweep_data)

        # --- Confidence scoring ---
        # Stage 1: Determine if source text validation was unavailable
        _text_validation_unavailable = (
            slide_text is None or not slide_text.full_text
            or not slide_text.full_text.strip()
        )
        # B5: Only award Pass C bonus if verdicts were actually parsed
        confidence, reasoning = _compute_diagram_confidence(
            post_b_graph, word_count,
            pass_c_run=pass_c_verdicts_parsed,
            sweep_run=sweep_run,
            sanity_triggered=sanity_triggered,
            text_validation_unavailable=_text_validation_unavailable,
        )

        # --- Build final DiagramAnalysis ---
        graph = DiagramGraph.from_dict(post_b_graph)

        # B4: Abstain on empty graph
        if len(graph.nodes) == 0:
            analysis.abstained = True
            analysis.review_required = True
            analysis.review_questions = [
                "Extraction produced zero nodes — possible empty or unrecognizable diagram"
            ]
            analysis.diagram_confidence = confidence
            analysis.extraction_confidence = confidence
            analysis.confidence_reasoning = reasoning
            results[slide_num] = analysis
            page_img.close()
            continue

        # Issue #2: IoU-based ID inheritance — check in-memory graph first,
        # then read stale on-disk cache (bypasses marker validation)
        prior_graph = None
        if analysis.graph and analysis.graph.nodes:
            prior_graph = analysis.graph
        else:
            # Load directly from disk, ignoring marker validation
            stale_entry = diagram_cache.load_stale_entry(
                cache_dir, "final", image_hash
            )
            if stale_entry is not None:
                try:
                    prior_da = DiagramAnalysis.from_dict(stale_entry)
                    if prior_da.graph and prior_da.graph.nodes:
                        prior_graph = prior_da.graph
                except Exception:
                    pass  # stale entry may not parse — skip gracefully

        if prior_graph and prior_graph.nodes:
            mapping = match_nodes_by_iou(graph.nodes, prior_graph.nodes)
            if mapping:
                for node in graph.nodes:
                    if node.id in mapping:
                        object.__setattr__(node, "id", mapping[node.id])
                graph = DiagramGraph(
                    nodes=graph.nodes,
                    edges=_rewrite_edge_ids(graph.edges, mapping),
                    groups=graph.groups,
                )

        analysis.diagram_type = post_b_graph.get("diagram_type", "unknown")
        analysis.graph = graph
        analysis.diagram_confidence = confidence
        analysis.extraction_confidence = confidence  # backward compat
        analysis.confidence_reasoning = reasoning

        # B4: Abstain on very low confidence
        if confidence < 0.30:
            analysis.abstained = True
            analysis.review_required = True
            if not analysis.review_questions:
                analysis.review_questions = [
                    f"Confidence {confidence:.2f} below abstention threshold (0.30)"
                ]
        elif confidence < 0.60:
            analysis.review_required = True

        # S-NEW-1: Review questions from low-confidence nodes
        # (guard: don't overwrite sanity-triggered review_questions)
        if not sanity_triggered:
            review_qs = []
            for node in graph.nodes:
                if node.confidence < 0.6:
                    review_qs.append(f"Low confidence node: {node.label}")
            # S7: Flag sweep-discovered nodes
            sweep_nodes = [
                n for n in post_b_graph.get("nodes", [])
                if n.get("sweep_discovered")
            ]
            for sn in sweep_nodes:
                review_qs.append(f"Sweep-discovered node: {sn.get('label', '?')}")
            if review_qs:
                analysis.review_questions = review_qs[:5]

        analysis = _update_inherited_fields(analysis, post_b_graph, is_mixed)

        # Populate _extraction_metadata
        analysis._extraction_metadata = {
            "pass_a_model": model,
            "pass_a_provider": provider_name,
            "pass_a_requested_max_tokens": pass_a_requested_tokens,
            "pass_a_truncated": pass_a_truncated,
            "pass_a_raw_response_length": pass_a_raw_len,
            "pass_a_escalation_retry_attempted": pass_a_escalation_attempted,
            "pass_a_escalation_retry_succeeded": pass_a_escalation_succeeded,
            "pass_a_parse_outcome": pass_a_parse_outcome,
            "pass_b_mutations": mutation_accounting,
            "pass_b_sanity_triggered": sanity_triggered,
            "pass_c_attempted": pass_c_attempted,
            "pass_c_verdicts_parsed": pass_c_verdicts_parsed,
            "pass_c_claims_count": len(claims),
            "sweep_run": sweep_run,
            "text_validation_unavailable": _text_validation_unavailable,
            "total_usage": {
                "input_tokens": total_usage.input_tokens,
                "output_tokens": total_usage.output_tokens,
                "total_tokens": total_usage.total_tokens,
            },
            "text_inventory_word_count": word_count,
        }

        results[slide_num] = analysis

        # Record per-slide usage and provenance
        stage_meta.per_slide_usage[slide_num] = total_usage
        stage_meta.per_slide_providers[slide_num] = (provider_name, model)
        stage_meta.usage_total = TokenUsage(
            input_tokens=stage_meta.usage_total.input_tokens + total_usage.input_tokens,
            output_tokens=stage_meta.usage_total.output_tokens + total_usage.output_tokens,
            total_tokens=stage_meta.usage_total.total_tokens + total_usage.total_tokens,
        )

        # Cache final result with expanded dep hashes
        if cache_dir:
            entry = analysis.to_dict()
            diagram_cache.store_entry(
                final_cache, image_hash, entry,
                final_deps,
                provider_name, model,
            )
            diagram_cache.save_stage_cache(
                cache_dir, "final", final_cache,
                provider_name, model, DIAGRAM_EXTRACTION_PROMPT,
            )

        page_img.close()

    stage_meta.slide_count = len(slide_numbers or [])
    stage_meta.cache_hits = stats.hits
    stage_meta.cache_misses = stats.misses

    return results, stats, stage_meta
