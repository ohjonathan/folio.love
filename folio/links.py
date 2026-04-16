"""Document-level relationship proposal review and confirmation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import FolioConfig
from .enrich import _atomic_write_text, _replace_frontmatter
from .pipeline.enrich_data import (
    RELATIONSHIP_FIELDS,
    RelationshipProposal,
    compute_relationship_proposal_id,
    is_singular_relationship,
)
from .tracking import registry as registry_mod

PAGE_SIZE = 20
SUPPORTED_RELATIONS = frozenset({"supersedes", "impacts", "draws_from", "depends_on"})
_CONFIDENCE_RANK = {"high": 0, "medium": 1}


@dataclass
class RelationshipProposalView:
    source_id: str
    source_path: Path
    source_markdown_path: str
    producer: str
    proposal: RelationshipProposal


@dataclass
class RelationshipStatusRow:
    source_id: str
    pending: int
    confirmed: int


def _matches_scope(path: str, scope: str) -> bool:
    norm_scope = scope.rstrip("/") + "/"
    return path == scope or path.startswith(norm_scope)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_markdown(path: Path) -> tuple[str, dict | None]:
    content = path.read_text(encoding="utf-8")
    return content, registry_mod._read_frontmatter(path)


def _proposal_from_raw(source_id: str, producer: str, raw: dict) -> RelationshipProposal:
    raw_copy = dict(raw)
    raw_copy.setdefault("producer", producer)
    raw_copy.setdefault("source_id", source_id)
    if not raw_copy.get("proposal_id"):
        raw_copy["proposal_id"] = compute_relationship_proposal_id(
            source_id=source_id,
            relation=str(raw_copy.get("relation", "")),
            target_id=str(raw_copy.get("target_id", "")),
            basis_fingerprint=str(raw_copy.get("basis_fingerprint", "")),
        )
    return RelationshipProposal.from_dict(raw_copy)


def canonical_relationship_targets(fm: dict) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    for field_name in RELATIONSHIP_FIELDS:
        value = fm.get(field_name)
        if isinstance(value, str) and value:
            targets.append((field_name, value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item:
                    targets.append((field_name, item))
    return targets


def _iter_producer_proposals(source_id: str, fm: dict):
    llm_meta = fm.get("_llm_metadata")
    if not isinstance(llm_meta, dict):
        return
    for producer, producer_meta in llm_meta.items():
        if not isinstance(producer_meta, dict):
            continue
        axes = producer_meta.get("axes")
        if not isinstance(axes, dict):
            continue
        relationships = axes.get("relationships")
        if not isinstance(relationships, dict):
            continue
        proposals = relationships.get("proposals")
        if not isinstance(proposals, list):
            continue
        for raw in proposals:
            if not isinstance(raw, dict):
                continue
            proposal = _proposal_from_raw(source_id, producer, raw)
            if proposal.relation not in SUPPORTED_RELATIONS:
                continue
            yield producer, raw, proposal


def collect_pending_relationship_proposals(
    config: FolioConfig,
    *,
    scope: Optional[str] = None,
    doc_id: Optional[str] = None,
    target_id: Optional[str] = None,
) -> list[RelationshipProposalView]:
    library_root = config.library_root.resolve()
    registry_data = registry_mod.load_registry(library_root / "registry.json")
    proposals: list[RelationshipProposalView] = []

    for entry_id, entry_data in registry_data.get("decks", {}).items():
        entry = registry_mod.entry_from_dict(entry_data)
        if doc_id and entry.id != doc_id:
            continue
        if scope and not (
            _matches_scope(entry.markdown_path, scope)
            or _matches_scope(entry.deck_dir, scope)
        ):
            continue

        md_path = library_root / entry.markdown_path
        fm = registry_mod._read_frontmatter(md_path)
        if not isinstance(fm, dict):
            continue

        for producer, _raw, proposal in _iter_producer_proposals(entry.id, fm):
            if proposal.status != "pending_human_confirmation":
                continue
            if target_id and proposal.target_id != target_id:
                continue
            proposals.append(
                RelationshipProposalView(
                    source_id=entry.id,
                    source_path=md_path,
                    source_markdown_path=entry.markdown_path,
                    producer=producer,
                    proposal=proposal,
                )
            )

    proposals.sort(
        key=lambda view: (
            view.source_id,
            _CONFIDENCE_RANK.get(view.proposal.confidence, 9),
            view.proposal.proposal_id,
        )
    )
    return proposals


def paginate(rows: list, page: int) -> tuple[list, int]:
    total_pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(1, page), total_pages)
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    return rows[start:end], total_pages


def relationship_status_summary(
    config: FolioConfig,
    *,
    scope: Optional[str] = None,
) -> list[RelationshipStatusRow]:
    library_root = config.library_root.resolve()
    registry_data = registry_mod.load_registry(library_root / "registry.json")
    pending_counts: dict[str, int] = {}
    for view in collect_pending_relationship_proposals(config, scope=scope):
        pending_counts[view.source_id] = pending_counts.get(view.source_id, 0) + 1
    rows: list[RelationshipStatusRow] = []

    for entry_data in registry_data.get("decks", {}).values():
        entry = registry_mod.entry_from_dict(entry_data)
        if scope and not (
            _matches_scope(entry.markdown_path, scope)
            or _matches_scope(entry.deck_dir, scope)
        ):
            continue
        fm = registry_mod._read_frontmatter(library_root / entry.markdown_path)
        if not isinstance(fm, dict):
            continue
        pending = pending_counts.get(entry.id, 0)
        confirmed = len(canonical_relationship_targets(fm))
        if pending or confirmed:
            rows.append(RelationshipStatusRow(source_id=entry.id, pending=pending, confirmed=confirmed))

    rows.sort(key=lambda row: row.source_id)
    return rows


def _ensure_confirmation_meta(fm: dict) -> list[dict]:
    llm_meta = fm.setdefault("_llm_metadata", {})
    if not isinstance(llm_meta, dict):
        fm["_llm_metadata"] = {}
        llm_meta = fm["_llm_metadata"]
    links_meta = llm_meta.setdefault("links", {})
    if not isinstance(links_meta, dict):
        llm_meta["links"] = {}
        links_meta = llm_meta["links"]
    confirmed = links_meta.setdefault("confirmed_relationships", [])
    if not isinstance(confirmed, list):
        links_meta["confirmed_relationships"] = []
        confirmed = links_meta["confirmed_relationships"]
    return confirmed


def _upsert_confirmation_record(
    fm: dict,
    *,
    proposal: RelationshipProposal,
    confirmation_source: str,
) -> None:
    confirmed = _ensure_confirmation_meta(fm)
    record = {
        "proposal_id": proposal.proposal_id,
        "relation": proposal.relation,
        "target_id": proposal.target_id,
        "producer": proposal.producer,
        "basis_fingerprint": proposal.basis_fingerprint,
        "confirmed_at": _now_iso(),
        "confirmation_source": confirmation_source,
    }
    updated = False
    for idx, existing in enumerate(confirmed):
        if isinstance(existing, dict) and existing.get("proposal_id") == proposal.proposal_id:
            confirmed[idx] = record
            updated = True
            break
    if not updated:
        confirmed.append(record)
    confirmed.sort(key=lambda item: str(item.get("proposal_id", "")))


def _add_canonical_relationship(fm: dict, relation: str, target_id: str) -> None:
    if is_singular_relationship(relation):
        existing = fm.get(relation)
        if isinstance(existing, str) and existing and existing != target_id:
            raise ValueError(
                f"Canonical field '{relation}' already points to '{existing}'"
            )
        fm[relation] = target_id
        return

    existing_list = fm.get(relation, [])
    if isinstance(existing_list, str):
        existing_values = [existing_list] if existing_list else []
    elif isinstance(existing_list, list):
        existing_values = [item for item in existing_list if isinstance(item, str) and item]
    else:
        existing_values = []
    if target_id not in existing_values:
        existing_values.append(target_id)
    fm[relation] = sorted(dict.fromkeys(existing_values), key=str.lower)


def _write_markdown(path: Path, content: str, fm: dict) -> None:
    _atomic_write_text(path, _replace_frontmatter(content, fm))


def _find_pending_view(config: FolioConfig, proposal_id: str) -> RelationshipProposalView:
    matches = [
        view
        for view in collect_pending_relationship_proposals(config)
        if view.proposal.proposal_id == proposal_id
    ]
    if not matches:
        raise ValueError(f"Unknown proposal_id '{proposal_id}'")
    return matches[0]


def _remove_or_update_proposal(
    fm: dict,
    *,
    source_id: str,
    producer: str,
    proposal_id: str,
    new_status: Optional[str] = None,
) -> RelationshipProposal:
    llm_meta = fm.get("_llm_metadata")
    if not isinstance(llm_meta, dict):
        raise ValueError("Document has no relationship proposal metadata")
    producer_meta = llm_meta.get(producer)
    if not isinstance(producer_meta, dict):
        raise ValueError(f"Producer '{producer}' has no relationship proposal metadata")
    relationships = producer_meta.get("axes", {}).get("relationships", {})
    proposals = relationships.get("proposals")
    if not isinstance(proposals, list):
        raise ValueError(f"Producer '{producer}' has no relationship proposal list")

    kept: list[dict] = []
    matched: Optional[RelationshipProposal] = None
    for raw in proposals:
        if not isinstance(raw, dict):
            kept.append(raw)
            continue
        proposal = _proposal_from_raw(source_id, producer, raw)
        if proposal.proposal_id != proposal_id:
            kept.append(raw)
            continue
        matched = proposal
        if new_status is not None:
            raw_copy = dict(raw)
            raw_copy["proposal_id"] = proposal.proposal_id
            raw_copy["producer"] = proposal.producer
            raw_copy["status"] = new_status
            kept.append(raw_copy)

    if matched is None:
        raise ValueError(f"Proposal '{proposal_id}' is no longer pending")

    relationships["proposals"] = kept
    return matched


def confirm_proposal(
    config: FolioConfig,
    proposal_id: str,
    *,
    confirmation_source: str = "folio links confirm",
) -> RelationshipProposal:
    view = _find_pending_view(config, proposal_id)
    content, fm = _read_markdown(view.source_path)
    if fm is None:
        raise ValueError(f"Cannot read frontmatter from {view.source_path}")

    proposal = _remove_or_update_proposal(
        fm,
        source_id=view.source_id,
        producer=view.producer,
        proposal_id=proposal_id,
        new_status=None,
    )
    _add_canonical_relationship(fm, proposal.relation, proposal.target_id)
    _upsert_confirmation_record(
        fm,
        proposal=proposal,
        confirmation_source=confirmation_source,
    )
    _write_markdown(view.source_path, content, fm)
    return proposal


def reject_proposal(config: FolioConfig, proposal_id: str) -> RelationshipProposal:
    view = _find_pending_view(config, proposal_id)
    content, fm = _read_markdown(view.source_path)
    if fm is None:
        raise ValueError(f"Cannot read frontmatter from {view.source_path}")

    proposal = _remove_or_update_proposal(
        fm,
        source_id=view.source_id,
        producer=view.producer,
        proposal_id=proposal_id,
        new_status="rejected",
    )
    _write_markdown(view.source_path, content, fm)
    return proposal


def confirm_doc(config: FolioConfig, doc_id: str) -> int:
    proposals = [
        view.proposal.proposal_id
        for view in collect_pending_relationship_proposals(config, doc_id=doc_id)
    ]
    count = 0
    for proposal_id in proposals:
        confirm_proposal(config, proposal_id, confirmation_source="folio links confirm-doc")
        count += 1
    return count


def reject_doc(config: FolioConfig, doc_id: str) -> int:
    proposals = [
        view.proposal.proposal_id
        for view in collect_pending_relationship_proposals(config, doc_id=doc_id)
    ]
    count = 0
    for proposal_id in proposals:
        reject_proposal(config, proposal_id)
        count += 1
    return count
