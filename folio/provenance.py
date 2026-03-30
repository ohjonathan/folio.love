"""Retroactive provenance linking pipeline and CLI helpers."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from .config import FolioConfig
from .enrich import _atomic_write_text, _replace_frontmatter
from .lock import library_lock
from .output.diagram_notes import _parse_frontmatter_from_content
from .pipeline.provenance_analysis import (
    ProvenanceMatch,
    context_window_for_model,
    estimate_tokens,
    evaluate_provenance_matches,
)
from .pipeline.provenance_data import (
    ExtractedEvidenceItem,
    PROVENANCE_REVIEW_FLAG,
    PROVENANCE_SPEC_VERSION,
    compute_basis_fingerprint,
    compute_claim_hash as _claim_hash,
    compute_pair_fingerprint,
    make_link_id as _link_id,
    make_proposal_id as _proposal_id,
)
from .tracking import registry as registry_mod

logger = logging.getLogger(__name__)

PAIR_SHARD_CEILING = 8
REPAIR_RETRY_LIMIT = 3
PAGE_SIZE = 20

_SLIDE_RE = re.compile(r"^## Slide (\d+)\s*$", re.MULTILINE)
_EVIDENCE_START_RE = re.compile(r"^\*\*Evidence:\*\*\s*$")
_TOP_CLAIM_RE = re.compile(r"^\s*-\s*claim:\s*(.*?)\s*$")
_SUBFIELD_RE = re.compile(r"^\s*-\s*([a-zA-Z_]+):\s*(.*?)\s*$")
_MARKDOWN_EVIDENCE_RE = re.compile(
    r'^\s*-\s+\*\*(?P<claim>.+?)\s+\((?P<confidence_blob>[^)]*)\):\*\*\s+"(?P<quote>.*?)"\s+\*\((?P<element_type>[^)]*)\)\*(?:\s+\[unverified\])?\s*$'
)
_CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}

@dataclass
class ProvenanceProposal:
    """Machine-generated pending provenance proposal."""

    proposal_id: str
    source_claim: dict
    target_evidence: dict
    confidence: str
    rationale: str
    basis_fingerprint: str
    model: str
    timestamp_proposed: str
    status: str = "pending_human_confirmation"
    replaces_link_id: Optional[str] = None

    def to_dict(self) -> dict:
        data = {
            "proposal_id": self.proposal_id,
            "source_claim": self.source_claim,
            "target_evidence": self.target_evidence,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "basis_fingerprint": self.basis_fingerprint,
            "model": self.model,
            "timestamp_proposed": self.timestamp_proposed,
            "status": self.status,
        }
        if self.replaces_link_id:
            data["replaces_link_id"] = self.replaces_link_id
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ProvenanceProposal":
        return cls(
            proposal_id=str(data.get("proposal_id", "")),
            source_claim=dict(data.get("source_claim", {}) or {}),
            target_evidence=dict(data.get("target_evidence", {}) or {}),
            confidence=str(data.get("confidence", "medium")),
            rationale=str(data.get("rationale", "")),
            basis_fingerprint=str(data.get("basis_fingerprint", "")),
            model=str(data.get("model", "")),
            timestamp_proposed=str(data.get("timestamp_proposed", "")),
            status=str(data.get("status", "pending_human_confirmation")),
            replaces_link_id=data.get("replaces_link_id"),
        )


@dataclass
class ProvenanceRunResult:
    """Batch provenance run summary."""

    evaluated: int = 0
    proposed: int = 0
    unchanged: int = 0
    protected: int = 0
    blocked: int = 0
    failed: int = 0
    skipped: int = 0
    candidate_pairs: int = 0
    estimated_calls: int = 0
    pending_repairs: int = 0


@dataclass
class PendingProposalView:
    """Proposal row returned for review and mutation commands."""

    source_id: str
    target_id: str
    proposal: ProvenanceProposal
    md_path: Path
    title: str = ""


@dataclass
class StaleLinkView:
    """Stale-link row returned for review/status and mutation commands."""

    source_id: str
    target_id: str
    md_path: Path
    link: dict
    state: str
    orphaned: bool
    title: str = ""


@dataclass(frozen=True)
class RefreshHashesPreview:
    """Persisted-vs-current evidence snapshots shown before refresh-hashes."""

    source_before: dict
    source_after: dict
    target_before: dict
    target_after: dict


def _matches_scope(path: str, scope: str) -> bool:
    norm_scope = scope.rstrip("/") + "/"
    return path == scope or path.startswith(norm_scope)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _read_markdown(path: Path) -> tuple[str, dict | None]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return "", None
    return content, _parse_frontmatter_from_content(content)


def _ensure_registry(config: FolioConfig, *, persist: bool) -> dict:
    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    if registry_path.exists():
        data = registry_mod.load_registry(registry_path)
        if not data.get("_corrupt"):
            return data
    data = registry_mod.rebuild_registry(library_root)
    if persist:
        registry_mod.save_registry(registry_path, data)
    return data


def _get_provenance_root(fm: dict) -> dict:
    llm_meta = fm.setdefault("_llm_metadata", {})
    if not isinstance(llm_meta, dict):
        llm_meta = {}
        fm["_llm_metadata"] = llm_meta
    prov = llm_meta.get("provenance")
    if not isinstance(prov, dict):
        prov = {}
        llm_meta["provenance"] = prov
    if "pairs" not in prov or not isinstance(prov.get("pairs"), dict):
        prov["pairs"] = {}
    return prov


def _pair_meta_for_target(fm: dict, target_id: str) -> dict:
    prov = _get_provenance_root(fm)
    pairs = prov.setdefault("pairs", {})
    pair_meta = pairs.get(target_id)
    if not isinstance(pair_meta, dict):
        pair_meta = {}
        pairs[target_id] = pair_meta
    if "proposals" not in pair_meta or not isinstance(pair_meta.get("proposals"), list):
        pair_meta["proposals"] = []
    return pair_meta


def _clear_pair_repair_state(pair_meta: dict) -> None:
    pair_meta["repair_error"] = None
    pair_meta["repair_error_detail"] = None
    pair_meta["re_evaluate_requested"] = False
    pair_meta.pop("repair_attempts", None)


def _clear_acknowledgement_fields(link: dict) -> None:
    link.pop("acknowledged_at_claim_hash", None)
    link.pop("acknowledged_at_target_hash", None)


def _evidence_snapshot(*, slide_number: int, claim_index: int, claim_text: str, supporting_quote: str) -> dict:
    return {
        "slide_number": slide_number,
        "claim_index": claim_index,
        "claim_text": claim_text,
        "supporting_quote": supporting_quote,
    }


def _pair_stale_counts(stale_views: list[StaleLinkView], *, target_id: str | None = None) -> dict[str, int]:
    counts = {
        "stale": 0,
        "acknowledged": 0,
        "re_evaluate_pending": 0,
        "repair_blocked": 0,
        "orphaned": 0,
    }
    for view in stale_views:
        if target_id and view.target_id != target_id:
            continue
        if view.orphaned:
            counts["orphaned"] += 1
        if view.state in counts:
            counts[view.state] += 1
    return counts


def _repair_attempt_count(pair_meta: dict) -> int:
    raw = pair_meta.get("repair_attempts", 0)
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def _repair_link_ids(repair_links: list[dict]) -> set[str]:
    return {
        str(link.get("link_id", ""))
        for link in repair_links
        if isinstance(link, dict) and link.get("link_id")
    }


def _has_pending_repair_proposals(pair_meta: dict, repair_links: list[dict]) -> bool:
    repair_ids = _repair_link_ids(repair_links)
    if not repair_ids:
        return False
    for raw in pair_meta.get("proposals", []) or []:
        if not isinstance(raw, dict):
            continue
        if raw.get("status") != "pending_human_confirmation":
            continue
        if str(raw.get("replaces_link_id", "")) in repair_ids:
            return True
    return False


def extract_evidence_items(content: str) -> list[ExtractedEvidenceItem]:
    """Extract structured `**Evidence:**` entries from an evidence note."""
    if not content:
        return []
    items: list[ExtractedEvidenceItem] = []
    slide_matches = list(_SLIDE_RE.finditer(content))
    for index, match in enumerate(slide_matches):
        slide_number = int(match.group(1))
        section_start = match.end()
        section_end = slide_matches[index + 1].start() if index + 1 < len(slide_matches) else len(content)
        section_text = content[section_start:section_end]
        items.extend(_extract_items_from_slide(section_text, slide_number))
    return items


def _extract_items_from_slide(section_text: str, slide_number: int) -> list[ExtractedEvidenceItem]:
    lines = section_text.splitlines()
    in_block = False
    current: dict | None = None
    parsed: list[dict] = []

    def finalize_current() -> None:
        nonlocal current
        if not current:
            return
        claim_text = str(current.get("claim", "")).strip()
        if not claim_text:
            current = None
            return
        parsed.append(current)
        current = None

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if not in_block:
            if _EVIDENCE_START_RE.match(stripped):
                in_block = True
            continue
        if not stripped:
            continue
        markdown_match = _MARKDOWN_EVIDENCE_RE.match(line)
        if markdown_match:
            finalize_current()
            confidence_blob = markdown_match.group("confidence_blob").strip()
            confidence = confidence_blob.split(",", 1)[0].strip()
            parsed.append(
                {
                    "claim": markdown_match.group("claim").strip(),
                    "quote": markdown_match.group("quote").strip(),
                    "confidence": confidence,
                    "element_type": markdown_match.group("element_type").strip(),
                }
            )
            continue
        top_match = _TOP_CLAIM_RE.match(line)
        if top_match:
            finalize_current()
            current = {"claim": top_match.group(1).strip()}
            continue
        field_match = _SUBFIELD_RE.match(line)
        if field_match and current is not None:
            key = field_match.group(1).strip().lower()
            value = field_match.group(2).strip().strip('"')
            current[key] = value
            continue
        if stripped.startswith("---") or stripped.startswith("## ") or stripped.startswith("# "):
            break

    finalize_current()

    items: list[ExtractedEvidenceItem] = []
    for claim_index, item in enumerate(parsed):
        claim_text = str(item.get("claim", "")).strip()
        supporting_quote = str(item.get("quote", "")).strip()
        evidence_item = ExtractedEvidenceItem(
            slide_number=slide_number,
            claim_index=claim_index,
            claim_text=claim_text,
            supporting_quote=supporting_quote,
            original_confidence=str(item.get("confidence", "")).strip(),
            element_type=str(item.get("element_type", "")).strip(),
            claim_hash=_claim_hash(claim_text, supporting_quote),
        )
        items.append(evidence_item)
    return items


def _find_item(
    items: list[ExtractedEvidenceItem],
    slide_number: int,
    claim_index: int,
) -> ExtractedEvidenceItem | None:
    for item in items:
        if item.slide_number == slide_number and item.claim_index == claim_index:
            return item
    return None


def _pair_fingerprint(
    source_items: list[ExtractedEvidenceItem],
    target_items: list[ExtractedEvidenceItem],
    profile_name: str,
) -> str:
    return compute_pair_fingerprint(
        source_items,
        target_items,
        profile_name,
        spec_version=PROVENANCE_SPEC_VERSION,
    )


def _basis_fingerprint(source_item: ExtractedEvidenceItem, target_item: ExtractedEvidenceItem, profile_name: str) -> str:
    return compute_basis_fingerprint(
        source_item.claim_hash,
        target_item.claim_hash,
        profile_name,
    )


def _serialize_link(
    *,
    source_id: str,
    target_id: str,
    source_item: ExtractedEvidenceItem,
    target_item: ExtractedEvidenceItem,
    confidence: str,
    replaces_link_id: str | None,
) -> dict:
    link_id = _link_id(
        source_id,
        source_item.slide_number,
        source_item.claim_index,
        target_id,
        target_item.slide_number,
        target_item.claim_index,
    )
    link = {
        "link_id": link_id,
        "source_slide": source_item.slide_number,
        "source_claim_index": source_item.claim_index,
        "source_claim_hash": source_item.claim_hash,
        "source_claim_text_snapshot": source_item.claim_text,
        "source_supporting_quote_snapshot": source_item.supporting_quote,
        "target_doc": target_id,
        "target_slide": target_item.slide_number,
        "target_claim_index": target_item.claim_index,
        "target_claim_hash": target_item.claim_hash,
        "target_claim_text_snapshot": target_item.claim_text,
        "target_supporting_quote_snapshot": target_item.supporting_quote,
        "confidence": confidence,
        "confirmed_at": _utc_now(),
        "link_status": "confirmed",
    }
    if replaces_link_id:
        link["replaces_link_id"] = replaces_link_id
    return link


def _review_flags_with_provenance(fm: dict, has_stale_signal: bool) -> list[str]:
    review_flags = list(fm.get("review_flags", []) or [])
    review_flags = [flag for flag in review_flags if flag != PROVENANCE_REVIEW_FLAG]
    if has_stale_signal:
        review_flags.append(PROVENANCE_REVIEW_FLAG)
    return review_flags


def _surface_link_state(
    link: dict,
    source_items: list[ExtractedEvidenceItem],
    target_items: list[ExtractedEvidenceItem],
    pair_meta: dict,
) -> tuple[str, bool]:
    source_item = _find_item(
        source_items,
        int(link.get("source_slide", -1)),
        int(link.get("source_claim_index", -1)),
    )
    target_item = _find_item(
        target_items,
        int(link.get("target_slide", -1)),
        int(link.get("target_claim_index", -1)),
    )
    orphaned = source_item is None or target_item is None
    status = str(link.get("link_status", "confirmed"))
    if status == "re_evaluate_pending":
        return ("repair_blocked" if pair_meta.get("repair_error") else "re_evaluate_pending", orphaned)
    if source_item is None or target_item is None:
        return ("stale", True)

    source_hash_match = source_item.claim_hash == link.get("source_claim_hash")
    target_hash_match = target_item.claim_hash == link.get("target_claim_hash")
    if status == "acknowledged_stale":
        ack_source = link.get("acknowledged_at_claim_hash")
        ack_target = link.get("acknowledged_at_target_hash")
        if source_item.claim_hash == ack_source and target_item.claim_hash == ack_target:
            return ("acknowledged", False)
        return ("stale", orphaned)
    if status == "confirmed" and source_hash_match and target_hash_match:
        return ("fresh", False)
    return ("stale", orphaned)


def _dedupe_against_confirmed(
    proposals: list[ProvenanceProposal],
    links: list[dict],
    source_items: list[ExtractedEvidenceItem],
    target_items: list[ExtractedEvidenceItem],
    pair_meta: dict,
) -> list[ProvenanceProposal]:
    result: list[ProvenanceProposal] = []
    for proposal in proposals:
        suppressed = False
        for link in links:
            if int(link.get("source_slide", -1)) != int(proposal.source_claim.get("slide_number", -1)):
                continue
            if int(link.get("source_claim_index", -1)) != int(proposal.source_claim.get("claim_index", -1)):
                continue
            if str(link.get("target_doc")) != str(proposal.target_evidence.get("target_doc")):
                continue
            if int(link.get("target_slide", -1)) != int(proposal.target_evidence.get("slide_number", -1)):
                continue
            if int(link.get("target_claim_index", -1)) != int(proposal.target_evidence.get("claim_index", -1)):
                continue
            state, _ = _surface_link_state(link, source_items, target_items, pair_meta)
            if state in {"fresh", "acknowledged"}:
                suppressed = True
                break
        if not suppressed:
            result.append(proposal)
    return result


def _suppress_rejections(
    proposals: list[ProvenanceProposal],
    pair_meta: dict,
    *,
    clear_rejections: bool,
) -> list[ProvenanceProposal]:
    if clear_rejections:
        return proposals
    rejected: dict[tuple[int, int, int, int], str] = {}
    for raw in pair_meta.get("proposals", []) or []:
        if not isinstance(raw, dict) or raw.get("status") != "rejected":
            continue
        source_claim = raw.get("source_claim", {}) or {}
        target_evidence = raw.get("target_evidence", {}) or {}
        key = (
            int(source_claim.get("slide_number", -1)),
            int(source_claim.get("claim_index", -1)),
            int(target_evidence.get("slide_number", -1)),
            int(target_evidence.get("claim_index", -1)),
        )
        rejected[key] = str(raw.get("basis_fingerprint", ""))

    kept: list[ProvenanceProposal] = []
    for proposal in proposals:
        key = (
            int(proposal.source_claim.get("slide_number", -1)),
            int(proposal.source_claim.get("claim_index", -1)),
            int(proposal.target_evidence.get("slide_number", -1)),
            int(proposal.target_evidence.get("claim_index", -1)),
        )
        existing_basis = rejected.get(key)
        if existing_basis and existing_basis == proposal.basis_fingerprint:
            continue
        kept.append(proposal)
    return kept


def _build_shards(
    source_items: list[ExtractedEvidenceItem],
    target_items: list[ExtractedEvidenceItem],
    context_budget: int,
) -> tuple[list[tuple[list[ExtractedEvidenceItem], list[ExtractedEvidenceItem]]], list[str]]:
    warnings: list[str] = []
    overhead = 2_000
    effective_budget = max(1_000, context_budget - overhead)

    def item_tokens(item: ExtractedEvidenceItem) -> int:
        return estimate_tokens(
            json.dumps(
                {
                    "claim_text": item.claim_text,
                    "supporting_quote": item.supporting_quote,
                    "slide_number": item.slide_number,
                    "claim_index": item.claim_index,
                },
                ensure_ascii=False,
            )
        )

    def truncate_item(item: ExtractedEvidenceItem, budget: int, kind: str) -> ExtractedEvidenceItem:
        token_count = item_tokens(item)
        if token_count <= budget:
            return item
        trimmed = item.supporting_quote
        while trimmed and item_tokens(
            ExtractedEvidenceItem(
                slide_number=item.slide_number,
                claim_index=item.claim_index,
                claim_text=item.claim_text,
                supporting_quote=trimmed,
                original_confidence=item.original_confidence,
                element_type=item.element_type,
                claim_hash=item.claim_hash,
            )
        ) > budget:
            trimmed = trimmed[:- max(1, len(trimmed) // 10)]
        if trimmed != item.supporting_quote:
            warnings.append(
                f"{kind} quote truncated: slide {item.slide_number}, claim {item.claim_index}"
            )
        updated = ExtractedEvidenceItem(
            slide_number=item.slide_number,
            claim_index=item.claim_index,
            claim_text=item.claim_text,
            supporting_quote=trimmed,
            original_confidence=item.original_confidence,
            element_type=item.element_type,
            claim_hash=item.claim_hash,
        )
        return updated

    source_items = [truncate_item(item, effective_budget, "source claim") for item in source_items]
    target_items = [truncate_item(item, effective_budget, "target evidence") for item in target_items]

    total_source = sum(item_tokens(item) for item in source_items)
    total_target = sum(item_tokens(item) for item in target_items)
    if total_source + total_target <= effective_budget:
        return [(
            sorted(source_items, key=lambda i: (i.slide_number, i.claim_index)),
            sorted(target_items, key=lambda i: (i.slide_number, i.claim_index)),
        )], warnings

    source_chunks: list[list[ExtractedEvidenceItem]] = []
    if total_source <= effective_budget:
        source_chunks = [sorted(source_items, key=lambda i: (i.slide_number, i.claim_index))]
    else:
        current: list[ExtractedEvidenceItem] = []
        current_tokens = 0
        for item in sorted(source_items, key=lambda i: (i.slide_number, i.claim_index)):
            tokens = item_tokens(item)
            if current and current_tokens + tokens > effective_budget:
                source_chunks.append(current)
                current = []
                current_tokens = 0
            current.append(item)
            current_tokens += tokens
        if current:
            source_chunks.append(current)

    shards: list[tuple[list[ExtractedEvidenceItem], list[ExtractedEvidenceItem]]] = []
    for claim_chunk in source_chunks:
        claim_tokens = sum(item_tokens(item) for item in claim_chunk)
        remaining = max(1_000, effective_budget - claim_tokens)
        current_targets: list[ExtractedEvidenceItem] = []
        current_tokens = 0
        for item in sorted(target_items, key=lambda i: (i.slide_number, i.claim_index)):
            tokens = item_tokens(item)
            if current_targets and current_tokens + tokens > remaining:
                shards.append((claim_chunk, current_targets))
                current_targets = []
                current_tokens = 0
            current_targets.append(item)
            current_tokens += tokens
        if current_targets:
            shards.append((claim_chunk, current_targets))
    return shards, warnings


def _build_prompt_payload(items: list[ExtractedEvidenceItem], prefix: str, *, target_doc: str | None = None) -> tuple[list[dict], dict[str, ExtractedEvidenceItem]]:
    payload: list[dict] = []
    lookup: dict[str, ExtractedEvidenceItem] = {}
    for index, item in enumerate(items, 1):
        ref = f"{prefix}{index}"
        row = item.to_prompt_dict(ref)
        if target_doc:
            row["target_doc"] = target_doc
        payload.append(row)
        lookup[ref] = item
    return payload, lookup


def _repair_links_for_target(fm: dict, target_id: str) -> list[dict]:
    links = list(fm.get("provenance_links", []) or [])
    return [
        link for link in links
        if isinstance(link, dict)
        and link.get("target_doc") == target_id
        and link.get("link_status") == "re_evaluate_pending"
    ]


def _serialize_proposals(
    *,
    source_id: str,
    target_id: str,
    matches: list[ProvenanceMatch],
    claims_lookup: dict[str, ExtractedEvidenceItem],
    target_lookup: dict[str, ExtractedEvidenceItem],
    profile_name: str,
    provider_name: str,
    model: str,
    repair_links: list[dict],
) -> list[ProvenanceProposal]:
    proposals: list[ProvenanceProposal] = []
    timestamp = _utc_now()
    repair_map_exact = {
        (
            int(link.get("source_slide", -1)),
            int(link.get("source_claim_index", -1)),
            int(link.get("target_slide", -1)),
            int(link.get("target_claim_index", -1)),
        ): str(link.get("link_id", ""))
        for link in repair_links
        if isinstance(link, dict) and link.get("link_id")
    }
    repair_map_by_source: dict[tuple[int, int], list[str]] = {}
    for link in repair_links:
        if not isinstance(link, dict) or not link.get("link_id"):
            continue
        key = (
            int(link.get("source_slide", -1)),
            int(link.get("source_claim_index", -1)),
        )
        repair_map_by_source.setdefault(key, []).append(str(link.get("link_id", "")))
    for match in matches:
        source_item = claims_lookup.get(match.claim_ref)
        target_item = target_lookup.get(match.target_ref)
        if source_item is None or target_item is None:
            continue
        exact_key = (
            source_item.slide_number,
            source_item.claim_index,
            target_item.slide_number,
            target_item.claim_index,
        )
        replaces_link_id = repair_map_exact.get(exact_key)
        if replaces_link_id is None:
            same_source_repairs = repair_map_by_source.get(
                (source_item.slide_number, source_item.claim_index),
                [],
            )
            if len(same_source_repairs) == 1:
                replaces_link_id = same_source_repairs[0]
        proposal = ProvenanceProposal(
            proposal_id=_proposal_id(
                source_id,
                source_item.slide_number,
                source_item.claim_index,
                target_id,
                target_item.slide_number,
                target_item.claim_index,
            ),
            source_claim={
                "slide_number": source_item.slide_number,
                "claim_index": source_item.claim_index,
                "claim_text": source_item.claim_text,
                "claim_hash": source_item.claim_hash,
                "supporting_quote": source_item.supporting_quote,
            },
            target_evidence={
                "target_doc": target_id,
                "slide_number": target_item.slide_number,
                "claim_index": target_item.claim_index,
                "claim_text": target_item.claim_text,
                "supporting_quote": target_item.supporting_quote,
                "claim_hash": target_item.claim_hash,
            },
            confidence=match.confidence,
            rationale=match.rationale,
            basis_fingerprint=_basis_fingerprint(source_item, target_item, profile_name),
            model=f"{provider_name}/{model}",
            timestamp_proposed=timestamp,
            replaces_link_id=replaces_link_id or None,
        )
        proposals.append(proposal)
    return proposals


def _merge_shard_matches(existing: dict[tuple[int, int, int, int], ProvenanceProposal], proposals: list[ProvenanceProposal]) -> None:
    for proposal in proposals:
        key = (
            int(proposal.source_claim.get("slide_number", -1)),
            int(proposal.source_claim.get("claim_index", -1)),
            int(proposal.target_evidence.get("slide_number", -1)),
            int(proposal.target_evidence.get("claim_index", -1)),
        )
        current = existing.get(key)
        if current is None or _CONFIDENCE_RANK.get(proposal.confidence, 99) < _CONFIDENCE_RANK.get(current.confidence, 99):
            existing[key] = proposal


def _proposals_for_pair(pair_meta: dict) -> list[ProvenanceProposal]:
    proposals: list[ProvenanceProposal] = []
    for raw in pair_meta.get("proposals", []) or []:
        if isinstance(raw, dict):
            proposals.append(ProvenanceProposal.from_dict(raw))
    return proposals


def _upsert_provenance_root(
    *,
    fm: dict,
    requested_profile: str,
    profile_name: str,
    provider_name: str,
    model: str,
) -> dict:
    prov = _get_provenance_root(fm)
    prov["requested_profile"] = requested_profile
    prov["profile"] = profile_name
    prov["provider"] = provider_name
    prov["model"] = model
    prov["provenance_spec_version"] = PROVENANCE_SPEC_VERSION
    return prov


def _write_provenance_note_locked(
    config: FolioConfig,
    *,
    md_path: Path,
    mutate: Callable[[str, dict, dict, Path], None],
    expected_source_hash: str | None = None,
    target_path: Path | None = None,
    expected_target_hash: str | None = None,
) -> bool:
    """Write one source note under the library lock, optionally validating inputs."""
    library_root = config.library_root.resolve()
    with library_lock(library_root, "provenance"):
        current_content, current_fm = _read_markdown(md_path)
        if current_fm is None:
            raise ValueError(f"Cannot read frontmatter from {md_path}")
        if expected_source_hash is not None and _content_hash(current_content) != expected_source_hash:
            return False
        if target_path is not None and expected_target_hash is not None:
            target_content, target_fm = _read_markdown(target_path)
            if target_fm is None or _content_hash(target_content) != expected_target_hash:
                return False
        reg_data = _ensure_registry(config, persist=False)
        mutate(current_content, current_fm, reg_data, library_root)
        _write_frontmatter_only(md_path, current_content, current_fm)
        return True


def provenance_batch(
    config: FolioConfig,
    *,
    scope: str | None = None,
    dry_run: bool = False,
    llm_profile: str | None = None,
    force: bool = False,
    clear_rejections: bool = False,
    limit: int | None = None,
    echo: Optional[Callable[[str], None]] = None,
) -> ProvenanceRunResult:
    """Run the PR D provenance pipeline over evidence notes in scope."""
    if clear_rejections and not force:
        raise ValueError("--clear-rejections requires --force")

    echo = echo or (lambda _msg: None)
    library_root = config.library_root.resolve()
    reg_data = _ensure_registry(config, persist=False)
    profile = config.llm.resolve_profile(llm_profile, task="provenance")
    fallbacks = config.llm.get_fallbacks(llm_profile, task="provenance")
    provider_settings = getattr(config, "providers", {}) or {}

    entries = []
    for deck_id in sorted(reg_data.get("decks", {})):
        entry_data = reg_data["decks"][deck_id]
        entry = registry_mod.entry_from_dict(entry_data)
        if entry.type != "evidence":
            continue
        if scope and not (
            _matches_scope(entry.deck_dir, scope)
            or _matches_scope(entry.markdown_path, scope)
            or entry.id == scope
        ):
            continue
        entries.append(entry)

    result = ProvenanceRunResult()
    planned_lines: list[str] = []
    evaluations_done = 0

    for entry in entries:
        md_path = library_root / entry.markdown_path
        content, fm = _read_markdown(md_path)
        if fm is None:
            continue
        source_content_hash = _content_hash(content)
        target_id = fm.get("supersedes")
        prov = _get_provenance_root(fm)
        links = [link for link in fm.get("provenance_links", []) or [] if isinstance(link, dict)]
        if not isinstance(target_id, str) or not target_id:
            if links or prov.get("pairs"):
                result.candidate_pairs += 1
            continue

        pair_meta = _pair_meta_for_target(fm, target_id)
        repair_links = _repair_links_for_target(fm, target_id)
        pending_repairs = len(repair_links)
        if pending_repairs:
            result.pending_repairs += pending_repairs
        stale_pair_request = bool(pair_meta.get("re_evaluate_requested")) and not repair_links
        if stale_pair_request:
            pair_meta["re_evaluate_requested"] = False
            pair_meta["repair_error"] = None
            pair_meta["repair_error_detail"] = None
            pair_meta.pop("repair_attempts", None)

        target_entry_data = reg_data.get("decks", {}).get(target_id)
        target_entry = registry_mod.entry_from_dict(target_entry_data) if isinstance(target_entry_data, dict) else None
        source_items = extract_evidence_items(content)
        stale_views = _collect_stale_links_for_note(entry, fm, reg_data, library_root)
        stale_counts = _pair_stale_counts(stale_views, target_id=target_id)
        target_path: Path | None = None
        target_content_hash: str | None = None

        disposition = "evaluate"
        reason = ""
        target_items: list[ExtractedEvidenceItem] = []
        blocked_reason = None
        protection_reason = ""
        if fm.get("curation_level", "L0") != "L0":
            protection_reason = f"curation_level={fm.get('curation_level', 'L0')}"
        elif fm.get("review_status") in {"reviewed", "overridden"}:
            protection_reason = f"review_status={fm.get('review_status')}"
        if protection_reason:
            if not (repair_links or pair_meta.get("re_evaluate_requested")):
                disposition = "protected"
                reason = protection_reason
        if target_entry is None:
            disposition = "blocked" if (repair_links or pair_meta.get("re_evaluate_requested")) else "skip"
            blocked_reason = "target_missing"
            reason = "target missing"
        elif target_entry.type != "evidence":
            disposition = "blocked" if (repair_links or pair_meta.get("re_evaluate_requested")) else "skip"
            blocked_reason = "target_ineligible"
            reason = "target ineligible"
        else:
            target_path = library_root / target_entry.markdown_path
            target_content, target_fm = _read_markdown(target_path)
            if target_fm is None:
                disposition = "blocked" if (repair_links or pair_meta.get("re_evaluate_requested")) else "skip"
                blocked_reason = "frontmatter_unreadable"
                reason = "target unreadable"
            else:
                target_content_hash = _content_hash(target_content)
                target_items = extract_evidence_items(target_content)
                if not target_items:
                    disposition = "blocked" if (repair_links or pair_meta.get("re_evaluate_requested")) else "skip"
                    blocked_reason = "target_ineligible"
                    reason = "target has no evidence"

        result.candidate_pairs += 1
        if disposition in {"skip", "protected", "blocked"}:
            preview_bits: list[str] = []
            if stale_counts["stale"]:
                preview_bits.append(f"stale={stale_counts['stale']}")
            if stale_counts["acknowledged"]:
                preview_bits.append(f"ack={stale_counts['acknowledged']}")
            if stale_counts["re_evaluate_pending"]:
                preview_bits.append(f"re-eval={stale_counts['re_evaluate_pending']}")
            if stale_counts["repair_blocked"]:
                preview_bits.append(f"blocked={stale_counts['repair_blocked']}")
            if stale_counts["orphaned"]:
                preview_bits.append(f"orphaned={stale_counts['orphaned']}")
            preview_suffix = f"  [{', '.join(preview_bits)}]" if preview_bits else ""
            if disposition == "protected":
                result.protected += 1
                planned_lines.append(f"! {entry.id}                                         protected [{reason}]{preview_suffix}")
            elif disposition == "blocked":
                result.blocked += 1
                planned_lines.append(f"! {entry.id} → {target_id}                              repair blocked [{blocked_reason}]{preview_suffix}")
                if not dry_run and blocked_reason:
                    def persist_blocked(
                        _current_content: str,
                        current_fm: dict,
                        current_reg_data: dict,
                        current_library_root: Path,
                    ) -> None:
                        current_pair_meta = _pair_meta_for_target(current_fm, target_id)
                        current_pair_meta["repair_error"] = blocked_reason
                        current_pair_meta["repair_error_detail"] = reason
                        current_pair_meta["status"] = "error"
                        current_pair_meta["timestamp"] = _utc_now()
                        current_entry = registry_mod.entry_from_dict(current_reg_data["decks"][entry.id])
                        _apply_review_flag_updates(
                            current_fm,
                            current_entry,
                            current_reg_data,
                            current_library_root,
                        )

                    _write_provenance_note_locked(
                        config,
                        md_path=md_path,
                        mutate=persist_blocked,
                    )
            else:
                result.skipped += 1
                planned_lines.append(f"↷ {entry.id} → {target_id}                              skipped [{reason}]{preview_suffix}")
                if not dry_run and stale_pair_request:
                    def persist_stale_pair_cleanup(
                        _current_content: str,
                        current_fm: dict,
                        _current_reg_data: dict,
                        _current_library_root: Path,
                    ) -> None:
                        current_pair_meta = _pair_meta_for_target(current_fm, target_id)
                        current_pair_meta["re_evaluate_requested"] = False
                        current_pair_meta["repair_error"] = None
                        current_pair_meta["repair_error_detail"] = None
                        current_pair_meta.pop("repair_attempts", None)

                    _write_provenance_note_locked(
                        config,
                        md_path=md_path,
                        mutate=persist_stale_pair_cleanup,
                    )
            continue

        current_pair_fp = _pair_fingerprint(source_items, target_items, profile.name)
        queued_repair = bool(repair_links or pair_meta.get("re_evaluate_requested"))
        protected_repair_override = protection_reason if protection_reason and queued_repair else ""
        pair_meta.setdefault("proposals", [])
        if clear_rejections and pair_meta.get("proposals"):
            pair_meta["proposals"] = [
                raw for raw in pair_meta["proposals"]
                if not isinstance(raw, dict) or raw.get("status") != "rejected"
            ]
        if _has_pending_repair_proposals(pair_meta, repair_links):
            result.skipped += 1
            planned_lines.append(
                f"↷ {entry.id} → {target_id}                              repair proposal pending review"
            )
            continue
        repair_attempts = _repair_attempt_count(pair_meta)
        if repair_links and repair_attempts >= REPAIR_RETRY_LIMIT:
            result.blocked += 1
            planned_lines.append(
                f"! {entry.id} → {target_id}                              repair blocked [repair_retry_limit_exceeded: {repair_attempts}]"
            )
            if not dry_run:
                def persist_retry_limit(
                    _current_content: str,
                    current_fm: dict,
                    current_reg_data: dict,
                    current_library_root: Path,
                ) -> None:
                    current_pair_meta = _pair_meta_for_target(current_fm, target_id)
                    current_pair_meta["repair_error"] = "repair_retry_limit_exceeded"
                    current_pair_meta["repair_error_detail"] = (
                        f"{repair_attempts} unsuccessful re-evaluate attempt(s)"
                    )
                    current_pair_meta["status"] = "error"
                    current_pair_meta["timestamp"] = _utc_now()
                    current_entry = registry_mod.entry_from_dict(current_reg_data["decks"][entry.id])
                    _apply_review_flag_updates(
                        current_fm,
                        current_entry,
                        current_reg_data,
                        current_library_root,
                    )

                _write_provenance_note_locked(
                    config,
                    md_path=md_path,
                    mutate=persist_retry_limit,
                )
            continue
        if not force and not queued_repair and pair_meta.get("pair_fingerprint") == current_pair_fp:
            result.unchanged += 1
            planned_lines.append(f"~ {entry.id} → {target_id}                              unchanged")
            if not dry_run and stale_pair_request:
                def persist_stale_pair_cleanup_on_unchanged(
                    _current_content: str,
                    current_fm: dict,
                    _current_reg_data: dict,
                    _current_library_root: Path,
                ) -> None:
                    current_pair_meta = _pair_meta_for_target(current_fm, target_id)
                    current_pair_meta["re_evaluate_requested"] = False
                    current_pair_meta["repair_error"] = None
                    current_pair_meta["repair_error_detail"] = None
                    current_pair_meta.pop("repair_attempts", None)

                _write_provenance_note_locked(
                    config,
                    md_path=md_path,
                    mutate=persist_stale_pair_cleanup_on_unchanged,
                )
            continue

        shard_budget = int(context_window_for_model(profile.model) * 0.80)
        shards, shard_warnings = _build_shards(source_items, target_items, shard_budget)
        if len(shards) > PAIR_SHARD_CEILING:
            result.blocked += 1
            planned_lines.append(
                f"! {entry.id} → {target_id}                              repair blocked [shard_ceiling_exceeded: {len(shards)} > {PAIR_SHARD_CEILING}]"
            )
            if not dry_run:
                def persist_ceiling(
                    _current_content: str,
                    current_fm: dict,
                    current_reg_data: dict,
                    current_library_root: Path,
                ) -> None:
                    current_pair_meta = _pair_meta_for_target(current_fm, target_id)
                    current_pair_meta["repair_error"] = "shard_ceiling_exceeded"
                    current_pair_meta["repair_error_detail"] = f"{len(shards)} > {PAIR_SHARD_CEILING}"
                    current_pair_meta["status"] = "error"
                    current_pair_meta["timestamp"] = _utc_now()
                    current_entry = registry_mod.entry_from_dict(current_reg_data["decks"][entry.id])
                    _apply_review_flag_updates(
                        current_fm,
                        current_entry,
                        current_reg_data,
                        current_library_root,
                    )

                _write_provenance_note_locked(
                    config,
                    md_path=md_path,
                    mutate=persist_ceiling,
                )
            continue

        if limit is not None and evaluations_done >= limit:
            break

        result.estimated_calls += len(shards)
        evaluations_done += 1

        if dry_run:
            preview_bits: list[str] = []
            if stale_counts["stale"]:
                preview_bits.append(f"stale={stale_counts['stale']}")
            if stale_counts["acknowledged"]:
                preview_bits.append(f"ack={stale_counts['acknowledged']}")
            if stale_counts["re_evaluate_pending"]:
                preview_bits.append(f"re-eval={stale_counts['re_evaluate_pending']}")
            if stale_counts["repair_blocked"]:
                preview_bits.append(f"blocked={stale_counts['repair_blocked']}")
            if stale_counts["orphaned"]:
                preview_bits.append(f"orphaned={stale_counts['orphaned']}")
            if pending_repairs:
                preview_bits.append(f"queued_repair={pending_repairs}")
            if protected_repair_override:
                preview_bits.append(f"would trigger LLM on protected note [{protected_repair_override}]")
            preview_suffix = f"  [{', '.join(preview_bits)}]" if preview_bits else ""
            planned_lines.append(
                f"+ {entry.id} → {target_id}                              {len(source_items)} claims, {len(shards)} planned call(s){preview_suffix}"
            )
            for warning in shard_warnings:
                planned_lines.append(f"  ⚠ {warning}")
            continue

        aggregate: dict[tuple[int, int, int, int], ProvenanceProposal] = {}
        llm_error = None
        for claim_chunk, target_chunk in shards:
            claims_payload, claim_lookup = _build_prompt_payload(claim_chunk, "C")
            target_payload, target_lookup = _build_prompt_payload(target_chunk, "T", target_doc=target_id)
            try:
                matches = evaluate_provenance_matches(
                    source_note_id=entry.id,
                    target_note_id=target_id,
                    claims_payload=claims_payload,
                    target_payload=target_payload,
                    provider_name=profile.provider,
                    model=profile.model,
                    api_key_env=profile.api_key_env,
                    base_url_env=profile.base_url_env,
                    fallback_profiles=fallbacks,
                    all_provider_settings=provider_settings,
                )
            except Exception as exc:
                llm_error = str(exc)
                break
            shard_proposals = _serialize_proposals(
                source_id=entry.id,
                target_id=target_id,
                matches=matches,
                claims_lookup=claim_lookup,
                target_lookup=target_lookup,
                profile_name=profile.name,
                provider_name=profile.provider,
                model=profile.model,
                repair_links=repair_links,
            )
            _merge_shard_matches(aggregate, shard_proposals)

        if llm_error:
            def persist_llm_error(
                _current_content: str,
                current_fm: dict,
                current_reg_data: dict,
                current_library_root: Path,
            ) -> None:
                current_pair_meta = _pair_meta_for_target(current_fm, target_id)
                current_pair_meta["repair_error"] = "llm_error"
                current_pair_meta["repair_error_detail"] = llm_error
                current_pair_meta["status"] = "error"
                current_pair_meta["timestamp"] = _utc_now()
                current_entry = registry_mod.entry_from_dict(current_reg_data["decks"][entry.id])
                _apply_review_flag_updates(
                    current_fm,
                    current_entry,
                    current_reg_data,
                    current_library_root,
                )

            wrote_error = _write_provenance_note_locked(
                config,
                md_path=md_path,
                mutate=persist_llm_error,
                expected_source_hash=source_content_hash,
                target_path=target_path,
                expected_target_hash=target_content_hash,
            )
            if not wrote_error:
                result.skipped += 1
                planned_lines.append(
                    f"? {entry.id} → {target_id}                              changed during evaluation; rerun"
                )
                continue
            result.failed += 1
            planned_lines.append(f"x {entry.id} → {target_id}                              <error: {llm_error}>")
            continue

        proposals = list(aggregate.values())
        proposals = _dedupe_against_confirmed(proposals, links, source_items, target_items, pair_meta)
        proposals = _suppress_rejections(
            proposals,
            pair_meta,
            clear_rejections=clear_rejections,
        )
        sorted_proposals = sorted(
            proposals,
            key=lambda p: (
                int(p.source_claim.get("slide_number", -1)),
                int(p.source_claim.get("claim_index", -1)),
                _CONFIDENCE_RANK.get(p.confidence, 99),
                p.proposal_id,
            ),
        )
        proposal_payload = [proposal.to_dict() for proposal in sorted_proposals]

        def persist_proposals(
            _current_content: str,
            current_fm: dict,
            current_reg_data: dict,
            current_library_root: Path,
        ) -> None:
            current_pair_meta = _pair_meta_for_target(current_fm, target_id)
            prior_repair_attempts = _repair_attempt_count(current_pair_meta)
            if clear_rejections and current_pair_meta.get("proposals"):
                current_pair_meta["proposals"] = [
                    raw for raw in current_pair_meta["proposals"]
                    if not isinstance(raw, dict) or raw.get("status") != "rejected"
                ]
            existing_rejected = [
                raw for raw in current_pair_meta.get("proposals", [])
                if isinstance(raw, dict) and raw.get("status") == "rejected"
            ]
            current_pair_meta["proposals"] = existing_rejected + proposal_payload
            current_pair_meta["pair_fingerprint"] = current_pair_fp
            current_pair_meta["status"] = "proposed" if proposal_payload else "no_change"
            current_pair_meta["timestamp"] = _utc_now()
            _clear_pair_repair_state(current_pair_meta)
            if repair_links and not proposal_payload:
                current_pair_meta["repair_attempts"] = prior_repair_attempts + 1
            else:
                current_pair_meta.pop("repair_attempts", None)
            _upsert_provenance_root(
                fm=current_fm,
                requested_profile=llm_profile or profile.name,
                profile_name=profile.name,
                provider_name=profile.provider,
                model=profile.model,
            )
            current_entry = registry_mod.entry_from_dict(current_reg_data["decks"][entry.id])
            _apply_review_flag_updates(
                current_fm,
                current_entry,
                current_reg_data,
                current_library_root,
            )

        wrote_proposals = _write_provenance_note_locked(
            config,
            md_path=md_path,
            mutate=persist_proposals,
            expected_source_hash=source_content_hash,
            target_path=target_path,
            expected_target_hash=target_content_hash,
        )
        if not wrote_proposals:
            result.skipped += 1
            planned_lines.append(
                f"? {entry.id} → {target_id}                              changed during evaluation; rerun"
            )
            continue

        if proposals:
            result.evaluated += 1
            result.proposed += len(proposals)
            planned_lines.append(
                f"+ {entry.id} → {target_id}                              {len(source_items)} claims, {len(proposals)} proposed link(s)"
            )
        else:
            result.unchanged += 1
            planned_lines.append(f"~ {entry.id} → {target_id}                              unchanged")
        for warning in shard_warnings:
            planned_lines.append(f"  ⚠ {warning}")

    if entries:
        echo(
            f"Scope: {len(entries)} source document(s), {result.candidate_pairs} candidate pair(s) [supersedes: {result.candidate_pairs}]"
        )
        echo(f"Estimated calls: {result.estimated_calls}")
        if result.pending_repairs:
            echo(f"Queued repair links: {result.pending_repairs}")
        echo("")
    for line in planned_lines:
        echo(line)
    if not dry_run:
        echo("")
        echo(
            "Provenance complete: "
            f"{result.evaluated} evaluated, {result.proposed} proposed, "
            f"{result.unchanged} unchanged, {result.protected} protected, "
            f"{result.blocked} blocked, {result.failed} failed"
        )
    return result


def _apply_review_flag_updates(
    fm: dict,
    entry: registry_mod.RegistryEntry,
    reg_data: dict,
    library_root: Path,
) -> None:
    stale_views = _collect_stale_links_for_note(entry, fm, reg_data, library_root)
    has_stale_signal = any(view.state in {"stale", "re_evaluate_pending", "repair_blocked"} for view in stale_views)
    fm["review_flags"] = _review_flags_with_provenance(fm, has_stale_signal)


def _collect_stale_links_for_note(
    entry: registry_mod.RegistryEntry,
    fm: dict,
    reg_data: dict,
    library_root: Path,
) -> list[StaleLinkView]:
    md_path = library_root / entry.markdown_path
    content, _ = _read_markdown(md_path)
    source_items = extract_evidence_items(content)
    links = [link for link in fm.get("provenance_links", []) or [] if isinstance(link, dict)]
    views: list[StaleLinkView] = []
    for link in links:
        target_id = str(link.get("target_doc", ""))
        target_entry_data = reg_data.get("decks", {}).get(target_id)
        target_items: list[ExtractedEvidenceItem] = []
        if isinstance(target_entry_data, dict):
            target_entry = registry_mod.entry_from_dict(target_entry_data)
            target_path = library_root / target_entry.markdown_path
            target_content, target_fm = _read_markdown(target_path)
            if target_fm is not None:
                target_items = extract_evidence_items(target_content)
        pair_meta = _pair_meta_for_target(fm, target_id)
        state, orphaned = _surface_link_state(link, source_items, target_items, pair_meta)
        if state == "fresh":
            continue
        views.append(
            StaleLinkView(
                source_id=entry.id,
                target_id=target_id,
                md_path=md_path,
                link=link,
                state=state,
                orphaned=orphaned,
                title=entry.title,
            )
        )
    return sorted(
        views,
        key=lambda view: (
            view.source_id,
            {"repair_blocked": 0, "re_evaluate_pending": 1, "stale": 2, "acknowledged": 3}.get(view.state, 9),
            1 if view.orphaned else 0,
            str(view.link.get("link_id", "")),
        ),
    )


def collect_pending_proposals(
    config: FolioConfig,
    *,
    scope: str | None = None,
    include_low: bool = False,
    doc_id: str | None = None,
    target_id: str | None = None,
) -> list[PendingProposalView]:
    """Collect pending proposals across evidence notes in deterministic order."""
    library_root = config.library_root.resolve()
    reg_data = _ensure_registry(config, persist=False)
    views: list[PendingProposalView] = []
    for deck_id in sorted(reg_data.get("decks", {})):
        entry = registry_mod.entry_from_dict(reg_data["decks"][deck_id])
        if entry.type != "evidence":
            continue
        if scope and not (
            _matches_scope(entry.deck_dir, scope)
            or _matches_scope(entry.markdown_path, scope)
            or entry.id == scope
        ):
            continue
        if doc_id and entry.id != doc_id:
            continue
        md_path = library_root / entry.markdown_path
        _content, fm = _read_markdown(md_path)
        if fm is None:
            continue
        prov = _get_provenance_root(fm)
        for current_target_id, pair_meta in sorted((prov.get("pairs") or {}).items()):
            if target_id and current_target_id != target_id:
                continue
            if not isinstance(pair_meta, dict):
                continue
            for raw in pair_meta.get("proposals", []) or []:
                if not isinstance(raw, dict):
                    continue
                proposal = ProvenanceProposal.from_dict(raw)
                if proposal.status != "pending_human_confirmation":
                    continue
                if not include_low and proposal.confidence == "low":
                    continue
                views.append(
                    PendingProposalView(
                        source_id=entry.id,
                        target_id=current_target_id,
                        proposal=proposal,
                        md_path=md_path,
                        title=entry.title,
                    )
                )
    return sorted(
        views,
        key=lambda view: (
            view.source_id,
            _CONFIDENCE_RANK.get(view.proposal.confidence, 99),
            view.proposal.proposal_id,
        ),
    )


def collect_stale_links(
    config: FolioConfig,
    *,
    scope: str | None = None,
    doc_id: str | None = None,
    target_id: str | None = None,
) -> list[StaleLinkView]:
    """Collect stale/repair-pending/acknowledged links in scope."""
    library_root = config.library_root.resolve()
    reg_data = _ensure_registry(config, persist=False)
    views: list[StaleLinkView] = []
    for deck_id in sorted(reg_data.get("decks", {})):
        entry = registry_mod.entry_from_dict(reg_data["decks"][deck_id])
        if entry.type != "evidence":
            continue
        if scope and not (
            _matches_scope(entry.deck_dir, scope)
            or _matches_scope(entry.markdown_path, scope)
            or entry.id == scope
        ):
            continue
        if doc_id and entry.id != doc_id:
            continue
        md_path = library_root / entry.markdown_path
        _content, fm = _read_markdown(md_path)
        if fm is None:
            continue
        for view in _collect_stale_links_for_note(entry, fm, reg_data, library_root):
            if target_id and view.target_id != target_id:
                continue
            views.append(view)
    return views


def provenance_status_summary(config: FolioConfig, *, scope: str | None = None) -> list[dict]:
    """Build per-source provenance status rows for CLI output."""
    library_root = config.library_root.resolve()
    reg_data = _ensure_registry(config, persist=False)
    rows: list[dict] = []
    for deck_id in sorted(reg_data.get("decks", {})):
        entry = registry_mod.entry_from_dict(reg_data["decks"][deck_id])
        if entry.type != "evidence":
            continue
        if scope and not (
            _matches_scope(entry.deck_dir, scope)
            or _matches_scope(entry.markdown_path, scope)
            or entry.id == scope
        ):
            continue
        md_path = library_root / entry.markdown_path
        content, fm = _read_markdown(md_path)
        if fm is None:
            continue
        prov = _get_provenance_root(fm)
        has_pair = isinstance(fm.get("supersedes"), str) and bool(fm.get("supersedes"))
        has_links_or_pairs = has_pair or bool(fm.get("provenance_links")) or bool((prov.get("pairs") or {}))
        if not has_links_or_pairs:
            continue
        source_items = extract_evidence_items(content)
        stale_views = _collect_stale_links_for_note(entry, fm, reg_data, library_root)
        fresh_claims: set[tuple[int, int]] = set()
        stale_count = 0
        ack_count = 0
        reeval_count = 0
        blocked_count = 0
        orphaned_count = 0
        for view in stale_views:
            if view.orphaned:
                orphaned_count += 1
            if view.state == "stale":
                stale_count += 1
            elif view.state == "acknowledged":
                ack_count += 1
            elif view.state == "re_evaluate_pending":
                reeval_count += 1
            elif view.state == "repair_blocked":
                blocked_count += 1
        links = [link for link in fm.get("provenance_links", []) or [] if isinstance(link, dict)]
        for link in links:
            target_id = str(link.get("target_doc", ""))
            pair_meta = _pair_meta_for_target(fm, target_id)
            target_entry_data = reg_data.get("decks", {}).get(target_id)
            target_items: list[ExtractedEvidenceItem] = []
            if isinstance(target_entry_data, dict):
                target_entry = registry_mod.entry_from_dict(target_entry_data)
                target_content, target_fm = _read_markdown(library_root / target_entry.markdown_path)
                if target_fm is not None:
                    target_items = extract_evidence_items(target_content)
            state, _ = _surface_link_state(link, source_items, target_items, pair_meta)
            if state == "fresh":
                fresh_claims.add((int(link.get("source_slide", -1)), int(link.get("source_claim_index", -1))))
        pending = 0
        rejected = 0
        for pair_meta in (prov.get("pairs") or {}).values():
            if not isinstance(pair_meta, dict):
                continue
            for raw in pair_meta.get("proposals", []) or []:
                if not isinstance(raw, dict):
                    continue
                if raw.get("status") == "pending_human_confirmation":
                    pending += 1
                elif raw.get("status") == "rejected":
                    rejected += 1
        rows.append(
            {
                "source_id": entry.id,
                "pairs": 1 if has_pair else 0,
                "claims": len(source_items),
                "pending": pending,
                "fresh": len(fresh_claims),
                "stale": stale_count,
                "acknowledged": ack_count,
                "re_evaluate_pending": reeval_count,
                "blocked": blocked_count,
                "orphaned": orphaned_count,
                "rejected": rejected,
                "coverage_numerator": len(fresh_claims),
                "fresh_claims": fresh_claims,
            }
        )
    return rows


def _write_frontmatter_only(path: Path, content: str, fm: dict) -> None:
    new_content = _replace_frontmatter(content, fm)
    _atomic_write_text(path, new_content)


def _refresh_hashes_for_link(
    source_id: str,
    link: dict,
    source_items: list[ExtractedEvidenceItem],
    target_items: list[ExtractedEvidenceItem],
) -> None:
    source_item = _find_item(source_items, int(link.get("source_slide", -1)), int(link.get("source_claim_index", -1)))
    target_item = _find_item(target_items, int(link.get("target_slide", -1)), int(link.get("target_claim_index", -1)))
    if source_item is None or target_item is None:
        raise ValueError(f"Cannot refresh hashes for orphaned link {link.get('link_id')}")
    refreshed = _serialize_link(
        source_id=source_id,
        target_id=str(link.get("target_doc", "")),
        source_item=source_item,
        target_item=target_item,
        confidence=str(link.get("confidence", "medium")),
        replaces_link_id=None,
    )
    link.update(refreshed)
    _clear_acknowledgement_fields(link)


def confirm_proposal(config: FolioConfig, proposal_id: str) -> str:
    """Confirm one pending proposal into canonical `provenance_links`."""
    matches = [view for view in collect_pending_proposals(config, include_low=True) if view.proposal.proposal_id == proposal_id]
    if not matches:
        raise ValueError(f"Unknown proposal_id '{proposal_id}'")
    view = matches[0]
    content, fm = _read_markdown(view.md_path)
    if fm is None:
        raise ValueError(f"Cannot read frontmatter from {view.md_path}")
    pair_meta = _pair_meta_for_target(fm, view.target_id)
    proposals = _proposals_for_pair(pair_meta)
    proposal = next((proposal for proposal in proposals if proposal.proposal_id == proposal_id), None)
    if proposal is None:
        raise ValueError(f"Proposal '{proposal_id}' is no longer pending")

    library_root = config.library_root.resolve()
    reg_data = _ensure_registry(config, persist=False)
    source_entry = registry_mod.entry_from_dict(reg_data["decks"][view.source_id])
    target_entry_data = reg_data.get("decks", {}).get(view.target_id)
    if not isinstance(target_entry_data, dict):
        raise ValueError(f"Target document '{view.target_id}' is missing")
    target_entry = registry_mod.entry_from_dict(target_entry_data)
    target_content, target_fm = _read_markdown(library_root / target_entry.markdown_path)
    if target_fm is None:
        raise ValueError(f"Cannot read target frontmatter for '{view.target_id}'")

    source_items = extract_evidence_items(content)
    target_items = extract_evidence_items(target_content)
    source_item = _find_item(
        source_items,
        int(proposal.source_claim.get("slide_number", -1)),
        int(proposal.source_claim.get("claim_index", -1)),
    )
    target_item = _find_item(
        target_items,
        int(proposal.target_evidence.get("slide_number", -1)),
        int(proposal.target_evidence.get("claim_index", -1)),
    )
    if source_item is None or target_item is None:
        raise ValueError("Proposal coordinates no longer exist in current content")

    new_link = _serialize_link(
        source_id=source_entry.id,
        target_id=view.target_id,
        source_item=source_item,
        target_item=target_item,
        confidence=proposal.confidence,
        replaces_link_id=proposal.replaces_link_id,
    )
    links = [link for link in fm.get("provenance_links", []) or [] if isinstance(link, dict)]
    link_id = new_link["link_id"]
    replaced = False
    if proposal.replaces_link_id:
        updated_links = []
        for link in links:
            if link.get("link_id") == proposal.replaces_link_id:
                if proposal.replaces_link_id == link_id:
                    link.update(new_link)
                    _clear_acknowledgement_fields(link)
                    replaced = True
                    updated_links.append(link)
                continue
            updated_links.append(link)
        links = updated_links
    for link in links:
        if link.get("link_id") == link_id:
            link.update(new_link)
            _clear_acknowledgement_fields(link)
            replaced = True
            break
    if not replaced:
        links.append(new_link)
    fm["provenance_links"] = sorted(
        links,
        key=lambda link: (
            int(link.get("source_slide", -1)),
            int(link.get("source_claim_index", -1)),
            int(link.get("target_slide", -1)),
            int(link.get("target_claim_index", -1)),
            str(link.get("link_id", "")),
        ),
    )
    pair_meta["proposals"] = [
        raw for raw in pair_meta.get("proposals", [])
        if not isinstance(raw, dict) or raw.get("proposal_id") != proposal_id
    ]
    if not _repair_links_for_target(fm, view.target_id):
        _clear_pair_repair_state(pair_meta)
    _apply_review_flag_updates(fm, source_entry, reg_data, library_root)
    _write_frontmatter_only(view.md_path, content, fm)
    return link_id


def reject_proposal(config: FolioConfig, proposal_id: str) -> None:
    """Reject one pending provenance proposal."""
    matches = [view for view in collect_pending_proposals(config, include_low=True) if view.proposal.proposal_id == proposal_id]
    if not matches:
        raise ValueError(f"Unknown proposal_id '{proposal_id}'")
    view = matches[0]
    content, fm = _read_markdown(view.md_path)
    if fm is None:
        raise ValueError(f"Cannot read frontmatter from {view.md_path}")
    pair_meta = _pair_meta_for_target(fm, view.target_id)
    updated = False
    for raw in pair_meta.get("proposals", []) or []:
        if isinstance(raw, dict) and raw.get("proposal_id") == proposal_id:
            raw["status"] = "rejected"
            updated = True
            break
    if not updated:
        raise ValueError(f"Proposal '{proposal_id}' is no longer pending")
    _write_frontmatter_only(view.md_path, content, fm)


def _apply_to_doc_proposals(
    config: FolioConfig,
    *,
    doc_id: str,
    target_id: str | None,
    action: Callable[[FolioConfig, str], None],
) -> int:
    proposals = collect_pending_proposals(config, include_low=False, doc_id=doc_id, target_id=target_id)
    count = 0
    for view in proposals:
        action(config, view.proposal.proposal_id)
        count += 1
    return count


def confirm_doc(config: FolioConfig, doc_id: str, *, target_id: str | None = None) -> int:
    return _apply_to_doc_proposals(config, doc_id=doc_id, target_id=target_id, action=lambda cfg, pid: confirm_proposal(cfg, pid))


def reject_doc(config: FolioConfig, doc_id: str, *, target_id: str | None = None) -> int:
    return _apply_to_doc_proposals(config, doc_id=doc_id, target_id=target_id, action=reject_proposal)


def confirm_range(config: FolioConfig, range_expr: str, *, scope: str | None = None, doc_id: str | None = None, target_id: str | None = None) -> int:
    proposals = collect_pending_proposals(config, scope=scope, include_low=False, doc_id=doc_id, target_id=target_id)
    if ".." not in range_expr:
        raise ValueError("Range must be start..end")
    start_id, end_id = range_expr.split("..", 1)
    ids = [view.proposal.proposal_id for view in proposals]
    try:
        start_index = ids.index(start_id)
        end_index = ids.index(end_id)
    except ValueError as exc:
        raise ValueError("Range endpoints not found in current pending ordering") from exc
    if start_index > end_index:
        start_index, end_index = end_index, start_index
    count = 0
    for proposal_id in ids[start_index:end_index + 1]:
        confirm_proposal(config, proposal_id)
        count += 1
    return count


def stale_refresh_hashes(config: FolioConfig, link_id: str) -> RefreshHashesPreview:
    views = [view for view in collect_stale_links(config) if view.link.get("link_id") == link_id]
    if not views:
        raise ValueError(f"Unknown stale link '{link_id}'")
    view = views[0]
    if view.orphaned:
        raise ValueError("refresh-hashes is not available for orphaned links")
    content, fm = _read_markdown(view.md_path)
    if fm is None:
        raise ValueError(f"Cannot read frontmatter from {view.md_path}")
    library_root = config.library_root.resolve()
    reg_data = _ensure_registry(config, persist=False)
    source_entry = registry_mod.entry_from_dict(reg_data["decks"][view.source_id])
    target_entry = registry_mod.entry_from_dict(reg_data["decks"][view.target_id])
    source_items = extract_evidence_items(content)
    target_content, target_fm = _read_markdown(library_root / target_entry.markdown_path)
    if target_fm is None:
        raise ValueError(f"Cannot read target frontmatter for '{view.target_id}'")
    target_items = extract_evidence_items(target_content)
    preview: RefreshHashesPreview | None = None
    for link in fm.get("provenance_links", []) or []:
        if isinstance(link, dict) and link.get("link_id") == link_id:
            source_item = _find_item(
                source_items,
                int(link.get("source_slide", -1)),
                int(link.get("source_claim_index", -1)),
            )
            target_item = _find_item(
                target_items,
                int(link.get("target_slide", -1)),
                int(link.get("target_claim_index", -1)),
            )
            if source_item is None or target_item is None:
                raise ValueError(f"Cannot refresh hashes for orphaned link {link.get('link_id')}")
            preview = RefreshHashesPreview(
                source_before=_evidence_snapshot(
                    slide_number=int(link.get("source_slide", -1)),
                    claim_index=int(link.get("source_claim_index", -1)),
                    claim_text=str(link.get("source_claim_text_snapshot", "")),
                    supporting_quote=str(link.get("source_supporting_quote_snapshot", "")),
                ),
                source_after=_evidence_snapshot(
                    slide_number=source_item.slide_number,
                    claim_index=source_item.claim_index,
                    claim_text=source_item.claim_text,
                    supporting_quote=source_item.supporting_quote,
                ),
                target_before=_evidence_snapshot(
                    slide_number=int(link.get("target_slide", -1)),
                    claim_index=int(link.get("target_claim_index", -1)),
                    claim_text=str(link.get("target_claim_text_snapshot", "")),
                    supporting_quote=str(link.get("target_supporting_quote_snapshot", "")),
                ),
                target_after=_evidence_snapshot(
                    slide_number=target_item.slide_number,
                    claim_index=target_item.claim_index,
                    claim_text=target_item.claim_text,
                    supporting_quote=target_item.supporting_quote,
                ),
            )
            _refresh_hashes_for_link(source_entry.id, link, source_items, target_items)
            break
    if preview is None:
        raise ValueError(f"Unknown stale link '{link_id}'")
    pair_meta = _pair_meta_for_target(fm, view.target_id)
    if not _repair_links_for_target(fm, view.target_id):
        _clear_pair_repair_state(pair_meta)
    _apply_review_flag_updates(fm, source_entry, reg_data, library_root)
    _write_frontmatter_only(view.md_path, content, fm)
    return preview


def stale_re_evaluate(config: FolioConfig, link_id: str) -> None:
    views = [view for view in collect_stale_links(config) if view.link.get("link_id") == link_id]
    if not views:
        raise ValueError(f"Unknown stale link '{link_id}'")
    view = views[0]
    content, fm = _read_markdown(view.md_path)
    if fm is None:
        raise ValueError(f"Cannot read frontmatter from {view.md_path}")
    for link in fm.get("provenance_links", []) or []:
        if isinstance(link, dict) and link.get("link_id") == link_id:
            link["link_status"] = "re_evaluate_pending"
            break
    pair_meta = _pair_meta_for_target(fm, view.target_id)
    pair_meta["re_evaluate_requested"] = True
    pair_meta["repair_error"] = None
    pair_meta["repair_error_detail"] = None
    pair_meta["repair_attempts"] = 0
    library_root = config.library_root.resolve()
    reg_data = _ensure_registry(config, persist=False)
    source_entry = registry_mod.entry_from_dict(reg_data["decks"][view.source_id])
    _apply_review_flag_updates(fm, source_entry, reg_data, library_root)
    _write_frontmatter_only(view.md_path, content, fm)


def stale_remove(config: FolioConfig, link_id: str) -> None:
    views = [view for view in collect_stale_links(config) if view.link.get("link_id") == link_id]
    if not views:
        raise ValueError(f"Unknown stale link '{link_id}'")
    view = views[0]
    content, fm = _read_markdown(view.md_path)
    if fm is None:
        raise ValueError(f"Cannot read frontmatter from {view.md_path}")
    fm["provenance_links"] = [
        link for link in fm.get("provenance_links", []) or []
        if not isinstance(link, dict) or link.get("link_id") != link_id
    ]
    pair_meta = _pair_meta_for_target(fm, view.target_id)
    if not _repair_links_for_target(fm, view.target_id):
        _clear_pair_repair_state(pair_meta)
    library_root = config.library_root.resolve()
    reg_data = _ensure_registry(config, persist=False)
    source_entry = registry_mod.entry_from_dict(reg_data["decks"][view.source_id])
    _apply_review_flag_updates(fm, source_entry, reg_data, library_root)
    _write_frontmatter_only(view.md_path, content, fm)


def stale_acknowledge(config: FolioConfig, link_id: str) -> None:
    views = [view for view in collect_stale_links(config) if view.link.get("link_id") == link_id]
    if not views:
        raise ValueError(f"Unknown stale link '{link_id}'")
    view = views[0]
    content, fm = _read_markdown(view.md_path)
    if fm is None:
        raise ValueError(f"Cannot read frontmatter from {view.md_path}")
    library_root = config.library_root.resolve()
    reg_data = _ensure_registry(config, persist=False)
    target_entry = registry_mod.entry_from_dict(reg_data["decks"][view.target_id])
    source_entry = registry_mod.entry_from_dict(reg_data["decks"][view.source_id])
    source_items = extract_evidence_items(content)
    target_content, target_fm = _read_markdown(library_root / target_entry.markdown_path)
    if target_fm is None:
        raise ValueError(f"Cannot read target frontmatter for '{view.target_id}'")
    target_items = extract_evidence_items(target_content)
    for link in fm.get("provenance_links", []) or []:
        if not isinstance(link, dict) or link.get("link_id") != link_id:
            continue
        source_item = _find_item(source_items, int(link.get("source_slide", -1)), int(link.get("source_claim_index", -1)))
        target_item = _find_item(target_items, int(link.get("target_slide", -1)), int(link.get("target_claim_index", -1)))
        if source_item is None or target_item is None:
            raise ValueError("Cannot acknowledge an orphaned link")
        link["link_status"] = "acknowledged_stale"
        link["acknowledged_at_claim_hash"] = source_item.claim_hash
        link["acknowledged_at_target_hash"] = target_item.claim_hash
        break
    pair_meta = _pair_meta_for_target(fm, view.target_id)
    if not _repair_links_for_target(fm, view.target_id):
        _clear_pair_repair_state(pair_meta)
    _apply_review_flag_updates(fm, source_entry, reg_data, library_root)
    _write_frontmatter_only(view.md_path, content, fm)


def stale_remove_doc(config: FolioConfig, doc_id: str, *, scope: str | None = None) -> int:
    views = collect_stale_links(config, scope=scope, doc_id=doc_id)
    count = 0
    for view in views:
        stale_remove(config, str(view.link.get("link_id", "")))
        count += 1
    return count


def stale_acknowledge_doc(config: FolioConfig, doc_id: str, *, scope: str | None = None) -> int:
    views = collect_stale_links(config, scope=scope, doc_id=doc_id)
    count = 0
    for view in views:
        if view.state == "acknowledged":
            continue
        stale_acknowledge(config, str(view.link.get("link_id", "")))
        count += 1
    return count


def paginate(items: list, page: int) -> tuple[list, int]:
    """Return one page and total pages for PAGE_SIZE pagination."""
    total_pages = max(1, math.ceil(len(items) / PAGE_SIZE))
    current_page = max(1, min(page, total_pages))
    start = (current_page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    return items[start:end], total_pages


def run_provenance(
    config: FolioConfig,
    *,
    scope: str | None = None,
    dry_run: bool = False,
    llm_profile: str | None = None,
    limit: int | None = None,
    force: bool = False,
    clear_rejections: bool = False,
    echo: Optional[Callable[[str], None]] = None,
) -> dict:
    """CLI-facing wrapper returning a plain dict summary."""
    result = provenance_batch(
        config,
        scope=scope,
        dry_run=dry_run,
        llm_profile=llm_profile,
        force=force,
        clear_rejections=clear_rejections,
        limit=limit,
        echo=echo,
    )
    return {
        "evaluated": result.evaluated,
        "proposed": result.proposed,
        "unchanged": result.unchanged,
        "protected": result.protected,
        "blocked": result.blocked,
        "failed": result.failed,
        "skipped": result.skipped,
        "candidate_pairs": result.candidate_pairs,
        "estimated_calls": result.estimated_calls,
        "pending_repairs": result.pending_repairs,
    }


def list_pending_proposals(
    config: FolioConfig,
    *,
    scope: str | None = None,
    include_low: bool = False,
    doc_id: str | None = None,
    target_id: str | None = None,
) -> list[dict]:
    """CLI-facing pending proposal rows."""
    rows: list[dict] = []
    for view in collect_pending_proposals(
        config,
        scope=scope,
        include_low=include_low,
        doc_id=doc_id,
        target_id=target_id,
    ):
        row = view.proposal.to_dict()
        row["source_doc"] = view.source_id
        row["target_doc"] = view.target_id
        row["title"] = view.title
        rows.append(row)
    return rows


def list_stale_links(
    config: FolioConfig,
    *,
    scope: str | None = None,
    doc_id: str | None = None,
    target_id: str | None = None,
) -> list[dict]:
    """CLI-facing stale-link rows."""
    rows: list[dict] = []
    for view in collect_stale_links(
        config,
        scope=scope,
        doc_id=doc_id,
        target_id=target_id,
    ):
        rows.append(
            {
                "source_doc": view.source_id,
                "target_doc": view.target_id,
                "title": view.title,
                "link": view.link,
                "state": view.state,
                "orphaned": view.orphaned,
            }
        )
    return rows


def summarize_status(config: FolioConfig, *, scope: str | None = None) -> list[dict]:
    """CLI-facing status rows."""
    rows: list[dict] = []
    for row in provenance_status_summary(config, scope=scope):
        rows.append(
            {
                "source_doc": row["source_id"],
                "pairs": row["pairs"],
                "claims": row["claims"],
                "pending": row["pending"],
                "fresh": row["fresh"],
                "stale": row["stale"],
                "acknowledged": row["acknowledged"],
                "re_evaluate_pending": row["re_evaluate_pending"],
                "blocked": row["blocked"],
                "orphaned": row["orphaned"],
                "rejected": row["rejected"],
                "coverage_numerator": len(row.get("fresh_claims", set())),
            }
        )
    return rows


def confirm_proposals_in_order(config: FolioConfig, proposal_ids: list[str]) -> int:
    count = 0
    for proposal_id in proposal_ids:
        confirm_proposal(config, proposal_id)
        count += 1
    return count


def reject_proposals_in_order(config: FolioConfig, proposal_ids: list[str]) -> int:
    count = 0
    for proposal_id in proposal_ids:
        reject_proposal(config, proposal_id)
        count += 1
    return count


def refresh_stale_link_hashes(config: FolioConfig, link_id: str) -> None:
    stale_refresh_hashes(config, link_id)


def re_evaluate_stale_link(config: FolioConfig, link_id: str) -> None:
    stale_re_evaluate(config, link_id)


def remove_stale_link(config: FolioConfig, link_id: str) -> None:
    stale_remove(config, link_id)


def acknowledge_stale_link(config: FolioConfig, link_id: str) -> None:
    stale_acknowledge(config, link_id)
