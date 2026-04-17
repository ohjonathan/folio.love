"""Graph health reporting for canonical Folio ontology state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .analysis_docs import compute_graph_input_fingerprint, resolve_input_entries
from .config import FolioConfig
from .links import canonical_relationship_targets, collect_pending_relationship_proposals
from .tracking import registry as registry_mod
from .tracking.entities import EntityRegistry

_GRAPH_RELATION_FIELDS = ("depends_on", "draws_from", "impacts", "relates_to", "supersedes", "instantiates")
_GRAPH_DOC_TYPES = frozenset({"analysis", "deliverable", "evidence", "interaction"})
_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}
_ACCEPTANCE_WARMUP_COUNT = 10
_ACCEPTANCE_GATE_RATE = 0.50
_STATUS_SORT_RANK = {"low-acceptance": 0, "ok": 1, "warmup": 2}

# Shared proposal contract emitted keys (§5 of tier4_discovery_proposal_layer_spec
# rev 5). 9 parent §5 rows → 11 emitted keys after ID-triad split. See
# docs/specs/v0.7.1_folio_graph_generalized_proposals_spec.md §2.1.
_SHARED_PROPOSAL_CONTRACT_EMITTED_KEYS: tuple[str, ...] = (
    "proposal_type",
    "source_id",
    "target_id",
    "subject_id",
    "evidence_bundle",
    "reason_summary",
    "trust_status",
    "schema_gate_result",
    "producer",
    "input_fingerprint",
    "lifecycle_state",
)

# Mirrors folio/links.py:21. Duplicated here to avoid a retrofit-layer import
# from links.py — this slice consumes the contract, does not modify links.
_SUPPORTED_RELATIONS: frozenset[str] = frozenset({"supersedes", "impacts", "draws_from", "depends_on"})


@dataclass
class GraphStatus:
    pending_relationship_proposals: int
    docs_without_canonical_graph_links: int
    orphaned_canonical_relation_targets: int
    enrich_protected_notes: int
    unconfirmed_entities: int
    confirmed_entities_missing_stubs: int
    duplicate_person_candidates: int
    stale_analysis_artifacts: int


@dataclass(frozen=True)
class ProducerAcceptanceRate:
    producer: str
    accepted: int
    rejected: int
    total_reviewed: int
    rate: Optional[float]
    status: str  # "ok" | "low-acceptance" | "warmup"
    warmup: bool


def _derive_trust_status(view) -> str:
    flagged = set(view.flagged_inputs or [])
    return "flagged" if ({"source", "target"} & flagged) else "ok"


def _compute_relationship_schema_gate(view, all_ids: set[str]) -> Optional[dict]:
    if view.proposal.target_id not in all_ids:
        return {"status": "fail", "rule": "target_registered"}
    if view.proposal.relation not in _SUPPORTED_RELATIONS:
        return {"status": "fail", "rule": "supported_relation"}
    return None


def _derive_recommended_action(trust_status: str, schema_gate_result: Optional[dict]) -> str:
    if schema_gate_result is not None:
        rule = schema_gate_result.get("rule", "unknown")
        if rule == "target_registered":
            return (
                "Target not in registry. Run `folio refresh` or `folio ingest` "
                "upstream; if the target is intentionally missing, reject via "
                "`folio links review`."
            )
        if rule == "supported_relation":
            return (
                "Proposal uses an unsupported relation kind. Reject via "
                "`folio links review` or amend the producer."
            )
        return (
            f"Schema gate failed (rule: {rule}). Review with "
            "`folio links review`; upstream fix may be needed."
        )
    if trust_status == "flagged":
        return (
            "Review with `folio links review`; note: source or target "
            "document has review_status: flagged."
        )
    return "Review with `folio links review` and confirm or reject it."


def _matches_scope(path: str, scope: str) -> bool:
    norm_scope = scope.rstrip("/") + "/"
    return path == scope or path.startswith(norm_scope)


def _iter_scoped_entries(registry_data: dict, scope: Optional[str]):
    for entry_data in registry_data.get("decks", {}).values():
        entry = registry_mod.entry_from_dict(entry_data)
        if scope and not (
            _matches_scope(entry.markdown_path, scope)
            or _matches_scope(entry.deck_dir, scope)
        ):
            continue
        yield entry


def _default_stub_path(library_root: Path, entity_type: str, canonical_name: str) -> Path:
    from .entity_stubs import _stub_filename

    return library_root / "_entities" / entity_type / f"{_stub_filename(canonical_name)}.md"


def _analysis_inputs_stale(entry, fm: dict, registry_data: dict) -> bool:
    llm_meta = fm.get("_llm_metadata")
    if not isinstance(llm_meta, dict):
        return False
    graph_meta = llm_meta.get("graph")
    if not isinstance(graph_meta, dict):
        return False
    stored = graph_meta.get("input_fingerprint")
    if not isinstance(stored, str) or not stored:
        return False

    input_ids: list[str] = []
    for field_name in ("draws_from", "depends_on"):
        value = fm.get(field_name)
        if isinstance(value, str) and value:
            input_ids.append(value)
        elif isinstance(value, list):
            input_ids.extend([item for item in value if isinstance(item, str) and item])
    if not input_ids:
        return False
    try:
        entries = resolve_input_entries(registry_data, input_ids)
    except ValueError:
        return True
    return compute_graph_input_fingerprint(entries) != stored


def graph_status(config: FolioConfig, *, scope: Optional[str] = None) -> GraphStatus:
    library_root = config.library_root.resolve()
    registry_data = registry_mod.load_registry(library_root / "registry.json")
    pending, _ = collect_pending_relationship_proposals(config, scope=scope)

    docs_without_links = 0
    orphaned_targets = 0
    protected_notes = 0
    stale_analysis = 0

    all_ids = set(registry_data.get("decks", {}).keys())
    for entry in _iter_scoped_entries(registry_data, scope):
        fm = registry_mod._read_frontmatter(library_root / entry.markdown_path)
        if not isinstance(fm, dict):
            continue
        canonical = canonical_relationship_targets(fm)
        if entry.type in _GRAPH_DOC_TYPES and len(canonical) == 0:
            docs_without_links += 1
        orphaned_targets += sum(1 for _relation, target_id in canonical if target_id not in all_ids)
        body_status = (
            fm.get("_llm_metadata", {})
            .get("enrich", {})
            .get("axes", {})
            .get("body", {})
            .get("status")
        )
        if body_status == "skipped_protected":
            protected_notes += 1
        if entry.type == "analysis" and _analysis_inputs_stale(entry, fm, registry_data):
            stale_analysis += 1

    unconfirmed_entities = 0
    missing_stubs = 0
    duplicate_candidates = 0
    entities_path = library_root / "entities.json"
    if entities_path.exists():
        reg = EntityRegistry(entities_path)
        reg.load()
        unconfirmed_entities = reg.unconfirmed_count()
        duplicate_candidates = len(reg.suggest_person_merges(apply_rejection_memory=True))
        for entity_type, _key, entity in reg.iter_entities():
            if entity.needs_confirmation:
                continue
            if not _default_stub_path(library_root, entity_type, entity.canonical_name).exists():
                missing_stubs += 1

    return GraphStatus(
        pending_relationship_proposals=len(pending),
        docs_without_canonical_graph_links=docs_without_links,
        orphaned_canonical_relation_targets=orphaned_targets,
        enrich_protected_notes=protected_notes,
        unconfirmed_entities=unconfirmed_entities,
        confirmed_entities_missing_stubs=missing_stubs,
        duplicate_person_candidates=duplicate_candidates,
        stale_analysis_artifacts=stale_analysis,
    )


def graph_doctor(
    config: FolioConfig,
    *,
    scope: Optional[str] = None,
    limit: Optional[int] = None,
    include_flagged: bool = False,
) -> list[dict]:
    library_root = config.library_root.resolve()
    registry_data = registry_mod.load_registry(library_root / "registry.json")
    findings: list[dict] = []
    all_ids = set(registry_data.get("decks", {}).keys())

    pending_views, _ = collect_pending_relationship_proposals(
        config, scope=scope, include_flagged=include_flagged
    )
    for view in pending_views:
        trust = _derive_trust_status(view)
        gate = _compute_relationship_schema_gate(view, all_ids)
        findings.append(
            {
                "code": "pending_relationship_proposal",
                "severity": "medium",
                "subject_id": None,
                "detail": (
                    f"{view.source_id} has pending {view.proposal.relation} -> "
                    f"{view.proposal.target_id} from {view.producer}"
                ),
                "recommended_action": _derive_recommended_action(trust, gate),
                "proposal_id": view.proposal.proposal_id,
                "proposal_type": "relationship",
                "source_id": view.source_id,
                "target_id": view.proposal.target_id,
                "evidence_bundle": list(view.proposal.signals),
                "reason_summary": view.proposal.rationale,
                "trust_status": trust,
                "schema_gate_result": gate,
                "producer": view.producer,
                "input_fingerprint": view.proposal.basis_fingerprint,
                "lifecycle_state": view.proposal.lifecycle_state,
            }
        )

    for entry in _iter_scoped_entries(registry_data, scope):
        fm = registry_mod._read_frontmatter(library_root / entry.markdown_path)
        if not isinstance(fm, dict):
            continue
        canonical = canonical_relationship_targets(fm)
        for relation, target_id in canonical:
            if target_id in all_ids:
                continue
            findings.append(
                {
                    "code": "orphaned_canonical_relation",
                    "severity": "high",
                    "subject_id": entry.id,
                    "detail": f"{relation} targets missing document '{target_id}'",
                    "recommended_action": "Remove or repair the canonical relationship target.",
                }
            )
        body_status = (
            fm.get("_llm_metadata", {})
            .get("enrich", {})
            .get("axes", {})
            .get("body", {})
            .get("status")
        )
        if body_status == "skipped_protected":
            findings.append(
                {
                    "code": "protected_enrich_body",
                    "severity": "medium",
                    "subject_id": entry.id,
                    "detail": "Enrich protected the body because managed sections were not identifiable.",
                    "recommended_action": "Re-convert or inspect the note structure before re-running enrich.",
                }
            )
        if entry.type == "analysis" and _analysis_inputs_stale(entry, fm, registry_data):
            findings.append(
                {
                    "code": "stale_analysis_artifact",
                    "severity": "high",
                    "subject_id": entry.id,
                    "detail": "Stored graph input fingerprint no longer matches current upstream inputs.",
                    "recommended_action": "Refresh or regenerate the analysis note from its current inputs.",
                }
            )

    entities_path = library_root / "entities.json"
    if entities_path.exists():
        reg = EntityRegistry(entities_path)
        reg.load()
        for entity_type, key, entity in reg.iter_entities():
            if entity.needs_confirmation:
                findings.append(
                    {
                        "code": "unconfirmed_entity",
                        "severity": "medium",
                        "subject_id": f"{entity_type}:{key}",
                        "detail": f"{entity.canonical_name} is still unconfirmed.",
                        "recommended_action": "Confirm or reject the entity before relying on it for graph queries.",
                    }
                )
            elif not _default_stub_path(library_root, entity_type, entity.canonical_name).exists():
                findings.append(
                    {
                        "code": "missing_entity_stub",
                        "severity": "low",
                        "subject_id": f"{entity_type}:{key}",
                        "detail": f"{entity.canonical_name} has no default stub note under _entities/.",
                        "recommended_action": "Run `folio entities generate-stubs --force`.",
                    }
                )
        for suggestion in reg.suggest_person_merges(apply_rejection_memory=True):
            findings.append(
                {
                    "code": "duplicate_person_candidate",
                    "severity": "medium",
                    "subject_id": f"{suggestion.left_key}|{suggestion.right_key}",
                    "detail": (
                        f"{suggestion.left_name} and {suggestion.right_name} look mergeable "
                        f"({', '.join(suggestion.reasons)})."
                    ),
                    "recommended_action": "Inspect with `folio entities suggest-merges` and merge if they are the same person.",
                }
            )

    findings.sort(
        key=lambda item: (
            _SEVERITY_RANK.get(item["severity"], 9),
            item["code"],
            item["subject_id"],
        )
    )
    if limit is not None:
        return findings[: max(0, limit)]
    return findings


def _aggregate_producer_acceptance_rates(
    config: FolioConfig,
    *,
    scope: Optional[str] = None,
) -> tuple[list[ProducerAcceptanceRate], int]:
    """Aggregate per-producer accepted / rejected counts across managed-doc frontmatter.

    Returns ``(rates, missing_producer_count)``. ``rates`` is sorted for rendering:
    ``low-acceptance`` first, then ``ok``, then ``warmup``; alphabetical by producer
    within each bucket. ``missing_producer_count`` tallies ``confirmed_relationships``
    entries that lack a ``producer`` field (data-integrity diagnostic).
    """

    library_root = config.library_root.resolve()
    registry_data = registry_mod.load_registry(library_root / "registry.json")

    accepted_counts: dict[str, int] = {}
    rejected_counts: dict[str, int] = {}
    missing_producer_count = 0

    for entry in _iter_scoped_entries(registry_data, scope):
        fm = registry_mod._read_frontmatter(library_root / entry.markdown_path)
        if not isinstance(fm, dict):
            continue
        llm_meta = fm.get("_llm_metadata")
        if not isinstance(llm_meta, dict):
            continue

        for key, producer_meta in llm_meta.items():
            if key == "links":
                continue  # SF-1: reserved namespace, not a producer axis
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
                state = raw.get("lifecycle_state")
                if state is None:
                    state = raw.get("status")
                if state == "rejected":
                    rejected_counts[key] = rejected_counts.get(key, 0) + 1

        links_meta = llm_meta.get("links")
        if isinstance(links_meta, dict):
            confirmed = links_meta.get("confirmed_relationships")
            if isinstance(confirmed, list):
                for record in confirmed:
                    if not isinstance(record, dict):
                        continue
                    producer = record.get("producer")
                    if not isinstance(producer, str) or not producer:
                        missing_producer_count += 1
                        continue
                    accepted_counts[producer] = accepted_counts.get(producer, 0) + 1

    producers = sorted(set(accepted_counts) | set(rejected_counts))
    rates: list[ProducerAcceptanceRate] = []
    for producer in producers:
        accepted = accepted_counts.get(producer, 0)
        rejected = rejected_counts.get(producer, 0)
        total = accepted + rejected
        if total < _ACCEPTANCE_WARMUP_COUNT:
            rates.append(
                ProducerAcceptanceRate(
                    producer=producer,
                    accepted=accepted,
                    rejected=rejected,
                    total_reviewed=total,
                    rate=None,
                    status="warmup",
                    warmup=True,
                )
            )
            continue
        rate = accepted / total if total else 0.0
        status = "low-acceptance" if rate < _ACCEPTANCE_GATE_RATE else "ok"
        rates.append(
            ProducerAcceptanceRate(
                producer=producer,
                accepted=accepted,
                rejected=rejected,
                total_reviewed=total,
                rate=rate,
                status=status,
                warmup=False,
            )
        )

    rates.sort(key=lambda r: (_STATUS_SORT_RANK.get(r.status, 9), r.producer))
    return rates, missing_producer_count
