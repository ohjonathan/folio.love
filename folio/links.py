"""Document-level relationship proposal review and confirmation."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    revived: bool = False
    flagged_inputs: list[str] = field(default_factory=list)  # ["source"], ["target"], or both


@dataclass
class SuppressionCounts:
    """Structured suppression counts returned alongside proposal views.

    Split into per-producer rejection-memory counts and a scalar flagged-input
    count. Prevents producer-name collision with a sentinel string and keeps
    renderers from conflating the two reasons (v0.6.4 CB-3 resolution).
    """

    rejection_memory: dict[str, int] = field(default_factory=dict)
    flagged_input: int = 0

    def total(self) -> int:
        return sum(self.rejection_memory.values()) + self.flagged_input


@dataclass
class RelationshipStatusRow:
    source_id: str
    pending: int
    confirmed: int
    flagged_excluded: int = 0


def _matches_scope(path: str, scope: str) -> bool:
    norm_scope = scope.rstrip("/") + "/"
    return path == scope or path.startswith(norm_scope)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_markdown(path: Path) -> tuple[str, dict | None]:
    content = path.read_text(encoding="utf-8")
    return content, registry_mod._read_frontmatter(path)


def _is_flagged(value) -> bool:
    """Normalize review_status to a flagged boolean.

    Conservative policy (v0.6.4 SF-E):
      - None or missing -> False
      - String exactly "flagged" (after strip + lower) -> True
      - Other string values -> False (unknown status)
      - Non-string values (list, dict, bool, int) -> False (malformed; fail-open)
    """
    if value is None:
        return False
    if not isinstance(value, str):
        return False
    return value.strip().lower() == "flagged"


def _resolve_target_flagged(
    target_id: str,
    registry_data: dict,
    library_root: Path,
    cache: dict[str, bool],
) -> bool:
    """Read target frontmatter review_status; cache result per-call.

    v0.6.4 CB-1 resolution: target trust state is read from frontmatter,
    not the registry dict. The registry can be stale between syncs and
    `review_status` is frontmatter-authoritative. Cache keyed by target_id
    bounds file I/O at O(unique_targets) per collect_pending call.
    """
    if target_id in cache:
        return cache[target_id]
    target_entry = registry_data.get("decks", {}).get(target_id)
    if not target_entry:
        cache[target_id] = False
        return False
    markdown_path = target_entry.get("markdown_path", "")
    if not markdown_path:
        cache[target_id] = False
        return False
    target_path = library_root / markdown_path
    target_fm = registry_mod._read_frontmatter(target_path)
    flagged = isinstance(target_fm, dict) and _is_flagged(target_fm.get("review_status"))
    cache[target_id] = flagged
    return flagged


def _build_rejection_key(
    source_id: str,
    proposal: RelationshipProposal,
) -> tuple[str, str, str, str]:
    return (
        source_id,
        proposal.target_id,
        proposal.relation,
        proposal.basis_fingerprint,
    )


def _is_rejection_suppressed(
    candidate_key: tuple[str, str, str, str],
    rejected_keys: set[tuple[str, str, str, str]],
) -> bool:
    return candidate_key in rejected_keys


def _proposal_from_raw(source_id: str, producer: str, raw: dict) -> RelationshipProposal:
    raw_copy = dict(raw)
    raw_copy.setdefault("producer", producer)
    raw_copy.setdefault("source_id", source_id)
    raw_copy.setdefault("relation", "")
    raw_copy.setdefault("target_id", "")
    raw_copy.setdefault("basis_fingerprint", "")
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
        if producer == "links":
            continue  # reserved namespace for confirmed_relationships; not a producer axis
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
            # Reject proposals with invalid target_id (empty string or non-string).
            # The D.4 scalar-default fix prevents KeyError on legacy frontmatter
            # missing target_id, but a proposal with target_id="" must not surface
            # as confirmable — confirming it would write canonical `impacts: ['']`
            # and corrupt frontmatter.
            if not isinstance(proposal.target_id, str) or not proposal.target_id:
                continue
            yield producer, raw, proposal


def collect_pending_relationship_proposals(
    config: FolioConfig,
    *,
    scope: Optional[str] = None,
    doc_id: Optional[str] = None,
    target_id: Optional[str] = None,
    include_flagged: bool = False,
) -> tuple[list[RelationshipProposalView], SuppressionCounts]:
    library_root = config.library_root.resolve()
    registry_data = registry_mod.load_registry(library_root / "registry.json")
    views: list[RelationshipProposalView] = []
    counts = SuppressionCounts()
    target_flagged_cache: dict[str, bool] = {}

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

        source_flagged = _is_flagged(fm.get("review_status"))

        rejected_keys_by_producer: dict[str, set[tuple[str, str, str, str]]] = {}
        rejected_fps_by_prefix: dict[str, dict[tuple[str, str, str], set[str]]] = {}
        for producer, _raw, proposal in _iter_producer_proposals(entry.id, fm):
            if proposal.lifecycle_state != "rejected":
                continue
            # Skip rejected entries with empty basis_fingerprint — treating
            # them as valid rejection keys would false-suppress pending
            # proposals that share the producer defect of empty fingerprints.
            if not proposal.basis_fingerprint:
                continue
            key = _build_rejection_key(entry.id, proposal)
            rejected_keys_by_producer.setdefault(producer, set()).add(key)
            prefix = (entry.id, proposal.target_id, proposal.relation)
            rejected_fps_by_prefix.setdefault(producer, {}).setdefault(prefix, set()).add(
                proposal.basis_fingerprint
            )

        for producer, _raw, proposal in _iter_producer_proposals(entry.id, fm):
            if proposal.lifecycle_state != "queued":
                continue
            if target_id and proposal.target_id != target_id:
                continue

            key = _build_rejection_key(entry.id, proposal)
            rejected_keys = rejected_keys_by_producer.get(producer, set())
            if _is_rejection_suppressed(key, rejected_keys):
                counts.rejection_memory[producer] = (
                    counts.rejection_memory.get(producer, 0) + 1
                )
                continue

            # Flagged-input check (§11 rule 1). Ordered AFTER rejection-memory
            # so an explicit operator rejection takes precedence as a
            # suppression reason (CB-3 / ADV-I-001).
            target_flagged = _resolve_target_flagged(
                proposal.target_id, registry_data, library_root, target_flagged_cache
            )
            flagged_list: list[str] = []
            if source_flagged:
                flagged_list.append("source")
            if target_flagged:
                flagged_list.append("target")
            if flagged_list and not include_flagged:
                counts.flagged_input += 1
                continue

            prefix = (entry.id, proposal.target_id, proposal.relation)
            rejected_fps = rejected_fps_by_prefix.get(producer, {}).get(prefix, set())
            revived = bool(rejected_fps) and proposal.basis_fingerprint not in rejected_fps

            views.append(
                RelationshipProposalView(
                    source_id=entry.id,
                    source_path=md_path,
                    source_markdown_path=entry.markdown_path,
                    producer=producer,
                    proposal=proposal,
                    revived=revived,
                    flagged_inputs=flagged_list,
                )
            )

    views.sort(
        key=lambda view: (
            view.source_id,
            _CONFIDENCE_RANK.get(view.proposal.confidence, 9),
            view.proposal.proposal_id,
        )
    )
    return views, counts


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
    include_flagged: bool = False,
) -> tuple[list[RelationshipStatusRow], int]:
    """Summarize pending + confirmed relationships per source document.

    v0.6.4 CB-2 resolution: returns `(rows, total_flagged_excluded)`. Each row
    carries a `flagged_excluded` count for §11 rule 5 (no silent empty when
    flagged inputs are the real cause). A row is emitted whenever pending,
    confirmed, OR flagged_excluded is nonzero.

    When `include_flagged=True`, flagged-input proposals count toward
    `pending` and `flagged_excluded` is zero (operator has opted in).
    """
    library_root = config.library_root.resolve()
    registry_data = registry_mod.load_registry(library_root / "registry.json")

    # Single pass with include_flagged=True on collect so we can partition.
    # When the caller sets include_flagged=True, we roll flagged proposals
    # into `pending` and leave `flagged_excluded` at zero.
    all_views, _ = collect_pending_relationship_proposals(
        config, scope=scope, include_flagged=True
    )
    pending_counts: dict[str, int] = {}
    flagged_counts: dict[str, int] = {}
    for view in all_views:
        if view.flagged_inputs and not include_flagged:
            flagged_counts[view.source_id] = flagged_counts.get(view.source_id, 0) + 1
        else:
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
        flagged_excluded = flagged_counts.get(entry.id, 0)
        confirmed = len(canonical_relationship_targets(fm))
        if pending or confirmed or flagged_excluded:
            rows.append(
                RelationshipStatusRow(
                    source_id=entry.id,
                    pending=pending,
                    confirmed=confirmed,
                    flagged_excluded=flagged_excluded,
                )
            )

    rows.sort(key=lambda row: row.source_id)
    total_flagged_excluded = sum(flagged_counts.values())
    return rows, total_flagged_excluded


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


def _find_pending_view(
    config: FolioConfig,
    proposal_id: str,
    *,
    include_flagged: bool = False,
) -> RelationshipProposalView:
    views, _ = collect_pending_relationship_proposals(
        config, include_flagged=include_flagged
    )
    matches = [view for view in views if view.proposal.proposal_id == proposal_id]
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
            raw_copy["lifecycle_state"] = new_status
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
    include_flagged: bool = False,
) -> tuple[RelationshipProposal, list[str]]:
    """Confirm a pending proposal; return `(proposal, flagged_inputs)`.

    v0.6.4 DS-C: trust-posture annotation flows back to the CLI success line
    when the operator used `--include-flagged`.
    """
    view = _find_pending_view(config, proposal_id, include_flagged=include_flagged)
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
    return proposal, list(view.flagged_inputs)


def reject_proposal(
    config: FolioConfig,
    proposal_id: str,
    *,
    include_flagged: bool = False,
) -> tuple[RelationshipProposal, list[str]]:
    """Reject a pending proposal; return `(proposal, flagged_inputs)`.

    v0.6.4 DS-C: trust-posture annotation flows back to the CLI success line.
    """
    view = _find_pending_view(config, proposal_id, include_flagged=include_flagged)
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
    return proposal, list(view.flagged_inputs)


def confirm_doc(
    config: FolioConfig,
    doc_id: str,
    *,
    include_flagged: bool = False,
) -> tuple[int, int]:
    """Confirm all pending proposals for a document.

    Returns `(acted, flagged_excluded)` per v0.6.4 CB-2: `flagged_excluded`
    is the number of proposals that would have been surfaced with
    `include_flagged=True` but were filtered out because source or target
    had `review_status: flagged`.
    """
    views, counts = collect_pending_relationship_proposals(
        config, doc_id=doc_id, include_flagged=include_flagged
    )
    proposals = [view.proposal.proposal_id for view in views]
    acted = 0
    for proposal_id in proposals:
        confirm_proposal(
            config,
            proposal_id,
            confirmation_source="folio links confirm-doc",
            include_flagged=include_flagged,
        )
        acted += 1
    return acted, counts.flagged_input


def reject_doc(
    config: FolioConfig,
    doc_id: str,
    *,
    include_flagged: bool = False,
) -> tuple[int, int]:
    """Reject all pending proposals for a document.

    Returns `(acted, flagged_excluded)` per v0.6.4 CB-2.
    """
    views, counts = collect_pending_relationship_proposals(
        config, doc_id=doc_id, include_flagged=include_flagged
    )
    proposals = [view.proposal.proposal_id for view in views]
    acted = 0
    for proposal_id in proposals:
        reject_proposal(config, proposal_id, include_flagged=include_flagged)
        acted += 1
    return acted, counts.flagged_input


